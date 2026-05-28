<!-- markdownlint-disable MD013 MD033 -->

# Manual de Operação — Fisiologia Vegetal Goiás Verde

> Versão do manual: 1.0 (alinhada à versão 1.x do aplicativo)
> Idioma de referência: Português. Espelhos planejados em [`manual.en.md`](manual.en.md) e [`manual.es.md`](manual.es.md).

---

## Índice

1. [Apresentação](#1-apresentação)
2. [Instalação e primeira execução](#2-instalação-e-primeira-execução)
3. [Carregando seus dados](#3-carregando-seus-dados)
4. [Pipeline de limpeza](#4-pipeline-de-limpeza)
5. [Filtros globais](#5-filtros-globais)
6. [Análise Exploratória (EDA)](#6-análise-exploratória-eda)
7. [Regressão bivariada](#7-regressão-bivariada)
8. [Modelagem preditiva](#8-modelagem-preditiva)
9. [Análise espacial](#9-análise-espacial)
10. [Série temporal](#10-série-temporal)
11. [Comparação por grupos](#11-comparação-por-grupos)
12. [Glossário estatístico](#12-glossário-estatístico)
13. [Solução de problemas (FAQ)](#13-solução-de-problemas-faq)
14. [Referências](#14-referências)
15. [Contribuindo](#15-contribuindo)

---

## 1. Apresentação

### 1.1 Para quem é este manual

Este manual é dirigido a **pesquisadores, estudantes de pós-graduação e técnicos de campo** que vão usar o aplicativo *Fisiologia Vegetal — Goiás Verde* para analisar dados ecofisiológicos coletados em campo (medições de IRGA, clorofilômetro, ceptômetro etc.). Não pressupõe experiência prévia com Streamlit nem com programação em Python; pressupõe familiaridade básica com os termos da fisiologia vegetal (`A`, `gs`, `Ci`, IAF, Clorofila a/b).

### 1.2 O que o aplicativo faz

Em uma frase: **valida, limpa, explora e modela** planilhas de campo de fisiologia vegetal, com suporte adicional a análises **espaciais** (sobre o município de Rio Verde, GO) e **temporais**. O fluxo padrão é Upload → Pipeline → EDA → Regressão/Modelagem/Espacial/Temporal/Comparativa. As páginas trabalham sobre o mesmo dataset em sessão e respeitam os filtros globais aplicados na barra lateral.

### 1.3 Convenções tipográficas

* `Caminhos/de/arquivo` e `códigos` aparecem em `fonte monoespaçada`.
* **Negrito** marca elementos da interface (botões, abas, rótulos de seletores).
* *Itálico* marca termos técnicos na primeira ocorrência — todos têm entrada no [Glossário](#12-glossário-estatístico).
* `>` marca uma instrução de ação ("> clique em **Upload**").
* Capturas de tela usam o dataset de exemplo `data/sample/0_Dados_Fisiologia_RIO VERDE.xlsx`.

---

## 2. Instalação e primeira execução

### 2.1 Pré-requisitos

| Item | Mínimo | Recomendado |
|---|---|---|
| Sistema operacional | Linux, macOS ou Windows 10+ | macOS / Linux |
| Python | 3.12 | 3.12 ou 3.14 |
| Memória RAM | 4 GB | 8 GB |
| Espaço em disco | 1 GB livre | 2 GB livre |
| Navegador | Chrome ou Firefox recente | qualquer baseado em Chromium |

### 2.2 Instalando o ambiente

A partir da pasta raiz do projeto, abra um terminal e execute:

```bash
# 1) Criar e ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# 2) Atualizar instaladores e instalar dependências
pip install -U pip wheel
pip install -r requirements.txt
```

A instalação baixa, entre outras, `streamlit`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, `esda`, `libpysal`, `geopandas`, `pyproj` e `geobr`. A primeira execução pode levar de 30 segundos a 2 minutos enquanto Streamlit cacheia recursos.

### 2.3 Rodando o aplicativo

Com o ambiente virtual ativado:

```bash
python -m streamlit run app.py
```

O terminal mostrará algo parecido com:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

![Terminal mostrando Streamlit iniciado](img/manual/01_terminal_streamlit_run.png)

O navegador deve abrir automaticamente em `http://localhost:8501`. Se não abrir, copie o **Local URL** e cole no seu navegador.

### 2.4 A primeira tela

Você verá a página **Upload** carregada, com a barra lateral à esquerda contendo:

* logo do **CEAGRE / Goiás Verde**;
* seletor de **Idioma** (`Português` / `English` / `Español`);
* menu de navegação com **Upload**, **Pipeline e Processamento**, **EDA**, **Regressão**, **Modelagem**, **Análise Espacial**, **Série Temporal** e **Comparativa**.

![Primeira tela do aplicativo](img/manual/02_app_primeira_tela.png)

### 2.5 Mudando o idioma

Use o seletor **Idioma** no topo da barra lateral. A mudança é instantânea; todas as páginas, rótulos e mensagens de aviso passam para o idioma escolhido. O idioma padrão é Português.

### 2.6 Login (opcional)

Se o ambiente foi configurado com [Supabase](https://supabase.com) (variáveis `SUPABASE_URL` e `SUPABASE_ANON_KEY` no arquivo `.streamlit/secrets.toml`), o aplicativo exibe uma tela de login antes do menu. Caso essas variáveis não existam, o login é desativado e o app abre direto na Upload — comportamento padrão para uso local.

---

## 3. Carregando seus dados

### 3.1 Formatos aceitos

| Extensão | Observações |
|---|---|
| `.xlsx` | Recomendado. Suporta múltiplas planilhas — você escolhe qual carregar. |
| `.xls` | Excel legado, aceito. |
| `.csv` | Aceito. Use separador `,` e codificação UTF-8 ou Latin-1. |

Limite por arquivo: **500 MB** (limite do Streamlit). Para arquivos maiores, divida em planilhas.

### 3.2 Schema esperado

O aplicativo compara o cabeçalho do seu arquivo contra um **schema de referência** com três severidades:

| Severidade | O que significa | O que acontece se faltar |
|---|---|---|
| **Obrigatória** | Sem essa coluna, o fluxo essencial não funciona. | Aviso destacado; o pipeline pode falhar. |
| **Recomendada** | Habilita as análises padrão (EDA, regressão, modelagem). | Aviso médio; análises específicas ficam vazias. |
| **Opcional** | Habilita módulos específicos (Espacial, Temporal, réplicas). | Aviso informativo; o módulo correspondente é desabilitado. |

O dicionário completo de colunas — nomes canônicos, sinônimos aceitos, tipo esperado e módulo dependente — está em [`docs/data_dictionary.md`](data_dictionary.md). A lista canônica é gerada a partir de [`src/schema.py`](../src/schema.py); sempre que o app for atualizado, esse dicionário reflete a verdade do código.

> **Importante:** o aplicativo aceita várias grafias para a mesma coluna. `Cultura`, `CULTURA` e `Crop_Type` são tratados como o mesmo campo; o mesmo vale para `Latitude` / `LATITUDE`, `Data da coleta` / `Data` / `Date`, e assim por diante. A coluna real do arquivo aparece na coluna "Encontrada" do relatório de validação.

### 3.3 Carregando o arquivo

> Clique em **Upload** > **Browse files**, escolha o arquivo `.xlsx` e clique em **Carregar arquivo**.

Se o arquivo for um Excel com várias planilhas, o app exibe um seletor para escolher qual carregar. Após o carregamento, duas métricas aparecem no topo:

* **Linhas** — total de registros lidos.
* **Colunas** — total de colunas no cabeçalho.

![Arquivo carregado com métricas e início do schema](img/manual/03_upload_arquivo_carregado.png)

### 3.4 Lendo o relatório de validação

Logo abaixo das métricas aparece o painel **Validação do schema esperado**, com três caixas resumo (obrigatórias / recomendadas / opcionais) no formato `presentes / total`.

![Resumo do schema](img/manual/04_upload_schema_resumo.png)

#### Avisos comuns e o que fazer

| Mensagem | Diagnóstico | Ação sugerida |
|---|---|---|
| **"Colunas obrigatórias ausentes"** | Faltam colunas críticas no arquivo. | Renomeie a coluna no Excel para um dos nomes aceitos (ver dicionário); recarregue. |
| **"Colunas obrigatórias presentes mas 100% vazias"** | A coluna existe no cabeçalho, mas todas as células estão vazias. Comum com `Manejo` e `Textura`. | Verifique se a coluna deveria estar preenchida. Se for um dado opcional para o seu estudo, ignore — o pipeline ainda funciona, mas algumas análises não considerarão essa variável. |
| **"Latitude fora do intervalo [-90, 90]"** | Possível troca de Latitude e Longitude, ou valores em outra unidade (graus minutos segundos). | Reabra o arquivo, confira os valores e converta para graus decimais. |
| Coluna marcada como **"tipo divergente"** | A coluna foi encontrada mas o conteúdo não corresponde ao tipo esperado (ex.: texto em coluna numérica). | Procure células com texto, comentários ou caracteres estranhos na coluna correspondente. |

#### Ver a tabela completa

> Clique em **Detalhes do schema** para expandir uma tabela com cada coluna esperada: nome encontrado, tipo detectado, status (`presente`, `vazia (100% nula)`, `ausente`, `tipo divergente`) e qual módulo do app depende dela.

![Tabela detalhada do schema](img/manual/05_upload_schema_tabela.png)

> **Dica:** clicar no botão **Baixar relatório de validação** salva essa tabela como CSV — útil para enviar à pessoa responsável pela planilha pedindo correções pontuais.

### 3.5 O que NÃO acontece no Upload

* O arquivo **não é enviado** para nenhum servidor externo. Tudo é processado localmente, na sua sessão do Streamlit.
* Nenhum dado é **descartado** nesta etapa. O pipeline de limpeza só roda quando você abre a próxima aba (**Pipeline e Processamento**).
* Colunas com nomes desconhecidos são **mantidas** no dataset — você pode usá-las nos filtros e gráficos do EDA, mesmo que não constem no schema oficial.

### 3.6 Quando recarregar

* Se você corrigiu a planilha externamente (Excel) e quer aplicar as mudanças, basta repetir o upload — o app substitui o arquivo carregado anteriormente.
* Se trocou de idioma, **não** precisa recarregar; só a UI muda, o dataset permanece.

---

## 4. Pipeline de limpeza

> Página **Pipeline e Processamento** no menu lateral.

A planilha enviada na aba Upload contém o dataset **bruto**. Antes de qualquer análise, o aplicativo aplica um pipeline de **4 etapas determinísticas** que padronizam o texto, removem linhas sem informação essencial, descartam pontos de grade vazios e tratam as réplicas das medições foliares (Clorofila a/b e IAF). O resultado é o dataset **processado**, usado por padrão em todas as análises subsequentes.

### 4.1 As 4 etapas do pipeline

Cada etapa é registrada no relatório de execução, com `Linhas antes`, `Linhas depois` e `% removidas`. Ordem fixa:

1. **Padronização de texto** — remove espaços extras das colunas categóricas (`Cultura`, `Uso atual`, `Época`, `Fazenda`, `Município`, `Estágio`) e converte strings "nan" / "None" / vazio em `NaN`. Não remove linhas; apenas normaliza.
2. **Remoção de registros sem metadados essenciais** — descarta linhas onde **qualquer uma** das colunas `Cultura`, `Uso atual` ou `Época` está vazia. Sem esses três campos, o registro não pode ser agrupado nas análises comparativas.
3. **Remoção de pontos de grade vazios** — descarta linhas onde **todas** as variáveis agronômicas/fisiológicas estão nulas (`A`, `E`, `gs`, `Ca`, `Ci`, `Ci/Ca`, `EUA`, `A/Ci`, `YII`, `ETR`, `Chl a`, `Chl b`, `IAF`). Estes são pontos amostrais previstos na grade mas que não receberam medição.
4. **Tratamento de réplicas** — consolida as réplicas de Clorofila a/b e IAF conforme o modo selecionado (ver §4.2). É a única etapa cujo comportamento o usuário controla.

### 4.2 Tratamento de réplicas — escolhendo entre os 6 modos

A planilha contém **duas réplicas** de Clorofila a (`Chl a`, `Chl a.1`), **duas** de Clorofila b (`Chl b`, `Chl b.1`) e **três** de IAF (`IAF`, `IAF.1`, `IAF.2`). O dropdown **Alterar Tratamento de Réplicas** oferece seis modos. Independentemente do escolhido, três colunas de saída são criadas para padronizar a interface: `Chl_a_media`, `Chl_b_media` e `IAF_media`.

![Dropdown de tratamento de réplicas](img/manual/06_pipeline_dropdown_replicas.png)

| Modo | O que faz | Quando usar |
|---|---|---|
| **Média das Réplicas** | Média aritmética das réplicas disponíveis. | Padrão. Apropriado quando as réplicas refletem variabilidade biológica genuína da folha/dossel. |
| **Mediana das Réplicas** | Mediana das réplicas. Equivalente à média quando n=2 (caso de Chl a/b); robusta a outlier no IAF (n=3). | Quando uma das leituras pode ter sido espúria (ex.: ceptômetro lendo o céu por engano) e você não quer que ela puxe o valor consolidado. |
| **Desdobrar em Linhas** | Cria uma linha por réplica, com a coluna `Replica` indicando 1, 2 ou 3. Pode até **triplicar** o número de linhas. | Quando você quer tratar cada leitura como observação independente (ex.: para visualizar a variabilidade intra-sítio em boxplots). |
| **Réplica 1 Apenas** | Usa só `Chl a`, `Chl b`, `IAF`. | Comparações de protocolo entre datasets que só guardaram a 1ª réplica. |
| **Réplica 2 Apenas** | Usa só `Chl a.1`, `Chl b.1`, `IAF.1`. | Auditoria — comparar ao modo Réplica 1 para detectar leituras discrepantes. |
| **Réplica 3 Apenas (IAF)** | Só `IAF.2`; Chl a/b ficam vazios (só existe 1 réplica adicional para IAF). | Auditoria específica de ceptômetro. |

#### Por que "Mediana" pode dar o mesmo resultado da "Média"

Quando há apenas **2 réplicas** (Chl a, Chl b), a mediana de dois valores é matematicamente igual à média deles. Por isso o aplicativo exibe uma caption explicativa logo abaixo do dropdown quando você seleciona o modo Mediana:

![Caption do modo Mediana](img/manual/09_pipeline_mediana_caption.png)

O ganho real de robustez aparece **só no IAF** (3 réplicas) — a mediana descarta o valor mais extremo entre as três leituras.

### 4.3 Avisos de descarte

O pipeline executa silenciosamente, mas exibe avisos amarelos destacados quando **mais de 50 %** das linhas são descartadas em uma única etapa ou no balanço final. Esse limite foi calibrado para o cenário típico de planilhas de fisiologia: pequenas perdas (1-5 %) são esperadas; perdas grandes geralmente significam que algo estranho está acontecendo na origem dos dados.

![Aviso de descarte massivo](img/manual/07_pipeline_warning_descarte.png)

No dataset de exemplo `0_Dados_Fisiologia_RIO VERDE.xlsx`, a etapa 2 remove 94,9 % das linhas — porque a planilha tem 1576 pontos da grade amostral cadastrados (com Latitude/Longitude e Fazenda) mas **sem** Cultura, Uso atual e Época preenchidos. Esses pontos representam locais previstos para coleta mas que não tiveram medições efetivas. **O comportamento está correto**; o aviso serve para você confirmar se realmente é o caso ou se há um problema de preenchimento que precisa ser corrigido na origem.

#### Quando se preocupar com o aviso

| Cenário | Provável causa | Ação |
|---|---|---|
| Descarte > 90 % na etapa 2 | Planilha contém grade amostral preenchida só com coordenadas, sem metadados de cultura. | Verifique se essas linhas eram esperadas. Se sim, ignore o aviso. |
| Descarte ~50 % na etapa 2 | Metade da planilha tem `Cultura` (ou `Uso atual`, ou `Época`) faltando. | Volte ao Excel e investigue qual coluna. Provavelmente algo se perdeu na exportação. |
| Descarte > 10 % na etapa 3 | Vários pontos de coleta sem nenhuma medição fisiológica. | Pode ser real (coleta interrompida) ou um vazamento de células vazias. |
| Avisos persistem após você ajustar | Modo de réplica errado, ou planilha com formato inesperado. | Tente alternar entre os 6 modos para ver qual mantém mais linhas. |

### 4.4 Lendo o relatório de etapas

Logo abaixo dos avisos (se houver), a página exibe a tabela **Relatório de etapas** com cinco colunas: `Etapa`, `Linhas antes`, `Linhas depois`, `Removidas`, `% removidas`.

![Relatório de etapas do pipeline](img/manual/08_pipeline_relatorio_etapas.png)

Para o dataset de exemplo, a leitura típica é:

| Etapa | Antes | Depois | Removidas |
|---|---|---|---|
| Padronização de texto | 1661 | 1661 | 0 |
| Remoção sem metadados essenciais | 1661 | 85 | 1576 |
| Remoção pontos de grade vazios | 85 | 81 | 4 |
| Consolidação de réplicas por média | 81 | 81 | 0 |

Resultado: **81 linhas analíticas**, derivadas das 1661 originais.

> **Dica:** se você selecionar o modo *Desdobrar em Linhas*, a última etapa terá `Linhas depois > Linhas antes` (até 3×) — é o único caso em que o pipeline **cresce** o número de linhas. O aviso de "% removidas" mostra um valor negativo nesse caso, o que é esperado.

### 4.5 Toggle "Usar dados processados"

Cada uma das páginas analíticas (EDA, Regressão, Modelagem, Espacial, Temporal, Comparativa) tem um interruptor **Usar dados processados** no topo:

* **Ligado** (padrão): a página usa o dataset **processado** pelo pipeline.
* **Desligado**: a página usa o dataset **bruto** (saída direta do Upload, sem nenhuma etapa do pipeline).

Use a posição "desligada" quando quiser inspecionar a planilha original — por exemplo, para conferir se uma linha que sumiu do EDA realmente estava ausente na origem ou foi removida em alguma das etapas. Para a análise principal, mantenha o toggle **ligado**.

### 4.6 Exportando o dataset processado

No pé da página há dois botões:

* **⬇ CSV** — arquivo `dataset_fisiologia_limpo.csv` com codificação UTF-8 BOM (abre direto no Excel sem quebrar acentos).
* **⬇ Excel** — arquivo `dataset_fisiologia_limpo.xlsx` com a planilha única `Fisiologia_Limpo`.

Ambos contêm o dataset **após o pipeline**, no modo de réplica atualmente selecionado. As três colunas consolidadas (`Chl_a_media`, `Chl_b_media`, `IAF_media`) estão presentes em qualquer modo; no modo *Desdobrar*, a coluna `Replica` aparece adicionalmente.

> **Dica de reprodutibilidade:** depois de carregar uma planilha bruta e escolher um modo de réplica, exporte o CSV processado e arquive-o junto com seus resultados. Você terá um snapshot do que de fato foi analisado, independente de futuras evoluções do pipeline.

---

## 5. Filtros globais

> Painel **⚙️ Painel de Configurações e Filtros** no topo das páginas EDA, Regressão, Modelagem, Espacial e Série Temporal.

Mesmo depois do pipeline, raramente queremos analisar o dataset inteiro de uma vez. O painel de filtros globais permite restringir reativamente a análise a um subconjunto — por cultura, por fazenda, por época, por intervalo de datas — sem precisar reprocessar o arquivo. Os filtros são aplicados em cada página independente e suas mudanças são propagadas a todos os gráficos e modelos da página em tempo real.

### 5.1 Estrutura do painel

O painel é um *expander* — clique no cabeçalho para expandir ou recolher. Por padrão abre expandido na primeira visita à página. Dentro dele, seis filtros organizados em duas linhas de três colunas:

![Painel de filtros globais](img/manual/10_eda_filtros_globais.png)

Linha 1: **Tratamento de Réplicas** • **Cultura** • **Município**
Linha 2: **Fazenda** • **Época** • **Intervalo de Datas**

Abaixo dos filtros, uma métrica de "Pontos Filtrados" mostra `n_filtrado / n_total` — útil para verificar rapidamente quantas linhas sobraram após combinar todos os critérios.

### 5.2 Detalhes de cada filtro

#### Tratamento de Réplicas (atalho)

Replica o dropdown da página Pipeline aqui no painel. Mudar o modo na sidebar **reprocessa todo o dataset** com o novo modo, mantendo os demais filtros. Útil quando você está numa página de análise e quer comparar o efeito de mudar de "Média" para "Mediana" sem voltar à página do Pipeline.

> **Atenção:** ao mudar o modo aqui, a página recarrega (Streamlit `st.rerun()`). Suas seleções nas demais abas são preservadas.

#### Cultura

Multiselect com todas as culturas presentes no dataset. Por padrão, todas vêm marcadas. Desmarque culturas para excluí-las da análise.

> No dataset de exemplo: opções *Soja* e *Cana-de-açúcar*.

#### Município

Selectbox single-select com a opção especial **"Todos"** no topo. Útil quando o dataset tem mais de uma cidade — restringe a um único município.

> No dataset de exemplo: apenas *Rio Verde*. O filtro fica disponível mas não tem efeito prático.

#### Fazenda

Selectbox com **"Todas"** + uma entrada por fazenda presente. **Importante:** se você já filtrou por Município, só aparecem as fazendas daquele município (filtros são encadeados).

> No dataset de exemplo: *Farm B* (soja) e *Farm A* (cana). Lembre-se: estas duas fazendas estão **redundantes** com a coluna `Cultura` — veja o painel de confundimento na aba **Qualidade** do EDA. Filtrar por uma é equivalente a filtrar pela outra.

#### Época

Multiselect com as épocas/estações disponíveis. Comportamento idêntico ao filtro de Cultura.

> No dataset de exemplo: *Verão* (52 linhas após pipeline) e *Primavera* (29 linhas).

#### Intervalo de Datas

`date_input` com **dois ponteiros** — defina a data inicial e a data final. Por padrão usa o range completo do dataset.

> No dataset de exemplo: três datas únicas (2025-12-19, 2026-01-16, 2026-02-28). O filtro é pouco útil aqui dado o pequeno número de coletas, mas ficará potente em datasets com séries mensais.

### 5.3 Combinando filtros — comportamento AND

Todos os filtros são aplicados **simultaneamente** (operador lógico **E**). Por exemplo: selecionar *Soja* na Cultura **e** *Verão* na Época mantém apenas as linhas que satisfazem **ambos** os critérios.

> **Dica de diagnóstico:** se a métrica de "Pontos Filtrados" mostra 0, alguma combinação dos seus filtros eliminou todas as linhas. Recolha o painel e tente reabrir uma seleção; o caso mais comum é cruzar Cultura e Fazenda contraditórias (ex.: Cana × Farm B no dataset de exemplo, que dá 0).

### 5.4 Escopo dos filtros — por página, não global

Apesar do nome "global", cada página tem **seu próprio painel de filtros**. Trocar para a aba EDA, ajustar filtros, e voltar à Regressão **não** aplica os ajustes na Regressão — você precisa configurá-los lá também. Isso é intencional: permite comparar análises sobre subconjuntos diferentes lado a lado.

A exceção é o **Tratamento de Réplicas** — mudar esse interfere no dataset processado e é refletido em todas as páginas, porque é uma decisão do pipeline e não um filtro de visualização.

### 5.5 Quando NÃO usar filtros

* **Antes do EDA inicial.** Comece olhando o dataset inteiro para detectar padrões e *outliers*. Use os filtros depois, para isolar grupos específicos.
* **Para limpar dados ruins.** Filtro não é limpeza. Se uma linha está errada, corrija na planilha de origem e refaça o upload; não esconda com filtro.
* **Para criar dois grupos a comparar.** Para isso, use a página **Comparativa** (capítulo 11), que tem ferramentas dedicadas (Mann-Whitney, log-linear por grupo).

## 6. Análise Exploratória (EDA)

> Página **EDA** no menu lateral.

O Análise Exploratória de Dados é o módulo mais extenso do aplicativo. Doze abas, cada uma com uma família de perguntas distintas: como os valores se distribuem? Há dados faltantes? Variáveis estão correlacionadas? Os grupos diferem entre si? Onde estão os pontos amostrais no espaço? Quando foram coletados? Há *outliers* a investigar?

Use o EDA **antes** de qualquer regressão ou modelagem — é nele que você descobre que `Fazenda` é redundante com `Cultura`, que `Ca` é praticamente constante (e portanto correlações com ela são espúrias), que metade do seu dataset tem `Peso Seco` faltando, ou que uma leitura foi gravada como 9999 por engano.

As 12 abas estão organizadas em três famílias:

* **Descritivo:** Resumo Estatístico, Qualidade dos Dados, Relações Bivariadas, Boxplots, Dispersão, Correlação, Composição.
* **Geográfico e Temporal:** Espacial, Temporal.
* **Inferência e Auditoria:** Inferência (KW + Normalidade + VIF), Hotspots, Outliers.

### 6.1 Resumo Estatístico

Mostra as estatísticas descritivas clássicas (count, mean, std, min, quartis, max) acrescidas de **skewness** (assimetria) e **kurtosis** (curtose) para cada variável numérica.

![Resumo estatístico do EDA](img/manual/11_eda_resumo_estatistico.png)

**Como ler:**

| Indicador | Interpretação |
|---|---|
| `count = 0` | Coluna 100 % vazia (caso de `Manejo` e `Textura` no dataset de exemplo). |
| Diferença grande entre `mean` e `50%` (mediana) | Distribuição assimétrica. |
| `skewness` entre -0,5 e 0,5 | Distribuição aproximadamente simétrica. |
| `|skewness|` > 1 | Distribuição fortemente assimétrica — considere transformação log ou métodos não-paramétricos. |
| `kurtosis` > 3 | Caudas pesadas (mais *outliers* que uma normal). |
| `kurtosis` < 0 | Distribuição achatada (caudas mais leves que uma normal). |

> **Dica:** o botão **Baixar resumo estatístico (CSV)** exporta essa tabela. É útil para incluir como anexo num relatório de campo.

### 6.2 Qualidade dos Dados

Combina três blocos: contagem de linhas/colunas, *missing* por coluna (tabela + gráfico) e — desde a v1.1 — auditoria de **confundimento entre categóricas**.

![Métricas e missing por coluna](img/manual/12_eda_qualidade_metrics.png)

#### Missing por coluna

Tabela ordenada do mais ao menos faltante, com `missing` (contagem absoluta) e `percent` (proporção). Logo abaixo, um gráfico de barras com as colunas que têm pelo menos 1 valor faltante.

> **No dataset Rio Verde (modo *desdobrar*):** `Manejo` e `Textura` aparecem com 100 % missing; `IAF.2` e `Peso Seco` com ~52 %; `IAF.1`, `Chl b.1`, `Chl a.1` com ~18 %; `gs` com ~6 %. Esse padrão (3ª réplica menos preenchida que a 2ª, que é menos que a 1ª) é típico de coletas de campo.

#### Frequência de categorias

Selectbox onde você escolhe uma coluna categórica (`Cultura`, `Fazenda`, `Estágio`, etc.) e vê a tabela de contagem por nível. Útil para detectar problemas de digitação ("Verão" vs "verao", "soja" vs "Soja").

#### Confundimento entre categorias

Esta é uma seção **fundamental** que evita conclusões enganosas no resto do manual. Mostra uma tabela com os pares de colunas categóricas que particionam as linhas da **mesma forma**, calculada por *Cramér's V* (ver Glossário §12).

![Painel de confundimento entre categorias](img/manual/13_eda_qualidade_confounding.png)

**Tipos de relação que aparecem:**

| Relação | O que significa | Exemplo no dataset Rio Verde |
|---|---|---|
| **Redundante (A ≡ B)** | As duas colunas são equivalentes; uma é só re-rotulação da outra. **Cramér's V = 1,000 nos dois sentidos.** | `Fazenda ⟷ Cultura ⟷ Uso atual` — todas particionam as 81 linhas em "Farm B / Soja / Ciclo Curto" vs "Farm A / Cana / Perene". |
| **{A} determina {B}** | Cada nível de A pertence a um único nível de B, mas o inverso não é verdade (B tem mais níveis). | `Estágio` determina `Cultura` (cada estágio fenológico só ocorre em uma cultura). |
| **Associação alta (parcial)** | Forte associação, mas nenhuma das direções é determinística. | Raro neste dataset. |

**Por que isso importa:**

Quando duas colunas são redundantes, qualquer "efeito" atribuído a uma é estatisticamente **indistinguível** do efeito da outra. Se você rodar um Moran's I e descobrir cluster espacial enorme (HH em uma fazenda, LL na outra), o que está sendo captado pode ser **diferença biológica entre as culturas**, e não **autocorrelação espacial real**. Da mesma forma, comparar `gs` entre fazendas é equivalente a comparar `gs` entre culturas — apenas com um rótulo diferente.

> **Quando há pares redundantes**, o app exibe um aviso amarelo destacado: *"Há pares totalmente redundantes — não use as duas como fatores independentes em modelos ou comparações."*

### 6.3 Relações Bivariadas (distribuições univariadas)

Apesar do nome, esta aba mostra **distribuições univariadas** — um histograma por variável selecionada. O nome reflete uma escolha histórica do app; o conteúdo é estritamente *univariado*.

**Configurações:**

* **Variáveis** (multiselect) — até 3 variáveis numéricas, com defaults sensatos.
* **Bins** (slider) — número de classes do histograma (10 a 100).
* **KDE** (checkbox) — sobrepõe uma estimativa de densidade kernel.

**Como usar:** comece com defaults e ajuste `bins` se a distribuição parecer "rugosa" (poucos bins) ou "ruidosa" (muitos bins). A KDE ajuda a identificar bimodalidade — útil para flagrar quando uma variável é mistura de duas populações (ex.: soja + cana). Quando a KDE mostra dois picos, considere rodar análises **por grupo** (com `hue` na aba Boxplot ou na Comparativa).

### 6.4 Boxplots por Grupo

Box-plots (ou *violin plots*) de uma variável numérica agrupada por uma coluna categórica, opcionalmente com uma segunda categórica como `hue`.

**Configurações principais:**

* **Variável-alvo** — a numérica que vai no eixo Y.
* **Agrupamento (X)** — a categórica que vai no eixo X.
* **Cor (hue)** — opcional, segunda categórica que colore os boxes lado a lado.
* **Tipo** — Boxplot ou Violinplot.

**Como ler:**

| Elemento | Significado |
|---|---|
| Caixa | 25º ao 75º percentil (intervalo interquartil, IQR). |
| Linha horizontal na caixa | Mediana. |
| "Bigodes" (whiskers) | Estendem até 1,5 × IQR. |
| Pontos isolados | Outliers (acima de 1,5 × IQR). |

Violinplot adiciona a forma da distribuição (largura proporcional à densidade local). Use **violino** quando a forma importa (bimodalidade); use **boxplot** quando você quer comparar muitos grupos rapidamente.

> **Cuidado com `hue` redundante:** se você selecionar `Cultura` no eixo X **e** `Fazenda` como `hue` no dataset Rio Verde, vai ver dois boxes idênticos lado a lado por categoria — porque são a mesma partição (ver §6.2). Escolha `hue` que **diferencia** dentro do grupo (ex.: `Estágio` dentro de Cultura).

### 6.5 Dispersão (pairplot)

Scatter de **pares** de variáveis numéricas em uma grade triangular inferior. Opcionalmente colorindo os pontos por uma categórica.

**Configurações:**

* **Variáveis** (multiselect) — entre 2 e 6 variáveis. Mais que 6 fica ilegível.
* **Cor (hue)** — opcional. Útil para visualizar separação entre culturas.
* **Amostra** (slider 100-5000) — limita o número de pontos plotados. Para o dataset Rio Verde de 81 linhas, irrelevante; importante em datasets grandes para manter o render rápido.

**O que procurar:**

* **Pares com correlação visível** (linha clara ascendente ou descendente) — confirme depois na aba Correlação (§6.6).
* **Outliers extremos** — pontos que ficam visivelmente longe da nuvem. Marque mentalmente para investigar na aba Outliers (§6.12).
* **Não-linearidades** — curvas ou padrões em U sugerem que regressão linear é inadequada e Spearman é melhor que Pearson.

### 6.6 Correlação

Heatmap de correlação entre as variáveis numéricas selecionadas, em três métricas alternativas:

| Método | Mede | Quando usar |
|---|---|---|
| **Pearson** | Associação linear. | Variáveis aproximadamente normais e relação linear. |
| **Spearman** | Associação monotônica (ordem). | **Padrão recomendado** — robusto a outliers e a não-linearidades monotônicas. |
| **Kendall** | Concordância de pares. | Datasets pequenos (n < 30) com muitos empates. |

![Heatmap de correlação Spearman](img/manual/14_eda_correlacao_spearman.png)

**Como ler valores típicos:**

| Faixa de r | Interpretação |
|---|---|
| `|r|` ≥ 0,8 | Correlação muito forte — confirme se não é por construção matemática (Ci/Ca derivado de Ci/Ca). |
| 0,5 ≤ `|r|` < 0,8 | Forte. |
| 0,3 ≤ `|r|` < 0,5 | Moderada. |
| `|r|` < 0,3 | Fraca a desprezível. |

> **No dataset Rio Verde:** vai aparecer `E ↔ gs` ≈ 0,93 (clássico fisiológico), `YII ↔ ETR` ≈ 0,96 (derivada — ETR é função de YII), `Ci ↔ Ci/Ca` = 1,00 (Ca quase constante, então Ci/Ca ≈ Ci × cte). Esses três pares são **esperados** e não indicam problema dos dados; refletem a química/matemática das próprias variáveis.

Use o botão **Baixar correlação (CSV)** para incluir a matriz num relatório.

### 6.7 Espacial (exploratório)

Mapa de dispersão dos pontos de coleta plotados em Longitude × Latitude, coloridos e dimensionados por uma variável escolhida. Opcionalmente faceteado por uma categórica (ex.: um painel por Cultura).

**Diferença em relação à página Análise Espacial:** aqui é só **visualização exploratória** — não há interpolação, autocorrelação ou kriging. Use esta aba para ter uma visão rápida da distribuição geográfica antes de partir para análises estatístico-espaciais (cap. 9).

### 6.8 Temporal (exploratório)

Série temporal agregada (média ou mediana diária) de uma variável, opcionalmente colorida por uma categórica.

> Para o dataset Rio Verde, com apenas três datas distintas, a série fica como três pontos. Em datasets com séries longas (campanhas mensais ou semanais), esta aba vira o gráfico de visão geral antes da decomposição STL (cap. 10).

### 6.9 Composição

Gráfico duplo (barras + pizza) mostrando a composição de uma coluna categórica. Útil para apresentações — comunica visualmente "60 % do dataset é soja, 40 % é cana".

### 6.10 Inferência

Esta aba combina **três análises estatísticas** distintas em uma única tela: Kruskal-Wallis (comparação entre grupos), testes de normalidade (Shapiro-Wilk, Anderson-Darling, D'Agostino-Pearson) e VIF (multicolinearidade). É a aba mais densa do EDA.

#### Kruskal-Wallis (KW)

Teste não-paramétrico para comparar **distribuições** de uma variável numérica entre **dois ou mais grupos** definidos por uma coluna categórica. Hipótese nula: todos os grupos vêm da mesma distribuição.

**Configurações:**

* **Coluna de agrupamento** — categórica (`Cultura`, `Época`, `Estágio`, etc.).
* **Variáveis numéricas** — uma ou mais (multiselect).
* **Alpha (α)** — nível de significância (padrão 0,05).
* **N mínimo por grupo** — exclui automaticamente níveis com menos de N amostras (padrão 5). Veja por quê na próxima caixa.

![Slider N mínimo + tabela com dropped_levels](img/manual/18_eda_kruskal_min_n.png)

**Por que existe o "N mínimo por grupo":** com grupos de tamanho 2 ou 3, o KW tem **baixo poder estatístico** e o p-value se torna impreciso. O slider permite descartar esses grupos antes do teste. A coluna `dropped_levels` na tabela de resultados mostra quais foram excluídos — útil para auditoria. Se houver descarte, o app emite um aviso explicativo abaixo da tabela.

**Como ler a tabela de resultados:**

| Coluna | Significado |
|---|---|
| `variable` | A variável testada. |
| `groups` | Número de grupos que sobreviveram ao filtro de N mínimo. |
| `H` | Estatística de Kruskal-Wallis (não-paramétrica). |
| `p_value` | Probabilidade sob H₀. |
| `significant` | `True` se p < α. |
| `dropped_levels` | Níveis excluídos por terem n < mínimo. |

> **Quando k = 2 grupos**, o Kruskal-Wallis é matematicamente equivalente ao **Mann-Whitney U** *two-sided*. O app mantém o rótulo "Kruskal-Wallis" para consistência, mas você pode reportar como Mann-Whitney quando descrever o teste no seu artigo.

#### Testes de normalidade

Três testes complementares aplicados a cada variável selecionada:

| Teste | Característica |
|---|---|
| **Shapiro-Wilk** | O mais sensível para n < 5000. Padrão da literatura. |
| **Anderson-Darling** | Boa potência nas caudas. Devolve estatística A² + valor crítico a 5 %. |
| **D'Agostino-Pearson (K²)** | Combina testes de assimetria e curtose. Robusto a empates. |

A coluna `normal_at_alpha` é `True` apenas quando **os três** testes concordam que não há rejeição da normalidade.

![Tabela de testes de normalidade](img/manual/15_eda_normalidade_tabela.png)

**Atenção ao tamanho da amostra:** com n grande (acima de algumas centenas), os três testes detectam desvios mínimos da normal e rejeitam quase sempre. Isso **não** significa que a distribuição é inutilizável para análises paramétricas — significa apenas que ela não é *perfeitamente* normal. O app inclui uma caption explicativa logo abaixo da tabela.

Para julgar a **magnitude** do desvio (e não só sua significância), olhe o **Q-Q plot** que aparece logo abaixo:

![Grade de Q-Q plots](img/manual/16_eda_normalidade_qqplots.png)

**Como ler um Q-Q plot:**

* Pontos sobre a linha vermelha (ou próximos a ela) → distribuição próxima da normal.
* Pontos formando uma curva em "S" → caudas mais leves ou pesadas que a normal.
* Pontos longe da linha nas pontas → outliers ou desvios nas caudas (típico em variáveis fisiológicas).

#### VIF — Variance Inflation Factor

Mede multicolinearidade entre variáveis explicativas. Para cada variável, o VIF é calculado regredindo-a contra todas as demais e devolvendo `1 / (1 - R²)`.

| Faixa de VIF | Interpretação |
|---|---|
| VIF < 5 | Multicolinearidade baixa — variáveis independentes o suficiente. |
| 5 ≤ VIF < 10 | Multicolinearidade moderada. |
| VIF ≥ 10 | Multicolinearidade severa — considere remover uma das variáveis. |

![Painel VIF com caption sobre derivadas](img/manual/17_eda_vif_painel.png)

> **Atenção a variáveis derivadas:** o app exibe uma caption alertando que `Ci/Ca`, `A/Ci`, `EUA = A/E` e `ETR` são razões/funções de outras variáveis no schema, o que infla o VIF **por construção matemática**, sem que isso reflita problema de qualidade dos dados. No dataset Rio Verde, por exemplo, `Ci/Ca` chega a VIF ≈ 149.000 — não é um número que sugere remover Ci/Ca, é um sinal de que Ca é praticamente constante e Ci/Ca virou uma reescala de Ci.

### 6.11 Hotspots

Ranking dos `top_n` grupos com maior valor médio (ou mediano) de uma variável-alvo, com gráfico de barras horizontais. Opcionalmente faceteado por uma segunda categórica.

**Quando usar:** identificar rapidamente quais fazendas, estágios ou regiões concentram os maiores valores de uma variável fisiológica. Saída exportável como CSV para inclusão em relatórios de campo.

### 6.12 Outliers (multi-método)

Detecção de outliers combinando **cinco** métodos com critérios bem diferentes:

| Método | Pressuposto | Robusto a outliers? |
|---|---|---|
| **Z-score** (\|z\| > 3) | Distribuição aproximadamente normal. | Não — desvio-padrão é puxado pelos próprios outliers. |
| **IQR (1,5×)** | Nenhum (não-paramétrico). | Sim. |
| **Isolation Forest** | Não-paramétrico, baseado em árvores. | Sim. |
| **LOF** (Local Outlier Factor) | Não-paramétrico, baseado em densidade local. | Sim. |
| **Elliptic Envelope** | **Normalidade multivariada.** | **Não — sensível a dados bimodais ou assimétricos.** |

![Painel de outliers com caption de pressupostos](img/manual/19_eda_outliers_assumptions.png)

**Consenso ≥3 votos:** o app marca uma linha como outlier por consenso quando pelo menos **3 dos 5 métodos** concordam. É uma regra deliberadamente conservadora: cada método sozinho gera falsos positivos com perfil diferente; exigir maioria reduz drasticamente as falsas marcações.

> **Limitação no dataset Rio Verde:** como tem só 81 linhas e duas culturas com distribuições muito distintas, os métodos baseados em normalidade (Z-score, Elliptic Envelope) tendem a sub-detectar, enquanto os baseados em densidade (LOF) podem marcar **culturas inteiras** como "outliers". Use a tabela de auditoria para investigar caso a caso antes de remover.

A tabela de saída lista as primeiras 200 linhas com cada flag binária (z_score, iqr, isolation_forest, lof, elliptic_envelope), a contagem de votos, e o consenso final. Disponível para download como CSV.

## 7. Regressão bivariada

> Página **Regressão** no menu lateral.

Esta página é dedicada à **regressão linear simples** entre **duas variáveis numéricas**, com opções de coloração por categoria (`hue`) e facetamento. É útil para inspecionar relações fisiológicas clássicas (gs vs. A, Ci vs. A) e validar visualmente se a relação é aproximadamente linear antes de partir para modelagem mais sofisticada (cap. 8).

### 7.1 Presets fisiológicos

No topo da página, um seletor **Preset** oferece quatro combinações pré-configuradas baseadas em pares fisiologicamente significativos:

| Preset | X | Y | Cor | Interpretação |
|---|---|---|---|---|
| Condutância Estomática (gs) vs. Fotossíntese (A) | gs | A | Cultura | Relação clássica: maior gs → mais CO₂ entra → maior A, até um ponto de saturação. |
| CO₂ Interno (Ci) vs. Fotossíntese (A) | Ci | A | Cultura | Curva A-Ci — fundamental no modelo Farquhar de fotossíntese. |
| Condutância Estomática (gs) vs. Transpiração (E) | gs | E | Cultura | Quase sempre fortemente linear: gs governa a transpiração. |
| Clorofila a vs. Fotossíntese (A) | Chl_a_media | A | Cultura | Esperada associação positiva — mais clorofila, mais captura de luz. |

> Os presets só aparecem quando **ambas** as colunas estão presentes no dataset. Se você selecionou um modo de réplica que não cria as colunas (`Chl_a_media` etc.), o respectivo preset some.

### 7.2 Regressão customizada

Abaixo dos presets, uma seção **Regressão customizada** dá controle total:

* **Variável X** (selectbox numérico).
* **Variável Y** (selectbox numérico, excluindo a X).
* **Cor (hue)** — opcional, categórica.
* **Facetar (col)** — opcional, categórica que abre um painel por nível.
* **Intervalo de confiança** (slider 0-99 %) — banda sombreada ao redor da reta.
* **Amostra máxima** (slider 100-5000) — limita pontos plotados para performance.

A saída é um `lmplot` do seaborn: scatter + reta de regressão + banda de IC. Quando `hue` está ativado, cada categoria recebe sua própria reta (regressão **por grupo**).

### 7.3 Como ler o resultado

Abaixo do gráfico, uma caption mostra a **correlação de Pearson** entre X e Y e o `n` do gráfico. Use-a para uma checagem rápida — se o r for próximo de zero mas o gráfico parecer linear, provavelmente há alguma transformação log/sqrt subjacente que faria a relação aparecer.

> **Limitações desta página:**
>
> * É **apenas linear** — não há ajuste polinomial, log-linear, ou modelos mistos. Para esses casos, use a página Comparativa (regressão log-linear por grupo, cap. 11) ou exporte o dataset processado e use R/Python externamente.
> * Não imprime coeficientes (intercepto, inclinação, p-value) — apenas o gráfico e a correlação. Para regressão **com diagnósticos completos**, use a página Modelagem (cap. 8) selecionando o modelo `Regressão Linear`.

---

## 8. Modelagem preditiva

> Página **Modelagem** no menu lateral.

Esta página permite **treinar e comparar múltiplos modelos de regressão** simultaneamente, com validação cruzada e métricas de holdout. O caso de uso típico no projeto é prever a **fotossíntese (A)** a partir das demais variáveis fisiológicas — útil para validar relações mecanísticas e identificar variáveis-chave.

### 8.1 Escolhendo target e features

* **Variável-alvo (target)** — uma variável numérica. Padrão: `A`.
* **Features** — múltiplas variáveis explicativas, numéricas e categóricas. Padrão (no dataset Rio Verde): `gs`, `Ca`, `Ci`, `Ci/Ca`, `E`, `YII`, `ETR`, `Chl_a_media`, `Chl_b_media`, `IAF_media`, `Cultura`, `Fazenda`, `Época`.

Categóricas são automaticamente codificadas via `OneHotEncoder`. Numéricas que precisam de escala (LR e KNN) recebem `StandardScaler` no pipeline.

### 8.2 Modelos disponíveis

Cinco modelos do `scikit-learn`, todos com hiperparâmetros razoáveis pré-configurados:

| Modelo | Características | Quando preferir |
|---|---|---|
| **Regressão Linear** | Coeficientes interpretáveis; pressupõe linearidade. | Quando se busca *explicação* mais que *predição* pura. |
| **Floresta Aleatória** | 200 árvores; bom desempenho out-of-the-box; captura não-linearidades e interações. | Padrão recomendado para modelagem preditiva. |
| **Árvore de Decisão** | Modelo simples, fácil de visualizar. | Apenas como baseline ou para entender regras. |
| **Gradient Boosting** | Frequentemente mais preciso que Random Forest; mais sensível a overfit. | Quando quer máxima acurácia e tem tempo de tunar. |
| **KNN** | Sem treino; previsão depende dos k=5 vizinhos. | Datasets pequenos e suaves. |

### 8.3 Holdout e validação cruzada

Dois sliders controlam o esquema de validação:

* **Tamanho do holdout** (0,10 a 0,40) — fração dos dados reservada para teste. Padrão 0,30.
* **Dobras da validação cruzada** (3 a 10) — número de folds. Padrão 5.

### 8.4 Estratégia de validação cruzada

Aqui está a decisão mais importante desta página. Um radio oferece duas opções:

![Modelagem com GroupKFold por Fazenda + Ponto](img/manual/20_modelagem_groupkfold.png)

| Estratégia | Descrição | Quando usar |
|---|---|---|
| **KFold aleatório** | Linhas distribuídas aleatoriamente entre folds. | Quando **não há pseudoreplicação** — cada linha do dataset é uma observação genuinamente independente. |
| **GroupKFold (por sítio)** | Todas as réplicas de um mesmo sítio ficam **no mesmo fold**. O modelo nunca vê em treino linhas correlacionadas com as do teste. | **Recomendado** sempre que há mais de uma medição por ponto amostral (modos de réplica *desdobrar*; sítios com múltiplas datas; etc.). |

#### Coluna de agrupamento

Quando você escolhe GroupKFold, aparece um selectbox **Coluna de agrupamento** com candidatos:

* **Fazenda + Ponto** — opção sintética que combina as duas colunas, criando um identificador único de sítio. Padrão recomendado.
* **Fazenda** — agrupa por fazenda; pode dar poucos grupos se o dataset tem só 2-3 fazendas.
* **ID**, **LABEL** — identificadores únicos por linha; quase equivalente a KFold aleatório.
* Outras categóricas presentes no dataset.

> **Ajuste automático de folds:** se o número de grupos é menor que o número de folds escolhido, o app reduz automaticamente os folds e exibe um aviso amarelo (ex.: "Apenas 4 grupos disponíveis; reduzindo as dobras de 5 para 4").

#### Por que isso importa para o dataset Rio Verde

Confirmamos durante a auditoria que o leak nesse dataset específico é pequeno (R² ~0,946 com random vs. ~0,944 com GroupKFold para Regressão Linear). **Mas:** esse cenário é privilegiado pelo sinal mecanístico muito forte entre `A` e os predictors. Em datasets futuros com mais réplicas por sítio (ex.: 3 réplicas × várias datas × 2 culturas), a diferença pode ser muito maior — e o KFold aleatório vai **superestimar** o R² esperado em campo. GroupKFold dá uma estimativa mais conservadora e realista.

### 8.5 Lendo a tabela de resultados

A tabela compara os modelos selecionados em cinco métricas:

| Métrica | Significado |
|---|---|
| `R² Holdout` | Coeficiente de determinação no holdout (30 % dos dados). |
| `MAE Holdout` | Erro absoluto médio (mesma unidade do target). |
| `RMSE Holdout` | Raiz do erro quadrático médio. |
| `CV R² média` | Média do R² nas K dobras da CV. |
| `CV R² desvio` | Desvio-padrão do R² nas dobras (estabilidade do modelo). |

O **melhor modelo** é destacado em duas métricas grandes acima da tabela ("Melhor CV R²" e "Melhor R² Holdout"). A linha de baseline costuma ser a Regressão Linear; modelos mais sofisticados (RF, GB) precisam superá-la com folga para justificar o uso.

### 8.6 Preditos vs. observados

Para qualquer modelo treinado, você pode plotar um gráfico de **predito × observado**. Pontos ao longo da diagonal vermelha indicam predição perfeita. Desvios sistemáticos (todos os pontos abaixo ou acima da linha) indicam viés que merece investigação.

### 8.7 Importância de features

Para modelos baseados em árvore (RF, GB, DT), aparece um gráfico de barras com as **importâncias de features** (feature_importances_ do sklearn). Para Regressão Linear, mostra os **|coeficientes|** absolutos após padronização. KNN não fornece importância.

> **Cuidado de interpretação:** importâncias de árvores **dividem o crédito** entre variáveis correlacionadas. Se `Ci` e `Ci/Ca` carregam quase a mesma informação (VIF > 10⁴ no Rio Verde, ver §6.10), o modelo divide a importância entre as duas, e nenhuma aparece como "muito importante" sozinha. Olhe o conjunto, não cada barra isoladamente.

---

## 9. Análise espacial

> Página **Análise Espacial** no menu lateral.

Esta página reúne **seis abas** de análise geoespacial: interpolação determinística (IDW), autocorrelação global e local (Moran's I), hotspots (Getis-Ord Gi*), agregação em grade UTM regular, krigagem ordinária com semivariograma esférico, e mapa sobre os limites administrativos de Rio Verde, GO.

Desde a v1.1, **todas as análises de distância** (IDW, kriging, Moran KNN, Gi*) operam internamente em **metros UTM** (EPSG 32722 para Rio Verde), mesmo quando o eixo dos mapas aparece em latitude/longitude. Isso elimina a anisotropia introduzida quando se computa distância Euclidiana em graus (1° de longitude ≈ 105 km vs. 1° de latitude ≈ 111 km em -17,8°).

### 9.1 IDW — Interpolação por Distância Inversa

> Aba **IDW**.

Estima o valor de uma variável em uma grade regular usando a média ponderada dos pontos amostrais conhecidos, com **peso inversamente proporcional à distância**.

![Mapa IDW de uma variável](img/manual/21_espacial_idw.png)

**Configurações:**

* **Variável-alvo** — qual variável interpolar.
* **Facetar por** — categórica opcional; gera um mapa por nível (útil para comparar Soja vs. Cana lado a lado).
* **Tamanho do grid** (80-320) — resolução da interpolação. Maior = mais bonito, mas mais lento. Padrão 180.
* **Power** (0,5-4,0) — expoente do inverso da distância. Padrão 2.
  * `power=1`: suavização forte, valores tendem à média.
  * `power=2`: padrão, equilíbrio.
  * `power=4`: cada ponto domina seu entorno imediato.

**Como ler o mapa:** as cores seguem a paleta `viridis`. Os círculos brancos são os **pontos amostrais reais**; o resto da superfície é interpolado. Áreas longe de qualquer ponto amostrado têm valor pouco confiável — o IDW força a continuidade mesmo onde não há dado.

> **Limitação:** IDW é **determinístico** — não há banda de incerteza. Para incerteza estatística, use Krigagem (§9.5).

### 9.2 Moran's I — Autocorrelação espacial

> Aba **Moran**.

Mede se valores **semelhantes** tendem a ficar próximos no espaço. Devolve um índice global e mapas de clusters locais (LISA).

![Mapa LISA + diagrama de dispersão de Moran](img/manual/22_espacial_moran.png)

**Configurações:**

* **Variável-alvo**.
* **k vizinhos mais próximos** (3-12) — quantos vizinhos definem o "entorno" de cada ponto.
* **Número de permutações** (99-999) — quanto maior, mais preciso o p-value (Monte Carlo).

**Métricas globais:**

| Métrica | Interpretação |
|---|---|
| `I` próximo de +1 | Autocorrelação positiva forte (valores parecidos se agrupam). |
| `I` próximo de 0 | Distribuição aleatória no espaço. |
| `I` próximo de -1 | Autocorrelação negativa (valores parecidos ficam afastados; raro). |
| `p_sim` < 0,05 | I é estatisticamente significativo. |

**Mapa LISA — quatro categorias:**

| Cluster | Cor | Significado |
|---|---|---|
| **HH** | Vermelho | Sítio com valor alto rodeado de vizinhos altos (hotspot). |
| **LL** | Azul | Sítio com valor baixo rodeado de vizinhos baixos (coldspot). |
| **HL** | Laranja | Sítio alto rodeado de baixos (outlier alto). |
| **LH** | Azul claro | Sítio baixo rodeado de altos (outlier baixo). |
| **NS** | Cinza | Não significativo. |

> **Cuidado com confundimento:** se a aba Qualidade (§6.2) reporta `Fazenda ⟷ Cultura` como redundantes, e cada cultura está concentrada em uma fazenda, o **Moran's I vai ser altíssimo** (~0,9). Mas esse cluster espacial pode ser apenas o reflexo do efeito-Cultura disfarçado de efeito-espaço. Confirme rodando o Moran condicionalmente: filtre por uma única cultura, restrinja o dataset, e veja se o I permanece alto.

### 9.3 Getis-Ord Gi* — Hotspots formais

> Aba **Gi***.

Detecta **hotspots** (cluster de valores altos) e **coldspots** (cluster de valores baixos) usando uma banda de distância em vez de KNN. Mais formal e direto que LISA quando o objetivo é **só identificar onde estão as concentrações**.

**Cálculo da banda d*:** o app pega cada ponto, encontra a distância ao seu k-ésimo vizinho, e usa o **máximo** dessas distâncias × 1,001. Isso garante que todo ponto tenha pelo menos k vizinhos no cálculo do Gi*. O valor de d* aparece em metros, com uma caption indicando o EPSG UTM utilizado.

Saída: mapa com pontos coloridos como **Hotspot** (vermelho), **Coldspot** (azul) ou **NS** (cinza); tabela-resumo com média e mediana por classe; CSV exportável.

### 9.4 Grade UTM regular

> Aba **Grade UTM**.

Em vez de interpolar uma superfície contínua, agrega os pontos amostrais em **células quadradas regulares** (em km) e calcula a média/mediana de uma variável por célula. Útil para apresentar valores médios "por quadrante" em comunicação para gestores.

**Configurações:**

* **Variável-alvo**.
* **Tamanho da célula** (0,5-10 km) — lado do quadrado.
* **Facetar por** — opcional.
* **Agregação** — média ou mediana.

Saída: mapa coreoplético (polígonos coloridos) + tabela das top-50 células ordenadas por valor + CSV.

### 9.5 Krigagem ordinária

> Aba **Kriging**.

Interpolação **estatística** baseada na estrutura espacial dos dados. Diferente do IDW, devolve estimativas com base num **variograma** ajustado — captura quão similar é a relação entre pares de pontos em função da distância.

![Variograma com eixo em metros e caption EPSG](img/manual/23_espacial_variograma_metros.png)

**Fluxo de duas etapas:**

#### Etapa 1: ajustar o variograma

* **Variável-alvo**.
* **Número de lags** (6-30) — classes de distância no variograma empírico.
* **Fração máxima** (0,3-0,95) — usa só pares até essa fração da distância máxima (descartando a "borda" do variograma, que tem poucos pares).
* **Winsorize** (checkbox) — corta caudas em 2 % e 98 % antes do ajuste; útil quando há outliers extremos.

O variograma empírico aparece como pontos verdes, e o **modelo esférico ajustado** como linha vermelha. Três parâmetros são reportados (todos em **metros**):

| Parâmetro | Significado |
|---|---|
| **Pepita (C₀)** | Variância em distância zero — reflete erro de medição + variância de escala fina. |
| **Patamar (C)** | Diferença entre o nível assintótico e a pepita. |
| **Alcance (a)** | Distância em que o variograma estabiliza. Além desse raio, pontos são considerados independentes espacialmente. |

**Diagnóstico:** se o variograma **não estabiliza** dentro da janela considerada (continua subindo até o final), o alcance ajustado vai sair como um número absurdamente alto (10⁵ a 10⁷ metros). Isso significa que **não há estrutura espacial detectável** nessa escala — provavelmente o dataset é pequeno demais, ou a variável é mal correlacionada com posição. Não rode a krigagem nessa situação.

#### Etapa 2: rodar a krigagem (sob demanda)

A krigagem é computacionalmente cara, então só roda quando você marca o checkbox **Executar krigagem ordinária**. O mapa de saída usa o mesmo grid de lat/lon nos eixos, mas o cálculo interno é todo em UTM.

### 9.6 Mapa sobre Rio Verde

> Aba **Basemap**.

Mostra os pontos amostrais coloridos por uma variável, **sobrepostos aos limites administrativos de Rio Verde, GO** (carregados via biblioteca `geobr`). Útil para apresentações que precisam mostrar o contexto geográfico do município.

> Requer conexão de internet na primeira execução (baixa o shapefile do município via geobr). Depois fica em cache.

## 10. Série temporal

> Página **Série Temporal** no menu lateral.

Esta página é específica para análise **univariada longitudinal** — agrega uma variável por dia e, opcionalmente, decompõe a série em componentes de tendência, sazonalidade e resíduo. **Diferente da aba Temporal do EDA** (§6.8), aqui o foco é a **estrutura temporal formal** da série, não apenas a visualização exploratória.

### 10.1 Detecção da coluna de data

O app procura automaticamente uma coluna de data candidata: `Data da coleta`, `Data`, `Date`, `DATE_TIME initial_value` e similares (lista canônica em [`src/pipeline.py`](../src/pipeline.py) na função `find_date_column`). Desde a v1.1, a detecção também coage colunas com **dtype `object` contendo mistura de `datetime.datetime` + `str` + `NaN`** — caso típico do Excel exportado em datasets de campo.

Se nenhuma coluna for detectada, a página exibe **"Coluna de data não encontrada"** e fica vazia. Verifique no Excel se a coluna de data está nomeada conforme uma das variantes aceitas e se as células estão como **datas reais** (não como texto).

### 10.2 Agregação diária

> Aba **Agregação diária**.

Configurações:

* **Variáveis para plotar** (multiselect) — uma ou mais.
* **Método de agregação** (radio) — média ou mediana por dia.

Cada variável vira uma linha colorida; o eixo X mostra as datas com formatação automática. Para o dataset Rio Verde, com apenas 3 datas de coleta, o gráfico aparece como 3 pontos ligados — útil para visualizar a evolução temporal, mas pouco interpretável estatisticamente.

### 10.3 Decomposição STL

> Aba **Decomposição STL**.

A decomposição STL (*Seasonal-Trend decomposition using LOESS*, Cleveland et al., 1990) separa uma série temporal em três componentes:

* **Tendência** — variação lenta de longo prazo.
* **Sazonalidade** — padrão cíclico que se repete com período fixo.
* **Resíduo** — ruído após remover tendência e sazonalidade.

**Configurações:**

* **Variável-alvo** (default: `FCO2_DRY` se existir, senão a primeira numérica).
* **Período sazonal (dias)** — slider 2 a 60. Padrão 7 (sazonalidade semanal).
* **Interpolar lacunas temporais** (checkbox) — preenche dias sem medição por interpolação linear no tempo.

#### Guard-rails da STL

Para evitar interpretações enganosas, o app impõe **dois bloqueios**:

![Aviso de poucas datas para STL](img/manual/24_temporal_stl_bloqueado.png)

| Condição | O que acontece |
|---|---|
| Menos de **10 datas com medição real** | A STL é bloqueada com aviso: *"Apenas N datas com medição real (mínimo 10). A decomposição STL exige pontos suficientes — campanhas pontuais não atendem ao requisito."* |
| Interpolação cobre **mais de 70 %** da série | A STL roda, mas com aviso destacado: as métricas de força de tendência/sazonalidade refletem em grande parte a própria interpolação, não o sinal observado. |

> **No dataset Rio Verde:** apenas 3 datas distintas (Dez/2025, Jan/2026, Fev/2026) → o app bloqueia a STL com mensagem clara. Este é o comportamento correto; a decomposição precisaria de campanhas mensais (~12 datas) ou semanais (~10+) para ser estatisticamente honesta.

#### Saída quando a STL roda

Quando há dados suficientes, a página produz quatro gráficos empilhados (Observado, Tendência, Sazonalidade, Resíduo) e três métricas:

* **Força de tendência** — `1 − Var(resíduo) / Var(observado − sazonal)`. Próximo de 1 = tendência muito clara.
* **Força de sazonalidade** — `1 − Var(resíduo) / Var(observado − tendência)`. Próximo de 1 = sazonalidade muito clara.
* **n** — número de pontos da série após agregação/interpolação.

---

## 11. Comparação por grupos

> Página **Comparação por grupo** no menu lateral.

Esta página implementa o caso de uso clássico **"o Grupo A difere do Grupo B?"** com ferramentas estatísticas robustas. Diferentemente da aba Boxplot do EDA (§6.4), aqui você tem:

* **Definição flexível dos grupos** — escolha manual de quais valores entram em A e B, ou pattern matching por substring.
* **Teste estatístico formal** — Mann-Whitney U *two-sided* para cada variável.
* **Regressão log-linear por grupo** — ajusta a relação log(Y) ~ X separadamente em A e B.
* **Padrão horário** — agrega Y por hora do dia para cada grupo (útil para fluxos diurnos vs. noturnos).

### 11.1 Configuração dos grupos

![Configuração de Comparativa: Cana vs. Soja](img/manual/25_comparativa_setup.png)

**Coluna categórica** — selectbox no topo. Define qual coluna será particionada em dois grupos. Padrão: `Cultura`.

**Duas vias de definir A e B:**

#### Modo manual (padrão)

Dois multiselects, lado a lado:

* **Valores no Grupo A** + rótulo customizável (default: primeiro valor da coluna).
* **Valores no Grupo B** + rótulo customizável (default: o segundo valor).

Você pode atribuir múltiplos valores a um mesmo grupo (ex.: agrupar "R1", "R2", "R3" num só "Estágio reprodutivo precoce").

> **Validação automática:** se algum valor aparecer nos dois lados, o app exibe `st.error` e impede o avanço.

#### Modo pattern matching

Marque o checkbox **Classificar automaticamente por padrão de texto**. Aparece um campo de texto onde você digita um padrão (case-insensitive):

* Valores que **contêm** o padrão → Grupo A (Match).
* Valores que **não contêm** → Grupo B (Other).

Útil quando a coluna tem muitos níveis (ex.: 14 estágios fenológicos) e você quer rapidamente separar "tudo que contém 'maturação'" do resto. O app mostra a lista de cada grupo em caption para você conferir antes de analisar.

#### Métricas de N por grupo

Após a configuração, duas métricas grandes mostram quantas linhas caíram em cada grupo:

> **No dataset Rio Verde (modo Desdobrar):** Cana-de-açúcar = 54, Soja = 104. Em modo Média seria 27 vs. 54 — siga atento ao número porque ele governa o poder estatístico dos testes que vêm em seguida.

### 11.2 Resumo & teste — Mann-Whitney U

> Primeira aba dentro da Comparativa.

Para cada variável numérica selecionada, devolve dois blocos:

**Tabela de resumo descritivo** (`group`, `variable`, `n`, `mean`, `se`, `median`):

**Tabela de teste de Mann-Whitney U:**

![Tabela Mann-Whitney na Comparativa](img/manual/26_comparativa_mannwhitney.png)

| Coluna | Significado |
|---|---|
| `variable` | A variável testada. |
| `g1`, `g2` | Rótulos dos grupos. |
| `n_g1`, `n_g2` | Tamanho de cada grupo. |
| `U` | Estatística de Mann-Whitney. |
| `p_value` | Probabilidade sob H₀ (mesma distribuição). |
| `significant_5%` | `True` se p < 0,05. |

#### Quando o Mann-Whitney é apropriado

| Condição | Implicação |
|---|---|
| Os dois grupos têm forma de distribuição **similar** | Mann-Whitney compara medianas (interpretação direta). |
| Distribuições têm formas **diferentes** | Mann-Whitney compara distribuições globais (rejeição não significa "mediana diferente", mas "distribuição diferente"). |
| Há **pseudoreplicação** (réplicas no mesmo sítio) | n inflado → p artificialmente pequeno. Considere agregar por sítio (modo de réplica Média ou Mediana) antes de comparar. |

> **No dataset Rio Verde:** rodando Cana vs. Soja em Latitude e Longitude, os p-values são da ordem de 10⁻⁸ — o que **não** significa que cana e soja têm "latitudes diferentes" no sentido fisiológico. Significa que **as duas fazendas estão em locais geograficamente distintos** e cada uma tem só uma cultura (lembre o confundimento Fazenda ⟷ Cultura). Para um achado biologicamente significativo, teste variáveis fisiológicas (`A`, `gs`, `E`, etc.) e leia em conjunto com a aba de Confundimento (§6.2).

### 11.3 Log-linear por grupo

> Segunda aba dentro da Comparativa.

Ajusta uma regressão linear simples em escala **log(Y)** versus X, **separadamente para cada grupo**. Útil quando a relação Y-X é exponencial ou multiplicativa (saturação, decaimento).

**Configurações:**

* **Variável Y** (numérica) — só valores **estritamente positivos** entram (log(0) e log negativo são descartados silenciosamente).
* **Variável X** (numérica).

Saída: scatter colorido por grupo + retas ajustadas + tabela com `intercept`, `slope`, `R²`, `p_value`, `se_slope` por grupo.

> **Cuidado quando Y tem valores ≤ 0:** o app descarta essas linhas antes do log. Se um grupo tem muitos negativos (caso de FCO2_DRY em uptake, FCH4_DRY em sumidouro), você compara N drasticamente diferentes entre os grupos, **comprometendo a comparabilidade**. Verifique sempre o `n` reportado em cada grupo no gráfico.

### 11.4 Padrão horário

> Terceira aba dentro da Comparativa.

Para datasets com coluna de **data/hora** (não apenas data), extrai a hora de cada medição e calcula a média/mediana de Y por hora-do-dia, separadamente para cada grupo.

Saída: dois gráficos lado a lado:

* **Esquerda:** média (ou mediana) por hora, linha por grupo.
* **Direita:** soma cumulativa por hora — útil para visualizar fluxo acumulado ao longo do dia (ex.: emissão de CO₂ diurna).

Tabela exportável como CSV.

> **No dataset Rio Verde:** a coluna `Data da coleta` tem apenas a parte de data (sem hora), então todas as medições caem na hora `00:00`. A aba fica visualmente vazia, exceto pela barra única em zero. Em datasets de fluxo de solo com timestamp completo (IRGA medindo a cada 1-2 horas) a aba é muito mais útil.

---

## 12. Glossário estatístico

Definições curtas dos termos técnicos usados no manual. Para aprofundamento, ver as Referências (§14).

* **Anderson-Darling** — teste de normalidade sensível a desvios nas caudas. Devolve estatística A² e valor crítico a 5 %; rejeita se A² > crítico.
* **Cramér's V** — medida de associação entre duas variáveis categóricas, no intervalo [0, 1]. V=1 indica equivalência perfeita; usado no app para detectar confundimento.
* **D'Agostino-Pearson (K²)** — teste de normalidade que combina assimetria e curtose. Robusto a empates; recomendado para n moderado.
* **Elliptic Envelope** — método de detecção de outliers que assume **normalidade multivariada**. Pouco confiável em dados bimodais ou fortemente assimétricos.
* **Getis-Ord Gi*** — estatística local que classifica cada ponto como hotspot (cluster de altos), coldspot (cluster de baixos) ou não significativo, com base em sua vizinhança via banda de distância.
* **GroupKFold** — variante de validação cruzada que mantém todas as linhas de um mesmo "grupo" (sítio, fazenda, ponto) no mesmo fold. Evita inflar o R² quando há pseudoreplicação.
* **IDW (Inverse Distance Weighting)** — interpolação determinística que estima cada ponto do grid como média ponderada dos pontos amostrados, com peso ∝ 1/distância^power.
* **Isolation Forest** — algoritmo de detecção de outliers baseado em árvores aleatórias. Não-paramétrico, escala bem para muitas dimensões.
* **Kruskal-Wallis (KW)** — teste não-paramétrico que compara distribuições entre 2 ou mais grupos. Equivale ao Mann-Whitney quando há exatamente 2 grupos.
* **Kriging ordinária** — interpolação **estatística** baseada na estrutura espacial dos dados, ajustada via variograma. Devolve estimativas + incerteza.
* **LISA (Local Indicators of Spatial Association)** — versão local do Moran's I; classifica cada ponto em HH, HL, LH, LL ou NS conforme seu valor e o da sua vizinhança.
* **LOF (Local Outlier Factor)** — método de outliers baseado em densidade local. Marca pontos cuja vizinhança é menos densa que a dos seus vizinhos.
* **Mann-Whitney U** — teste não-paramétrico para comparar duas amostras independentes. Equivalente ao Kruskal-Wallis com k=2.
* **Moran's I** — índice de autocorrelação espacial global, no intervalo [-1, +1]. Positivo → valores similares se agrupam no espaço.
* **Pearson (r)** — coeficiente de correlação linear. Sensível a outliers; pressupõe relação linear.
* **Pseudoreplicação** — quando réplicas (medições) do mesmo sítio são tratadas como observações independentes. Infla o n efetivo e gera p-values otimistas.
* **Q-Q plot** — gráfico que compara os quantis amostrais aos teóricos da normal. Pontos alinhados na diagonal indicam normalidade visual.
* **Shapiro-Wilk (W)** — teste de normalidade. O mais sensível para n < 5000; padrão na literatura.
* **Spearman (ρ)** — coeficiente de correlação por postos. Robusto a outliers e capta relações monotônicas não-lineares.
* **STL (Seasonal-Trend decomposition using LOESS)** — decompõe uma série temporal em tendência, sazonalidade e resíduo via regressão local robusta.
* **UTM (Universal Transverse Mercator)** — sistema de projeção cartográfica em metros. Rio Verde, GO fica no fuso 22 Sul (EPSG 32722).
* **Variograma** — função que descreve a semivariância entre pares de pontos em função da distância. Parâmetros: nugget (variância em h=0), sill (assíntota) e range (distância em que estabiliza).
* **VIF (Variance Inflation Factor)** — mede multicolinearidade. VIF=1/(1-R²) onde R² vem da regressão da variável contra todas as outras. VIF ≥ 10 indica colinearidade severa.
* **Z-score** — número de desvios-padrão acima/abaixo da média. Critério |z|>3 marca outliers; **não-robusto** (o próprio outlier infla o desvio-padrão).

---

## 13. Solução de problemas (FAQ)

### "Aparece `sidebar.rep.media` (ou outra chave crua) em vez do texto traduzido"

O Streamlit cacheia o módulo de traduções no primeiro import. Se você atualizou o app após o servidor já estar rodando, as novas chaves não aparecem até reiniciar. **Solução:** `Ctrl+C` no terminal e `python -m streamlit run app.py` novamente.

### "O pipeline esvaziou meu dataset (ou removeu quase tudo)"

Vá em **Pipeline e Processamento** e leia o aviso amarelo destacado. A causa quase sempre é a etapa 2 — uma das colunas obrigatórias (`Cultura`, `Uso atual` ou `Época`) está vazia em muitas linhas. Volte ao Excel, identifique qual coluna está faltando, e refaça o upload com a planilha corrigida.

### "A página Série Temporal diz 'Coluna de data não encontrada'"

Verifique no Excel se sua coluna se chama `Data da coleta`, `Data`, `Date`, `DATE_TIME initial_value` ou alguma variante reconhecida (lista completa em [`docs/data_dictionary.md`](data_dictionary.md)). Se o nome estiver certo, abra a coluna e verifique se as células estão como **datas reais** (Excel mostra `2025-12-19` à direita) e não como **texto** ("2025-12-19" à esquerda). Salve o arquivo e recarregue.

### "GroupKFold reduziu meus folds automaticamente"

Significa que o número de grupos únicos na coluna escolhida é menor que o número de folds que você configurou. Por exemplo: você pediu 5 folds, mas só há 4 fazendas — o app ajusta para 4 folds. Se quiser manter os 5 folds, escolha uma coluna de agrupamento com mais níveis (ex.: `Fazenda + Ponto` em vez de só `Fazenda`).

### "Algumas variáveis aparecem com VIF infinito ou astronômico"

Isso é esperado para **variáveis derivadas matematicamente** de outras: `Ci/Ca` é Ci dividido por Ca (com Ca quase constante, vira reescala de Ci); `EUA = A/E`; `A/Ci` é uma razão; `ETR` é função de YII. VIF alto entre essas indica multicolinearidade **por construção**, não por problema dos dados. Inclua só uma representante do par derivado nos modelos.

### "Moran's I deu 0,9 — meus dados são extremamente agregados espacialmente?"

Antes de comemorar a descoberta de um cluster, confira a aba **Qualidade do EDA → Confundimento entre categorias**. Se `Fazenda ⟷ Cultura` (ou similar) aparecer como redundante, o Moran's I está captando **diferença biológica entre culturas** mais do que autocorrelação espacial verdadeira. Refaça o Moran filtrando para uma única cultura via filtro global, e veja se o índice permanece alto.

### "O variograma de kriging não estabiliza"

Provavelmente seu dataset não tem **estrutura espacial detectável** na escala do experimento (poucos pontos amostrais, ou variável dominada por outros fatores que não a posição). Não rode a krigagem nessa situação — os parâmetros ajustados (range em milhões de metros) são numericamente válidos mas estatisticamente inúteis. Considere voltar ao IDW (§9.1) ou rever a coleta.

### "Os modos de réplica `Réplica 1`, `Réplica 2` e `Réplica 3` parecem dar resultados diferentes para Chl a e b"

São diferentes mesmo — cada um pega uma medição específica da planilha. `Réplica 1` usa a coluna `Chl a` original; `Réplica 2` usa `Chl a.1`. **Réplica 3 deixa Chl a/b vazios** (só existe `IAF.2`, não `Chl a.2`). Use estes modos quando quiser auditar/comparar leituras específicas; para análise normal, use **Média** ou **Mediana**.

---

## 14. Referências

### Métodos estatísticos

* Anderson, T. W., & Darling, D. A. (1952). Asymptotic theory of certain "goodness of fit" criteria based on stochastic processes. *Annals of Mathematical Statistics*, 23(2), 193-212.
* Bergsma, W., & Wicher, M. (2013). A bias-correction for Cramér's V and Tschuprow's T. *Journal of the Korean Statistical Society*, 42(3), 323-328.
* Cleveland, R. B., Cleveland, W. S., McRae, J. E., & Terpenning, I. (1990). STL: A seasonal-trend decomposition procedure based on loess. *Journal of Official Statistics*, 6(1), 3-73.
* D'Agostino, R. B., Belanger, A., & D'Agostino Jr., R. B. (1990). A suggestion for using powerful and informative tests of normality. *American Statistician*, 44(4), 316-321.
* Getis, A., & Ord, J. K. (1992). The analysis of spatial association by use of distance statistics. *Geographical Analysis*, 24(3), 189-206.
* Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *JASA*, 47(260), 583-621.
* Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random variables is stochastically larger than the other. *Annals of Mathematical Statistics*, 18(1), 50-60.
* Moran, P. A. P. (1948). The interpretation of statistical maps. *Journal of the Royal Statistical Society, Series B*, 10(2), 243-251.
* Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality. *Biometrika*, 52(3-4), 591-611.

### Outliers e modelagem

* Breunig, M. M., Kriegel, H. P., Ng, R. T., & Sander, J. (2000). LOF: Identifying density-based local outliers. *SIGMOD Record*, 29(2), 93-104.
* Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest. *ICDM*, 413-422.
* Rousseeuw, P. J., & van Driessen, K. (1999). A fast algorithm for the minimum covariance determinant estimator. *Technometrics*, 41(3), 212-223.

### Fisiologia vegetal

* Farquhar, G. D., von Caemmerer, S., & Berry, J. A. (1980). A biochemical model of photosynthetic CO₂ assimilation in leaves of C3 species. *Planta*, 149(1), 78-90.

### Bibliotecas

* McKinney, W. (2010). pandas — Data analysis with Python. <https://pandas.pydata.org>
* Pedregosa, F. et al. (2011). Scikit-learn: Machine learning in Python. *JMLR*, 12, 2825-2830.
* Rey, S. J., & Anselin, L. (2010). PySAL: A Python library of spatial analytical methods. <https://pysal.org>
* Seabold, S., & Perktold, J. (2010). statsmodels: Econometric and statistical modeling. <https://www.statsmodels.org>
* Streamlit Inc. (2024). Streamlit. <https://streamlit.io>
* Virtanen, P. et al. (2020). SciPy 1.0. *Nature Methods*, 17, 261-272.

## 15. Contribuindo

Encontrou um bug, tem uma sugestão de melhoria ou quer adicionar uma análise nova?

### 15.1 Reportando bugs e propondo features

Abra uma issue no repositório do projeto no GitHub. Inclua:

1. **Versão do app** (verifique no rodapé ou no `pyproject.toml`).
2. **Passos para reproduzir** — comece sempre por "fui à aba X, cliquei em Y, esperava Z mas vi W".
3. **Captura de tela** (se for um problema visual).
4. **Trecho do dataset** (anonimizado) que dispara o problema, sempre que possível.

### 15.2 Contribuindo com código

* Veja [`docs/contributing.md`](contributing.md) para o fluxo de PRs e padrões de teste.
* Veja [`docs/architecture.md`](architecture.md) para entender o layout dos módulos.
* Veja [`docs/i18n.md`](i18n.md) para adicionar um novo idioma ou estender as traduções.

### 15.3 Gerando este manual em PDF

A fonte canônica deste manual é o arquivo Markdown que você está lendo (`docs/manual.pt.md`). O PDF é um derivado, gerado por [pandoc](https://pandoc.org/) + XeLaTeX.

#### Localmente

```bash
# 1) Pré-requisitos (uma vez por máquina)
brew install pandoc                       # macOS
brew install --cask basictex
sudo tlmgr install fancyhdr xurl booktabs longtable

# Ubuntu equivalente:
# sudo apt-get install pandoc texlive-xetex \
#   texlive-fonts-recommended texlive-latex-recommended

# 2) Gerar o PDF
scripts/build_manual_pdf.sh                       # → docs/manual.pt.pdf
scripts/build_manual_pdf.sh --lang en             # quando existir manual.en.md
scripts/build_manual_pdf.sh --output /tmp/x.pdf   # caminho customizado
```

O PDF é gerado em `docs/manual.<lang>.pdf` e o `.gitignore` impede que ele seja commitado por acidente.

#### Via GitHub Actions

O workflow [`build-manual.yml`](../.github/workflows/build-manual.yml) gera o PDF automaticamente:

* **Push para tag `v*`** — anexa o PDF como artifact da release correspondente.
* **Mudanças em `docs/manual.*.md`** ou nos screenshots — roda o build para validar que nada quebrou.
* **Execução manual** — vá em *Actions → Build manual PDF → Run workflow* e escolha o idioma.

Os artifacts ficam disponíveis por 30 dias e podem ser baixados sem precisar instalar pandoc localmente.

### 15.4 Traduzindo para outros idiomas

O esqueleto deste manual está pronto para receber espelhos em inglês e espanhol:

```bash
cp docs/manual.pt.md docs/manual.en.md
cp docs/manual.pt.md docs/manual.es.md
```

Traduza o conteúdo mantendo a estrutura de cabeçalhos. As imagens em `docs/img/manual/` são compartilhadas entre os três idiomas — só precisa de uma cópia.

---

*Fim do manual. Versão 1.0 — alinhada à versão 1.x do aplicativo.*

### 15.1 Gerando este manual em PDF

A fonte canônica deste manual é o arquivo Markdown que você está lendo (`docs/manual.pt.md`). O PDF é um derivado, gerado por [pandoc](https://pandoc.org/) + XeLaTeX.

#### Localmente

```bash
# 1) Pré-requisitos (uma vez por máquina)
brew install pandoc                       # macOS
brew install --cask basictex
sudo tlmgr install fancyhdr xurl booktabs longtable

# Ubuntu equivalente:
# sudo apt-get install pandoc texlive-xetex \
#   texlive-fonts-recommended texlive-latex-recommended

# 2) Gerar o PDF
scripts/build_manual_pdf.sh                       # → docs/manual.pt.pdf
scripts/build_manual_pdf.sh --lang en             # quando existir manual.en.md
scripts/build_manual_pdf.sh --output /tmp/x.pdf   # caminho customizado
```

O PDF é gerado em `docs/manual.<lang>.pdf` e o `.gitignore` impede que ele seja commitado por acidente.

#### Via GitHub Actions

O workflow [`build-manual.yml`](../.github/workflows/build-manual.yml) gera o PDF automaticamente:

* **Push para tag `v*`** — anexa o PDF como artifact da release correspondente.
* **Mudanças em `docs/manual.*.md`** ou nos screenshots — roda o build para validar que nada quebrou.
* **Execução manual** — vá em *Actions → Build manual PDF → Run workflow* e escolha o idioma.

Os artifacts ficam disponíveis por 30 dias e podem ser baixados sem precisar instalar pandoc localmente.
