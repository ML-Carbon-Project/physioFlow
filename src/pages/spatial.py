"""Página de Análise Espacial Avançada.

Inclui interpolação determinística (IDW) e estatísticas de autocorrelação
espacial global (Moran's I) e local (LISA). Dependências opcionais
(geobr, libpysal, esda) são carregadas com tratamento de erro para que a
aplicação continue funcionando mesmo quando elas não estão instaladas.
"""
from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from src.components.charts import show_fig

from src.components.dataset_controls import ensure_raw_dataframe, render_dataset_source_toggle
from src.i18n import t

LAT_COL = "Latitude"
LON_COL = "Longitude"

_LAT_ALIASES = ("latitude", "lat", "y", "lat_dd", "latitude_dd")
_LON_ALIASES = ("longitude", "lon", "long", "lng", "x", "lon_dd", "longitude_dd")


def _find_coord_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> Optional[str]:
    lookup = {c.strip().lower(): c for c in df.columns}
    for alias in aliases:
        if alias in lookup:
            return lookup[alias]
    return None


def _normalize_coord_columns(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Rename whatever lat/lon variant the dataset uses to canonical names.

    Returns None if either column is missing.
    """
    lat = _find_coord_column(df, _LAT_ALIASES)
    lon = _find_coord_column(df, _LON_ALIASES)
    if lat is None or lon is None:
        return None
    rename = {}
    if lat != LAT_COL:
        rename[lat] = LAT_COL
    if lon != LON_COL:
        rename[lon] = LON_COL
    return df.rename(columns=rename) if rename else df


def _has_coords(df: pd.DataFrame) -> bool:
    return LAT_COL in df.columns and LON_COL in df.columns


def _robust_norm(values: np.ndarray):
    """Normalização robusta usando 5–95 percentis (mantém escala estável com outliers)."""
    from matplotlib.colors import Normalize

    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return Normalize(vmin=0.0, vmax=1.0)
    lo, hi = np.percentile(finite, [5, 95])
    if hi - lo < 1e-12:
        hi = lo + 1.0
    return Normalize(vmin=lo, vmax=hi)


def _utm_epsg_from_lon(lon_mean: float, lat_mean: float = -1.0) -> int:
    """EPSG do fuso UTM correspondente, escolhendo hemisfério via latitude."""
    zone = int((lon_mean + 180) // 6) + 1
    if lat_mean >= 0:
        return 32600 + zone  # hemisfério norte
    return 32700 + zone  # hemisfério sul


def _project_lonlat_to_utm(
    lon: np.ndarray, lat: np.ndarray
) -> tuple[np.ndarray, np.ndarray, int]:
    """Projeta arrays ``(lon, lat)`` em graus para metros UTM.

    Retorna ``(x_m, y_m, epsg)``. O EPSG é escolhido pelo fuso UTM da longitude
    média e hemisfério da latitude média. Tenta ``pyproj`` primeiro; se não
    estiver disponível, cai numa aproximação equirretangular local (boa para
    áreas pequenas como a do projeto, com erro < 0,5 % em < 50 km).
    """
    lon_arr = np.asarray(lon, dtype=float)
    lat_arr = np.asarray(lat, dtype=float)
    lon_mean = float(np.nanmean(lon_arr))
    lat_mean = float(np.nanmean(lat_arr))
    epsg = _utm_epsg_from_lon(lon_mean, lat_mean)
    try:
        from pyproj import Transformer
    except ImportError:
        m_per_deg_lat = 111_320.0
        m_per_deg_lon = 111_320.0 * float(np.cos(np.radians(lat_mean)))
        x_m = (lon_arr - lon_mean) * m_per_deg_lon
        y_m = (lat_arr - lat_mean) * m_per_deg_lat
        return x_m, y_m, 0  # epsg=0 sinaliza fallback aproximado
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x_m, y_m = transformer.transform(lon_arr, lat_arr)
    return np.asarray(x_m, dtype=float), np.asarray(y_m, dtype=float), epsg


def _idw_grid(
    lon: np.ndarray,
    lat: np.ndarray,
    z: np.ndarray,
    grid_size: int = 220,
    power: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolação IDW manual em grid regular.

    O grid de saída (xi, yi) está em **graus** para preservar a leitura
    geográfica nos eixos do imshow, mas as distâncias usadas no cálculo dos
    pesos são em **metros UTM** — corrige a anisotropia que aparece em
    latitudes médias quando se computa distância Euclidiana em graus
    (1° lat ≈ 110 km vs. 1° lon ≈ 105 km em -17,8°).
    """
    lon_min, lon_max = float(np.min(lon)), float(np.max(lon))
    lat_min, lat_max = float(np.min(lat)), float(np.max(lat))
    lon_pad = (lon_max - lon_min) * 0.05 or 1e-3
    lat_pad = (lat_max - lat_min) * 0.05 or 1e-3
    xi = np.linspace(lon_min - lon_pad, lon_max + lon_pad, grid_size)
    yi = np.linspace(lat_min - lat_pad, lat_max + lat_pad, grid_size)
    XI, YI = np.meshgrid(xi, yi)

    obs_x, obs_y, _ = _project_lonlat_to_utm(lon, lat)
    grid_x, grid_y, _ = _project_lonlat_to_utm(XI.ravel(), YI.ravel())
    pts = np.column_stack([obs_x, obs_y])
    grid_pts = np.column_stack([grid_x, grid_y])

    diff = grid_pts[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    eps = 1e-12
    weights = 1.0 / np.power(dist + eps, power)
    weights /= weights.sum(axis=1, keepdims=True)
    zi = (weights * z).sum(axis=1).reshape(XI.shape)
    return xi, yi, zi


def _render_idw_section(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.idw.title')}")
    st.caption(t("spatial.idw.caption"))

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(
        t("spatial.idw.target"),
        options=numeric_cols,
        key="spatial_idw_target",
    )
    facet_options = [t("common.none")] + [c for c in cat_cols if c in df.columns]
    facet_col = st.selectbox(
        t("spatial.idw.facet"),
        options=facet_options,
        key="spatial_idw_facet",
    )
    grid_size = st.slider(t("spatial.idw.grid"), 80, 320, 180, 20, key="spatial_idw_grid")
    power = st.slider(t("spatial.idw.power"), 0.5, 4.0, 2.0, 0.5, key="spatial_idw_power")

    work = df[[LAT_COL, LON_COL, target] + ([] if facet_col == t("common.none") else [facet_col])].dropna()
    if work.empty:
        st.info(t("spatial.idw.no_data"))
        return

    if facet_col == t("common.none"):
        fig, ax = plt.subplots(figsize=(8, 6))
        xi, yi, zi = _idw_grid(
            work[LON_COL].to_numpy(),
            work[LAT_COL].to_numpy(),
            work[target].to_numpy(),
            grid_size=grid_size,
            power=power,
        )
        norm = _robust_norm(zi)
        im = ax.imshow(
            zi,
            origin="lower",
            extent=[xi.min(), xi.max(), yi.min(), yi.max()],
            cmap="viridis",
            norm=norm,
            aspect="auto",
        )
        ax.scatter(work[LON_COL], work[LAT_COL], c="white", edgecolor="black", s=18, linewidths=0.5)
        ax.set_xlabel(t("spatial.longitude"))
        ax.set_ylabel(t("spatial.latitude"))
        ax.set_title(t("spatial.idw.title_dynamic", var=target))
        fig.colorbar(im, ax=ax, label=target)
        show_fig(fig)
        plt.close(fig)
    else:
        levels = sorted(work[facet_col].dropna().unique().tolist())
        cols_per_row = 2
        n_rows = int(np.ceil(len(levels) / cols_per_row))
        fig, axes = plt.subplots(n_rows, cols_per_row, figsize=(12, 5 * n_rows), squeeze=False)

        z_all = work[target].to_numpy()
        norm = _robust_norm(z_all)

        for idx, level in enumerate(levels):
            r, c = divmod(idx, cols_per_row)
            ax = axes[r][c]
            sub = work[work[facet_col] == level]
            if len(sub) < 4:
                ax.set_title(t("spatial.idw.facet_too_few", level=str(level)))
                ax.axis("off")
                continue
            xi, yi, zi = _idw_grid(
                sub[LON_COL].to_numpy(),
                sub[LAT_COL].to_numpy(),
                sub[target].to_numpy(),
                grid_size=grid_size,
                power=power,
            )
            im = ax.imshow(
                zi,
                origin="lower",
                extent=[xi.min(), xi.max(), yi.min(), yi.max()],
                cmap="viridis",
                norm=norm,
                aspect="auto",
            )
            ax.scatter(sub[LON_COL], sub[LAT_COL], c="white", edgecolor="black", s=18, linewidths=0.5)
            ax.set_title(f"{facet_col} = {level}")
            ax.set_xlabel(t("spatial.longitude"))
            ax.set_ylabel(t("spatial.latitude"))
            fig.colorbar(im, ax=ax, label=target)

        for empty_idx in range(len(levels), n_rows * cols_per_row):
            r, c = divmod(empty_idx, cols_per_row)
            axes[r][c].axis("off")

        fig.suptitle(t("spatial.idw.title_facet", var=target, facet=facet_col), y=1.0)
        show_fig(fig)
        plt.close(fig)


def _render_moran_section(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.moran.title')}")
    st.caption(t("spatial.moran.caption"))

    try:
        from libpysal.weights import KNN
        from esda.moran import Moran, Moran_Local
    except ImportError:
        st.warning(t("spatial.moran.missing_deps"))
        return

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(
        t("spatial.moran.target"),
        options=numeric_cols,
        key="spatial_moran_target",
    )
    k = st.slider(t("spatial.moran.k"), 3, 12, 6, 1, key="spatial_moran_k")
    n_perm = st.slider(t("spatial.moran.permutations"), 99, 999, 499, 100, key="spatial_moran_perm")

    work = df[[LAT_COL, LON_COL, target]].dropna()
    if len(work) < max(k + 2, 8):
        st.info(t("spatial.moran.too_few", n=len(work)))
        return

    y = work[target].to_numpy()
    # KNN em metros UTM: a ordem dos vizinhos passa a ser isotrópica.
    obs_x_m, obs_y_m, _ = _project_lonlat_to_utm(
        work[LON_COL].to_numpy(), work[LAT_COL].to_numpy()
    )
    coords_utm = np.column_stack([obs_x_m, obs_y_m])

    try:
        w = KNN.from_array(coords_utm, k=k)
        w.transform = "r"
        moran = Moran(y, w, permutations=n_perm)
        local = Moran_Local(y, w, permutations=n_perm)
    except Exception as exc:
        st.error(t("spatial.moran.error", error=str(exc)))
        return

    c1, c2, c3 = st.columns(3)
    c1.metric(t("spatial.moran.metric_I"), f"{moran.I:.4f}")
    c2.metric(t("spatial.moran.metric_p"), f"{moran.p_sim:.4f}")
    c3.metric(t("spatial.moran.metric_z"), f"{moran.z_sim:.3f}")

    sig = local.p_sim < 0.05
    quadrant = local.q
    cluster = np.full(len(work), "NS", dtype=object)
    cluster[(quadrant == 1) & sig] = "HH"
    cluster[(quadrant == 2) & sig] = "LH"
    cluster[(quadrant == 3) & sig] = "LL"
    cluster[(quadrant == 4) & sig] = "HL"

    work = work.assign(cluster=cluster, local_I=local.Is, local_p=local.p_sim)

    color_map = {
        "HH": "#d7191c",
        "LL": "#2c7bb6",
        "HL": "#fdae61",
        "LH": "#abd9e9",
        "NS": "#bdbdbd",
    }

    fig, (ax_lisa, ax_scatter) = plt.subplots(1, 2, figsize=(14, 6))
    for label, color in color_map.items():
        mask = work["cluster"] == label
        if mask.any():
            ax_lisa.scatter(
                work.loc[mask, LON_COL],
                work.loc[mask, LAT_COL],
                c=color,
                s=60,
                edgecolor="black",
                linewidths=0.4,
                label=f"{label} ({int(mask.sum())})",
            )
    ax_lisa.set_xlabel(t("spatial.longitude"))
    ax_lisa.set_ylabel(t("spatial.latitude"))
    ax_lisa.set_title(t("spatial.moran.lisa_map_title", var=target))
    ax_lisa.legend(loc="best", fontsize=8)

    y_z = (y - y.mean()) / (y.std() if y.std() > 0 else 1.0)
    wy = (w.sparse @ y_z) if hasattr(w, "sparse") else np.array([np.mean([y_z[j] for j in w.neighbors[i]]) for i in range(len(y_z))])
    ax_scatter.scatter(y_z, wy, c=[color_map[c] for c in work["cluster"]], edgecolor="black", linewidths=0.3, alpha=0.85)
    ax_scatter.axhline(0, color="black", linewidth=0.5)
    ax_scatter.axvline(0, color="black", linewidth=0.5)
    ax_scatter.set_xlabel(t("spatial.moran.scatter_x", var=target))
    ax_scatter.set_ylabel(t("spatial.moran.scatter_y"))
    ax_scatter.set_title(t("spatial.moran.scatter_title"))

    show_fig(fig)
    plt.close(fig)

    summary = (
        work.groupby("cluster")
        .agg(n=("cluster", "size"), mean_value=(target, "mean"), median_value=(target, "median"))
        .reindex(["HH", "HL", "LH", "LL", "NS"])
        .dropna(how="all")
        .round(4)
    )
    st.markdown(f"##### {t('spatial.moran.summary_title')}")
    st.dataframe(summary, use_container_width=True)
    st.download_button(
        t("spatial.moran.download"),
        data=work.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"lisa_{target}.csv",
        mime="text/csv",
    )


def _render_gistar_section(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.gistar.title')}")
    st.caption(t("spatial.gistar.caption"))

    try:
        from libpysal.weights import DistanceBand
        from esda.getisord import G_Local
        from scipy.spatial import cKDTree
    except ImportError:
        st.warning(t("spatial.gistar.missing_deps"))
        return

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(t("spatial.gistar.target"), options=numeric_cols, key="spatial_gistar_target")
    k = st.slider(t("spatial.gistar.k"), 3, 12, 6, 1, key="spatial_gistar_k")
    n_perm = st.slider(t("spatial.gistar.permutations"), 99, 999, 499, 100, key="spatial_gistar_perm")
    alpha = st.slider(t("spatial.gistar.alpha"), 0.001, 0.10, 0.05, 0.005, key="spatial_gistar_alpha")

    work = df[[LAT_COL, LON_COL, target]].dropna()
    if len(work) < max(k + 2, 8):
        st.info(t("spatial.gistar.too_few", n=len(work)))
        return

    y = work[target].to_numpy()

    # Para o Getis-Ord usamos coordenadas em metros UTM — o raio d* da
    # distance-band fica então em metros, fisicamente interpretável, e não
    # sofre a distorção anisotrópica de lat/lon em graus.
    obs_x_m, obs_y_m, epsg = _project_lonlat_to_utm(
        work[LON_COL].to_numpy(), work[LAT_COL].to_numpy()
    )
    coords_utm = np.column_stack([obs_x_m, obs_y_m])

    try:
        # Distance-band threshold: max of each point's distance to its k-th nearest
        # neighbour, scaled by 1.001 to ensure all k-th neighbours are included.
        # This follows the methodology specification (Getis & Ord 1992).
        tree = cKDTree(coords_utm)
        kth_dist, _ = tree.query(coords_utm, k=k + 1)  # k+1 because index 0 is self
        d_star = float(kth_dist[:, -1].max() * 1.001)
        w = DistanceBand.from_array(coords_utm, threshold=d_star, binary=False)
        w.transform = "r"
        gi = G_Local(y, w, star=True, permutations=n_perm)
    except Exception as exc:
        st.error(t("spatial.gistar.error", error=str(exc)))
        return

    crs_label = f"EPSG:{epsg}" if epsg > 0 else t("spatial.crs.local_equirect")
    st.caption(t("spatial.gistar.d_star_caption", d_star=f"{d_star:,.0f}", crs=crs_label))

    classes = np.full(len(work), "NS", dtype=object)
    sig = gi.p_sim < alpha
    classes[sig & (gi.Zs > 0)] = "Hotspot"
    classes[sig & (gi.Zs < 0)] = "Coldspot"

    work = work.assign(z_gi=gi.Zs, p_gi=gi.p_sim, gi_class=classes)
    color_map = {"Hotspot": "#d7191c", "Coldspot": "#2c7bb6", "NS": "#bdbdbd"}

    fig, ax = plt.subplots(figsize=(9, 7))
    for label, color in color_map.items():
        mask = work["gi_class"] == label
        if mask.any():
            ax.scatter(
                work.loc[mask, LON_COL],
                work.loc[mask, LAT_COL],
                c=color,
                s=70,
                edgecolor="black",
                linewidths=0.4,
                label=f"{label} ({int(mask.sum())})",
            )
    ax.set_xlabel(t("spatial.longitude"))
    ax.set_ylabel(t("spatial.latitude"))
    ax.set_title(t("spatial.gistar.map_title", var=target))
    ax.legend(loc="best", fontsize=9)
    show_fig(fig)
    plt.close(fig)

    summary = (
        work.groupby("gi_class")
        .agg(n=("gi_class", "size"), mean_value=(target, "mean"), median_value=(target, "median"))
        .reindex(["Hotspot", "Coldspot", "NS"])
        .dropna(how="all")
        .round(4)
    )
    st.markdown(f"##### {t('spatial.gistar.summary_title')}")
    st.dataframe(summary, use_container_width=True)
    st.download_button(
        t("spatial.gistar.download"),
        data=work.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"gistar_{target}.csv",
        mime="text/csv",
    )


def _render_utmgrid_section(df: pd.DataFrame, numeric_cols: list[str], cat_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.utmgrid.title')}")
    st.caption(t("spatial.utmgrid.caption"))

    try:
        import geopandas as gpd
        from shapely.geometry import Point, box
    except ImportError:
        st.warning(t("spatial.utmgrid.missing_deps"))
        return

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(t("spatial.utmgrid.target"), options=numeric_cols, key="spatial_utm_target")
    cell_km = st.slider(t("spatial.utmgrid.cell_km"), 0.5, 10.0, 1.0, 0.5, key="spatial_utm_cell")
    facet_options = [t("common.none")] + [c for c in cat_cols if c in df.columns]
    facet_col = st.selectbox(t("spatial.utmgrid.facet"), options=facet_options, key="spatial_utm_facet")
    agg_label = st.radio(
        t("spatial.utmgrid.agg"),
        options=[t("spatial.utmgrid.agg.median"), t("spatial.utmgrid.agg.mean")],
        horizontal=True,
        key="spatial_utm_agg",
    )
    agg_func = "median" if agg_label == t("spatial.utmgrid.agg.median") else "mean"

    needed_cols = [LAT_COL, LON_COL, target] + ([] if facet_col == t("common.none") else [facet_col])
    work = df[needed_cols].dropna().copy()
    if work.empty:
        st.info(t("spatial.utmgrid.no_data"))
        return

    epsg = _utm_epsg_from_lon(work[LON_COL].mean())
    geom = [Point(xy) for xy in zip(work[LON_COL], work[LAT_COL])]
    gdf = gpd.GeoDataFrame(work, geometry=geom, crs="EPSG:4326").to_crs(epsg=epsg)

    cell = cell_km * 1000.0
    minx, miny, maxx, maxy = gdf.total_bounds
    minx, miny = np.floor(minx / cell) * cell, np.floor(miny / cell) * cell
    maxx, maxy = np.ceil(maxx / cell) * cell, np.ceil(maxy / cell) * cell

    xs = np.arange(minx, maxx + cell, cell)
    ys = np.arange(miny, maxy + cell, cell)
    cells = []
    for x in xs[:-1]:
        for y in ys[:-1]:
            cells.append({"geometry": box(x, y, x + cell, y + cell), "_cx": x + cell / 2, "_cy": y + cell / 2})
    grid = gpd.GeoDataFrame(cells, crs=gdf.crs)
    grid["cell_id"] = np.arange(len(grid))

    joined = gpd.sjoin(gdf, grid[["geometry", "cell_id"]], how="left", predicate="within")
    if facet_col == t("common.none"):
        agg = joined.groupby("cell_id")[target].agg([agg_func, "size"]).rename(columns={agg_func: "value", "size": "n"}).reset_index()
        merged = grid.merge(agg, on="cell_id", how="left")
        fig, ax = plt.subplots(figsize=(10, 7))
        merged.plot(column="value", cmap="viridis", legend=True, ax=ax, missing_kwds={"color": "#f1f5f9"}, edgecolor="white", linewidth=0.3)
        ax.set_title(t("spatial.utmgrid.title_dynamic", var=target, cell=cell_km, epsg=epsg))
        ax.set_axis_off()
        show_fig(fig)
        plt.close(fig)
        st.dataframe(agg.dropna().sort_values("value", ascending=False).head(50), use_container_width=True)
        st.download_button(
            t("spatial.utmgrid.download"),
            data=agg.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"utmgrid_{cell_km}km_{target}.csv",
            mime="text/csv",
        )
    else:
        levels = sorted(joined[facet_col].dropna().unique().tolist())
        cols_per_row = 2
        n_rows = int(np.ceil(len(levels) / cols_per_row))
        fig, axes = plt.subplots(n_rows, cols_per_row, figsize=(13, 6 * n_rows), squeeze=False)
        for idx, level in enumerate(levels):
            r, c = divmod(idx, cols_per_row)
            ax = axes[r][c]
            sub = joined[joined[facet_col] == level]
            agg_l = sub.groupby("cell_id")[target].agg([agg_func, "size"]).rename(columns={agg_func: "value", "size": "n"}).reset_index()
            merged = grid.merge(agg_l, on="cell_id", how="left")
            merged.plot(column="value", cmap="viridis", legend=True, ax=ax, missing_kwds={"color": "#f1f5f9"}, edgecolor="white", linewidth=0.3)
            ax.set_title(f"{facet_col} = {level}")
            ax.set_axis_off()
        for empty_idx in range(len(levels), n_rows * cols_per_row):
            r, c = divmod(empty_idx, cols_per_row)
            axes[r][c].axis("off")
        fig.suptitle(t("spatial.utmgrid.title_facet", var=target, cell=cell_km), y=0.995)
        show_fig(fig)
        plt.close(fig)


def _empirical_variogram(coords: np.ndarray, z: np.ndarray, n_lags: int = 12, max_frac: float = 0.6, sample: int = 800):
    n = len(coords)
    if n > sample:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, size=sample, replace=False)
        coords, z = coords[idx], z[idx]
        n = sample
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    dz2 = (z[:, None] - z[None, :]) ** 2
    iu = np.triu_indices(n, k=1)
    d_flat = dist[iu]
    g_flat = dz2[iu] / 2.0
    h_max = float(d_flat.max() * max_frac)
    edges = np.linspace(0, h_max, n_lags + 1)
    centers, gammas, counts = [], [], []
    for i in range(n_lags):
        m = (d_flat >= edges[i]) & (d_flat < edges[i + 1])
        if m.sum() == 0:
            continue
        centers.append(0.5 * (edges[i] + edges[i + 1]))
        gammas.append(float(g_flat[m].mean()))
        counts.append(int(m.sum()))
    return np.array(centers), np.array(gammas), np.array(counts), h_max


def _spherical(h, nugget, sill, rng):
    h = np.asarray(h, dtype=float)
    out = np.where(
        h <= rng,
        nugget + sill * (1.5 * h / rng - 0.5 * (h / rng) ** 3),
        nugget + sill,
    )
    out = np.where(h <= 0, 0.0, out)
    return out


def _fit_spherical(centers, gammas):
    from scipy.optimize import least_squares

    sill0 = float(np.var(gammas)) + float(np.mean(gammas))
    rng0 = float(centers.max() * 0.5) if centers.size else 1.0
    nug0 = float(min(gammas)) if gammas.size else 0.0

    def residuals(params):
        nugget, sill, rng = params
        return _spherical(centers, max(nugget, 0.0), max(sill, 1e-9), max(rng, 1e-9)) - gammas

    res = least_squares(residuals, x0=[nug0, sill0, rng0], bounds=([0, 1e-9, 1e-9], [np.inf, np.inf, np.inf]))
    nugget, sill, rng = res.x
    return float(nugget), float(sill), float(rng)


def _ordinary_kriging(coords: np.ndarray, z: np.ndarray, grid_xy: np.ndarray, nugget: float, sill: float, rng: float):
    n = len(coords)
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    G = _spherical(dist, nugget, sill, rng)
    A = np.ones((n + 1, n + 1))
    A[:n, :n] = G
    A[n, n] = 0.0
    A_inv = np.linalg.pinv(A)
    diff_g = grid_xy[:, None, :] - coords[None, :, :]
    dist_g = np.sqrt((diff_g ** 2).sum(axis=2))
    g0 = _spherical(dist_g, nugget, sill, rng)
    rhs = np.column_stack([g0, np.ones(grid_xy.shape[0])])
    weights = rhs @ A_inv
    z_aug = np.append(z, 1.0)
    pred = (weights * z_aug).sum(axis=1) - weights[:, -1] * 1.0
    pred = (weights[:, :n] * z).sum(axis=1)
    return pred


def _render_kriging_section(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.kriging.title')}")
    st.caption(t("spatial.kriging.caption"))

    try:
        from scipy.optimize import least_squares  # noqa: F401
    except ImportError:
        st.warning(t("spatial.kriging.missing_deps"))
        return

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(t("spatial.kriging.target"), options=numeric_cols, key="spatial_krig_target")
    n_lags = st.slider(t("spatial.kriging.n_lags"), 6, 30, 12, 1, key="spatial_krig_lags")
    max_frac = st.slider(t("spatial.kriging.max_frac"), 0.3, 0.95, 0.60, 0.05, key="spatial_krig_maxfrac")
    grid_size = st.slider(t("spatial.kriging.grid"), 60, 220, 120, 10, key="spatial_krig_grid")
    winsorize = st.checkbox(t("spatial.kriging.winsorize"), value=True, key="spatial_krig_wins")

    work = df[[LAT_COL, LON_COL, target]].dropna()
    if len(work) < 12:
        st.info(t("spatial.kriging.too_few", n=len(work)))
        return

    z = work[target].to_numpy(dtype=float)
    if winsorize:
        lo, hi = np.percentile(z, [2, 98])
        z = np.clip(z, lo, hi)

    # Distâncias em metros (UTM) — antes computávamos a Euclidiana em graus,
    # o que inflate o eixo Y em ~5% em latitude -17,8° e dá range em "graus",
    # sem unidade física para o usuário.
    obs_lon = work[LON_COL].to_numpy(dtype=float)
    obs_lat = work[LAT_COL].to_numpy(dtype=float)
    obs_x_m, obs_y_m, epsg = _project_lonlat_to_utm(obs_lon, obs_lat)
    coords_utm = np.column_stack([obs_x_m, obs_y_m])

    try:
        centers, gammas, counts, h_max = _empirical_variogram(
            coords_utm, z, n_lags=n_lags, max_frac=max_frac
        )
        if centers.size < 3:
            st.info(t("spatial.kriging.few_lags"))
            return
        nugget, sill, rng = _fit_spherical(centers, gammas)
    except Exception as exc:
        st.error(t("spatial.kriging.error", error=str(exc)))
        return

    fig_v, ax_v = plt.subplots(figsize=(8, 4.5))
    ax_v.plot(centers, gammas, "o", color="#0f766e", label=t("spatial.kriging.empirical"))
    h_smooth = np.linspace(0, centers.max(), 200)
    ax_v.plot(h_smooth, _spherical(h_smooth, nugget, sill, rng), "-", color="#d7191c", label=t("spatial.kriging.spherical"))
    ax_v.set_xlabel(t("spatial.kriging.lag_h_m"))
    ax_v.set_ylabel(t("spatial.kriging.semivariance"))
    ax_v.set_title(t("spatial.kriging.variogram_title", var=target))
    ax_v.legend()
    show_fig(fig_v)
    plt.close(fig_v)

    crs_label = f"EPSG:{epsg}" if epsg > 0 else t("spatial.crs.local_equirect")
    st.caption(t("spatial.kriging.units_caption", crs=crs_label))
    c1, c2, c3 = st.columns(3)
    c1.metric(t("spatial.kriging.metric_nugget"), f"{nugget:.4g}")
    c2.metric(t("spatial.kriging.metric_sill"), f"{sill:.4g}")
    c3.metric(t("spatial.kriging.metric_range_m"), f"{rng:,.0f} m")

    if not st.checkbox(t("spatial.kriging.run_ok"), value=False, key="spatial_krig_run"):
        st.info(t("spatial.kriging.toggle_to_run"))
        return

    # Grid de saída em lat/lon (para o eixo do mapa); cálculo do kriging em UTM.
    lon_min, lon_max = obs_lon.min(), obs_lon.max()
    lat_min, lat_max = obs_lat.min(), obs_lat.max()
    lon_pad = (lon_max - lon_min) * 0.05 or 1e-3
    lat_pad = (lat_max - lat_min) * 0.05 or 1e-3
    xi = np.linspace(lon_min - lon_pad, lon_max + lon_pad, grid_size)
    yi = np.linspace(lat_min - lat_pad, lat_max + lat_pad, grid_size)
    XI, YI = np.meshgrid(xi, yi)
    grid_x_m, grid_y_m, _ = _project_lonlat_to_utm(XI.ravel(), YI.ravel())
    grid_xy_utm = np.column_stack([grid_x_m, grid_y_m])

    try:
        pred = _ordinary_kriging(coords_utm, z, grid_xy_utm, nugget, sill, rng).reshape(XI.shape)
    except Exception as exc:
        st.error(t("spatial.kriging.error", error=str(exc)))
        return

    fig_k, ax_k = plt.subplots(figsize=(9, 7))
    norm = _robust_norm(pred)
    im = ax_k.imshow(
        pred,
        origin="lower",
        extent=[xi.min(), xi.max(), yi.min(), yi.max()],
        cmap="viridis",
        norm=norm,
        aspect="auto",
    )
    ax_k.scatter(obs_lon, obs_lat, c="white", edgecolor="black", s=22, linewidths=0.5)
    ax_k.set_xlabel(t("spatial.longitude"))
    ax_k.set_ylabel(t("spatial.latitude"))
    ax_k.set_title(t("spatial.kriging.surface_title", var=target))
    fig_k.colorbar(im, ax=ax_k, label=target)
    show_fig(fig_k)
    plt.close(fig_k)


@st.cache_data(show_spinner=False)
def _load_rio_verde_boundary():
    try:
        import geobr  # type: ignore

        gdf = geobr.read_municipality(code_muni=5218805, year=2020)
        return gdf
    except Exception:
        return None


def _render_basemap_section(df: pd.DataFrame, numeric_cols: list[str]) -> None:
    st.markdown(f"#### {t('spatial.basemap.title')}")
    st.caption(t("spatial.basemap.caption"))

    boundary = _load_rio_verde_boundary()
    if boundary is None:
        st.info(t("spatial.basemap.unavailable"))
        return

    if len(numeric_cols) == 0:
        st.info(t("spatial.no_numeric"))
        return

    target = st.selectbox(
        t("spatial.basemap.target"),
        options=numeric_cols,
        key="spatial_basemap_target",
    )

    work = df[[LAT_COL, LON_COL, target]].dropna()
    if work.empty:
        st.info(t("spatial.basemap.no_data"))
        return

    fig, ax = plt.subplots(figsize=(9, 7))
    boundary.plot(ax=ax, color="#f0f9ff", edgecolor="#0f766e", linewidth=1.2)
    sc = ax.scatter(
        work[LON_COL],
        work[LAT_COL],
        c=work[target],
        cmap="magma_r",
        s=70,
        edgecolor="black",
        linewidths=0.4,
        alpha=0.9,
    )
    ax.set_xlabel(t("spatial.longitude"))
    ax.set_ylabel(t("spatial.latitude"))
    ax.set_title(t("spatial.basemap.title_dynamic", var=target))
    fig.colorbar(sc, ax=ax, label=target)
    show_fig(fig)
    plt.close(fig)


def render() -> None:
    st.subheader(t("spatial.title"))

    df_raw = ensure_raw_dataframe(t("spatial.warn_no_data"))
    if df_raw is None:
        return

    df = render_dataset_source_toggle("spatial_use_processed")
    if df is None:
        df = df_raw

    # Aplica os filtros na página
    from src.components.filters import render_page_filters
    df = render_page_filters(df)

    normalized = _normalize_coord_columns(df)
    if normalized is None:
        st.info(t("spatial.no_coords"))
        return
    df = normalized

    numeric_cols = list(df.select_dtypes(include="number").columns)
    numeric_cols = [c for c in numeric_cols if c not in (LAT_COL, LON_COL)]
    cat_cols = [c for c in df.columns if c not in df.select_dtypes(include="number").columns]

    tabs = st.tabs([
        t("spatial.tab.idw"),
        t("spatial.tab.moran"),
        t("spatial.tab.gistar"),
        t("spatial.tab.utmgrid"),
        t("spatial.tab.kriging"),
        t("spatial.tab.basemap"),
    ])
    with tabs[0]:
        _render_idw_section(df, numeric_cols, cat_cols)
    with tabs[1]:
        _render_moran_section(df, numeric_cols)
    with tabs[2]:
        _render_gistar_section(df, numeric_cols)
    with tabs[3]:
        _render_utmgrid_section(df, numeric_cols, cat_cols)
    with tabs[4]:
        _render_kriging_section(df, numeric_cols)
    with tabs[5]:
        _render_basemap_section(df, numeric_cols)
