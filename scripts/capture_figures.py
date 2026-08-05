"""Recaptura as figuras do artigo (Software Impacts) a partir do dataset sintético.

Sobe-se o app à parte e roda-se::

    .venv/bin/streamlit run app.py --server.headless true --server.port 8502
    .venv/bin/python scripts/capture_figures.py --port 8502

As PNGs vão para ``Paper_SoftwareImpacts/figs/`` em ``device_scale_factor=3``,
para atender ao mínimo de 300 dpi / 2244 px de largura da Elsevier.

Cada figura é recortada na região relevante da página (do primeiro ao último
elemento de interesse), reproduzindo o enquadramento das capturas originais em
vez de fotografar a página inteira.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import Locator, Page, TimeoutError as PWTimeout, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIGS = ROOT / "Paper_SoftwareImpacts" / "figs"

# As figuras do artigo derivam da campanha de campo, des-identificada por
# ``scripts/deidentify_field_dataset.py`` — é o que sustenta os números da
# Seção 5.1. O dataset sintético do repositório reproduz o *esquema*, não os
# resultados, e serve para reexecutar o fluxo, não para gerar as figuras.
DATASET = ROOT / "data" / "sample" / "physiology_synthetic.csv"

VIEWPORT = {"width": 1500, "height": 1800}
SCALE = 3
MAIN = '[data-testid="stMainBlockContainer"]'
SCROLLER = '[data-testid="stMain"]'
PAD = 18  # folga em px CSS acima/abaixo da região recortada

# Preditores do exercício de modelagem descrito no artigo (troca gasosa,
# fluorescência e clorofila). O default do app inclui Cultura/Fazenda/Época,
# que não fazem parte daquele run.
PAPER_FEATURES = (
    "gs", "Ca", "Ci", "Ci/Ca", "E", "YII", "ETR",
    "Chl_a_media", "Chl_b_media", "IAF_media",
)

PAPER_MODELS = (
    "Linear Regression", "Random Forest", "Decision Tree",
    "Gradient Boosting", "K-Nearest Neighbors",
)

# A toolbar ("Deploy", menu ⋮) e a faixa colorida do topo são cromo do Streamlit,
# não fazem parte da interface analisada no artigo.
HIDE_CHROME = """
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], header { display: none !important; }
"""


def wait_ready(page: Page, settle: int = 1200) -> None:
    """Espera o Streamlit terminar o rerun: status widget some e o DOM assenta."""
    page.wait_for_timeout(400)
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=60_000)
    except PWTimeout:
        pass
    page.wait_for_load_state("networkidle", timeout=60_000)
    page.wait_for_timeout(settle)


def nav(page: Page, label: str) -> None:
    """Clica um item do option_menu da sidebar.

    O ``streamlit_option_menu`` é um componente customizado e vive num iframe
    próprio — daí a busca pelo frame antes do clique.
    """
    for frame in page.frames:
        if "option_menu" in frame.url:
            frame.locator(f'.nav-link:has-text("{label}")').first.click()
            wait_ready(page)
            return
    raise RuntimeError("iframe do option_menu não encontrado")


def click_tab(page: Page, label: str) -> None:
    page.locator(f'[role="tab"]:has-text("{label}")').first.click()
    wait_ready(page)


def shot_region(page: Page, name: str, start: Locator | None, end: Locator | None) -> None:
    """Recorta a região de ``start`` a ``end`` do container principal.

    A área principal do Streamlit é um container rolável e virtualizado: o que
    está fora da viewport não é pintado, e um screenshot de elemento alto sai
    com faixas em branco. Por isso a região é primeiro rolada para o topo da
    viewport e só então fotografada via ``clip``.
    """
    FIGS.mkdir(parents=True, exist_ok=True)

    if start is not None:
        start.evaluate("el => el.scrollIntoView({block: 'start'})")
    else:
        page.eval_on_selector(SCROLLER, "el => el.scrollTop = 0")
    page.wait_for_timeout(900)

    box_main = page.locator(MAIN).first.bounding_box()
    box_start = start.bounding_box() if start is not None else None
    box_end = end.bounding_box() if end is not None else None
    if box_main is None:
        raise RuntimeError(f"{name}: container principal sem bounding box")

    top = max(0.0, (box_start["y"] - PAD) if box_start else box_main["y"])
    bottom = (box_end["y"] + box_end["height"] + PAD) if box_end else box_main["y"] + box_main["height"]
    bottom = min(bottom, float(VIEWPORT["height"]))
    if bottom - top < 40:
        raise RuntimeError(f"{name}: região inválida (top={top:.0f}, bottom={bottom:.0f})")
    if box_end and box_end["y"] + box_end["height"] > VIEWPORT["height"]:
        print(f"    ! {name}: região excede a viewport — aumente VIEWPORT['height']")

    img_bytes = page.screenshot(
        clip={"x": box_main["x"], "y": top, "width": box_main["width"], "height": bottom - top}
    )
    img = Image.open(io.BytesIO(img_bytes))
    img.save(FIGS / name)
    print(f"  ✓ {name}  {img.width}×{img.height}")


def page_heading(page: Page) -> Locator:
    """Título da página — âncora superior do recorte, evitando o respiro do topo."""
    return page.locator(f"{MAIN} :is(h1, h2, h3)").first


def sb_set(page: Page, sb: Locator, label: str) -> None:
    """Escolhe uma opção num ``st.selectbox``."""
    sb.click()
    page.wait_for_timeout(500)
    exact = page.locator('[role="option"]').filter(
        has_text=re.compile(rf"^{re.escape(label)}$")
    )
    (exact.first if exact.count() else page.locator('[role="option"]').first).click()
    wait_ready(page, 1200)


def ms_chips(ms: Locator) -> list[str]:
    return [
        chip.get_attribute("title") or ""
        for chip in ms.locator('[data-baseweb="tag"] span[title]').all()
    ]


def ms_remove(page: Page, ms: Locator, label: str) -> None:
    """Remove um chip pelo rótulo exato."""
    tag = ms.locator(f'[data-baseweb="tag"]:has(span[title="{label}"])').first
    tag.locator('svg[title="Delete"]').click()
    wait_ready(page, 900)


def ms_add(page: Page, ms: Locator, label: str) -> None:
    """Acrescenta uma opção a um ``st.multiselect``.

    Digita para filtrar e clica na opção de texto **exato** — com prefixos
    ambíguos ("Ca" também casa "Ci/Ca"), confirmar com Enter pega a errada.
    """
    field = ms.locator("input").first
    field.click()
    page.wait_for_timeout(300)
    field.type(label, delay=25)
    page.wait_for_timeout(700)
    exact = page.locator('[role="option"]').filter(
        has_text=re.compile(rf"^{re.escape(label)}$")
    )
    (exact.first if exact.count() else page.locator('[role="option"]').first).click()
    # Sem isso o dropdown fica aberto, com o filtro digitado, e entra na figura
    # como um painel "No results".
    page.keyboard.press("Escape")
    wait_ready(page, 900)


def ms_set(page: Page, ms: Locator, labels: tuple[str, ...]) -> None:
    """Faz o ``st.multiselect`` convergir para exatamente ``labels``.

    Um passo por rerun, relendo os chips a cada volta: o widget do baseweb
    reposiciona os chips a cada rerun do Streamlit, e um plano de cliques
    calculado de antemão acaba removendo o chip vizinho.
    """
    for _ in range(3 * len(labels) + 12):
        current = ms_chips(ms)
        extra = [c for c in current if c not in labels]
        missing = [w for w in labels if w not in current]
        if not extra and not missing:
            return
        print(f"    · ajustando: -{extra[:2]} +{missing[:2]} (tem {len(current)})")
        # Nunca esvaziar de todo: sem features o app retorna cedo e o widget some.
        if extra and (len(current) > 1 or not missing):
            ms_remove(page, ms, extra[0])
        else:
            ms_add(page, ms, missing[0])
    raise RuntimeError(f"multiselect não convergiu; atual={ms_chips(ms)}")


def set_english(page: Page) -> None:
    """Troca o idioma para inglês — as figuras do artigo estão em EN."""
    box = page.locator('[data-testid="stSelectbox"]').first
    if box.inner_text().strip().lower().startswith("english"):
        return
    box.click()
    page.wait_for_timeout(600)
    page.click('[role="option"]:has-text("English")')
    wait_ready(page, 2000)


def load_dataset(page: Page) -> None:
    page.set_input_files('[data-testid="stFileUploaderDropzone"] input[type=file]', str(DATASET))
    wait_ready(page, 2000)
    page.click('button:has-text("Load dataset")')
    wait_ready(page, 2500)


def fig_upload(page: Page) -> None:
    # O expander de schema fica fechado, como na figura original.
    shot_region(
        page,
        "upload_schema.png",
        start=page.locator('[data-testid="stButton"]').first,
        end=page.locator('[data-testid="stDataFrame"]').last,
    )


def fig_pipeline(page: Page) -> None:
    nav(page, "Pipeline & Processing")
    wait_ready(page, 2000)
    shot_region(
        page,
        "pipeline_audit.png",
        start=page_heading(page),
        end=page.locator('[data-testid="stDataFrame"]').first,  # tabela do step report
    )


def fig_confounding(page: Page) -> None:
    nav(page, "EDA")
    click_tab(page, "Data Quality")
    wait_ready(page, 2500)
    shot_region(
        page,
        "confounding.png",
        start=page.locator('h5:has-text("Confounding between categories")').first,
        end=page.locator('[data-testid="stAlert"]:has-text("redundant")').last,
    )


def fig_modeling(page: Page) -> None:
    nav(page, "Modeling")
    wait_ready(page, 2500)

    # O artigo compara os preditores fisiológicos (troca gasosa, fluorescência e
    # clorofila); Cultura/Fazenda/Época entram por padrão mas não fazem parte
    # daquele exercício.
    feats = page.locator('[data-testid="stMultiSelect"]:has-text("Features")').first
    ms_set(page, feats, PAPER_FEATURES)

    # O padrão do app são dois regressores; a figura do artigo compara os cinco.
    models = page.locator('[data-testid="stMultiSelect"]:has-text("Models to compare")').first
    ms_set(page, models, PAPER_MODELS)

    # GroupKFold não é o padrão (o padrão é KFold aleatório): a figura do artigo
    # mostra o guard-rail de pseudoreplicação ligado, agrupando por Fazenda+Ponto.
    page.locator('[data-testid="stRadio"] label:has-text("GroupKFold")').first.click()
    wait_ready(page, 5000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)

    shot_region(
        page,
        "modeling_comparison.png",
        start=page.locator('[data-testid="stSelectbox"]:has-text("Target variable")').first,
        end=page.locator('[data-testid="stMetric"]').last,
    )


def fig_stl(page: Page) -> None:
    nav(page, "Time Series")
    click_tab(page, "STL")
    wait_ready(page, 2000)
    # O default é a primeira coluna numérica ("Ponto", o número do ponto amostral),
    # cuja decomposição não faria sentido; a figura do artigo usa uma variável
    # fisiológica (EUA, eficiência do uso da água).
    sb_set(page, page.locator('[data-testid="stSelectbox"]:has-text("Variable")').first, "EUA")
    # O rerun disparado pelo selectbox deixa o painel da aba vizinha montado acima,
    # então o recorte começa no título da própria seção STL.
    shot_region(
        page,
        "stl_blocked.png",
        start=page.locator(f'{MAIN} :is(h3, h4):has-text("STL decomposition (trend")').first,
        end=page.locator('[data-testid="stAlert"]').last,
    )


def main() -> int:
    global DATASET

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8502)
    ap.add_argument("--only", default=None, help="captura só uma figura")
    ap.add_argument("--dataset", default=None, help="CSV/XLSX a carregar (default: sintético)")
    args = ap.parse_args()

    if args.dataset:
        DATASET = Path(args.dataset)
    if not DATASET.exists():
        print(f"dataset não encontrado: {DATASET}", file=sys.stderr)
        return 1
    print(f"→ dataset: {DATASET}")

    steps = {
        "upload": fig_upload,
        "pipeline": fig_pipeline,
        "confounding": fig_confounding,
        "modeling": fig_modeling,
        "stl": fig_stl,
    }

    url = f"http://localhost:{args.port}"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=SCALE)
        page = ctx.new_page()
        print(f"→ abrindo {url}")
        page.goto(url, wait_until="networkidle", timeout=60_000)
        wait_ready(page, 2000)
        page.add_style_tag(content=HIDE_CHROME)

        set_english(page)
        print("→ carregando dataset")
        load_dataset(page)

        # EDA/Modelagem/Séries leem o dataframe *processado*, que só passa a
        # existir depois de a página Pipeline rodar — como no uso real do app.
        if args.only and args.only != "pipeline":
            print("→ (pré-requisito) rodando o pipeline")
            nav(page, "Pipeline & Processing")
            wait_ready(page, 2000)

        for name, fn in steps.items():
            if args.only and args.only != name:
                continue
            print(f"→ {name}")
            fn(page)

        browser.close()
    print(f"\nfiguras em {FIGS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
