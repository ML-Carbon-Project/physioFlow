from __future__ import annotations

import streamlit as st

# Fração da largura do container ocupada pelos gráficos. Menor que 1.0 deixa um
# respiro à direita, tornando os gráficos menos dominantes no layout "wide"
# (o st.pyplot, por padrão, estica 100% da largura).
CHART_WIDTH_FRACTION = 0.85

# Resolução de renderização do PNG. Não altera o tamanho exibido (governado pela
# largura do container/fração), apenas a nitidez — o st.pyplot usa 200 por padrão.
CHART_DPI = 300


def show_fig(fig, fraction: float = CHART_WIDTH_FRACTION, dpi: int = CHART_DPI) -> None:
    """Renderiza uma figura matplotlib (ou grid do seaborn) ocupando ``fraction``
    da largura do container (padrão ~85%), com alta resolução (``dpi``).

    - ``fraction < 1.0``: gráfico numa coluna estreita (menos dominante).
    - ``fraction >= 1.0``: largura total do container.
    - ``dpi``: só afeta a nitidez do PNG, não o tamanho exibido.

    Use no lugar de ``st.pyplot(fig)`` para gráficos de nível superior. Não use
    dentro de um ``st.columns`` já aberto (criaria aninhamento de colunas além de
    um nível) — nesses casos o gráfico já é estreito e não precisa reduzir.
    """
    if fraction >= 1.0:
        st.pyplot(fig, dpi=dpi)
        return
    left, _ = st.columns([fraction, 1.0 - fraction])
    left.pyplot(fig, dpi=dpi)
