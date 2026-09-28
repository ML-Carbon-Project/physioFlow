# Validação externa do módulo de Estatística Experimental

Este documento registra a comparação entre os resultados da ferramenta
PhysioFlow (página **Estatística Experimental**) e resultados **publicados**
para datasets clássicos de domínio público. Serve como evidência de corretude
para o software paper e como roteiro de re-validação.

Os dados públicos ficam em `data/sample/test/` e os testes automatizados que
travam estes números estão em `tests/test_sample_datasets.py`.

> **Natureza da validação.** Vários datasets vêm do *ASReml Cookbook*, cujos
> resultados "oficiais" usam **modelos mistos/espaciais (REML)**. A ferramenta
> faz **ANOVA clássica**, então a comparação justa é contra a mesma ANOVA
> clássica (R/Rbio/seaborn), não contra a saída espacial. O caso mais forte de
> validação independente é o **Palmer Penguins**, fartamente documentado.

## 0. Cross-validação contra o R (`aov`, `car::Anova` tipo II, `emmeans`)

Os delineamentos foram conferidos **número a número** contra o R (rodado
localmente; o Rbio é só-Windows, mas o R base + CRAN estão disponíveis). Usa-se
`car::Anova(type=2)` para casar com a soma de quadrados Tipo II do statsmodels.

| Análise | Termo | PhysioFlow | R |
|---|---|---|---|
| Split-plot (oats) | gen / nitro / gen×nitro F | 1,485 / 37,686 / 0,303 | idem |
| Faixas (strip-plot) | A / B / A×B F (gl erros 4/6/12) | 18,08 / 22,03 / 1,593 | idem |
| Hierárquico (nested) | A vs B(A) / B(A) vs resíduo F | 67,81 / 3,430 (gl 3/8/48) | idem |
| ANCOVA (penguins) | flipper(cov) F / species F / slope | 175,687 / 18,393 / 40,7054 | idem |
| ANCOVA — médias ajustadas | Adelie/Chinstrap/Gentoo | 4147 / 3940 / 4414 | idem (`emmeans`) |
| Fatorial tipo II (penguins) | species / sex / interação F | 749,0 / 387,5 / 8,757 | idem |
| DIC uma-via (penguins) | flipper ~ species F | 594,80 | 594,80 |
| Scott-Knott | partição (3 datasets) | = pacote `ScottKnott` | = (§3b) |

Travado em `tests/test_sample_datasets.py` (valores de referência do R fixados,
sem depender do R em CI).

## 1. Palmer Penguins (`penguins.csv`)

Dataset clássico (Gorman et al., Palmer Station LTER), 344 registros, 3 espécies.

| Análise | PhysioFlow | Publicado | Confere |
|---|---|---|---|
| Pearson `flipper_length_mm` × `body_mass_g` | **0,871** | ~0,87 (0,863 M / 0,872 F) | ✅ |
| ANOVA `body_mass_g ~ species` | p ≈ 3×10⁻⁸², CV ≈ 11% | F(2,339) significativo, p<0,001 | ✅ |
| Tukey HSD em `body_mass_g` | Gentoo **a** (≈5076 g); Adelie e Chinstrap **b** (≈3701 / 3733 g) | Gentoo mais pesado e isolado; Adelie ≈ Chinstrap | ✅ |
| Fatorial `species × sex` | species, sex e interação significativos (interação p ≈ 0,0002) | efeitos principais e interação significativos | ✅ |
| Pearson `bill_depth_mm` × `body_mass_g` | **−0,472** (negativo) | negativo no agregado (paradoxo de Simpson) | ✅ |

Observação de dados: a coluna `sex` contém `"."` (1) e vazios (10); a ferramenta
descarta automaticamente esses níveis-lixo (`clean_factor_levels`), restando
333 registros MALE/FEMALE no fatorial.

## 2. Pressão arterial (`PRESSURE.txt`) — fatorial 3×2×2

`drug` (X/Y/Z) × `biofeed` (Absent/Present) × `diet` (No/Yes), 72 obs balanceadas.
Exercita o **fatorial de três fatores** (todas as interações).

| Termo | PhysioFlow (p) |
|---|---|
| drug | 0,0014 |
| biofeed | 0,0058 |
| drug × biofeed | 0,60 (não significativo) |
| interação tripla | presente no quadro |

## 3. Oats / Yates 1935 (`OATS.csv`) — parcelas subdivididas

Exemplo canônico de split-plot (3 variedades × 4 doses de N × 6 blocos), com
quadro de ANOVA publicado em livros de modelos mistos e no `nlme::Oats` do R.
**Validação independente do motor de split-plot** (a ferramenta não tem acesso
a esses valores; eles foram reproduzidos do zero).

| Termo | Estrato/erro | PhysioFlow | Publicado |
|---|---|---|---|
| Variety (parcela) | Erro(a), gl 10 | F(2,10) = **1,485**, p = 0,272 | 1,485, p = 0,272 |
| nitro (subparcela) | Erro(b), gl 45 | F(3,45) = **37,69**, p < 0,001 | 37,686, p < 0,001 |
| Variety × nitro | Erro(b), gl 45 | F(6,45) = **0,303**, p = 0,932 | 0,303, p = 0,932 |

CV(a) = 23,59%, CV(b) = 12,80%. **Coincidência decimal** nos três F.

## 3b. Scott-Knott vs. pacote oficial do R (`sk_crd1`, `sk_rcbd`, `sk_sorghum`)

Validação **padrão-ouro**: o agrupamento de Scott-Knott da ferramenta foi
comparado, treatment a treatment, com o do pacote oficial `ScottKnott` (CRAN)
executado no R, usando os datasets que acompanham o pacote (GPL). **Bate 100%.**

| Dataset | Delineamento | k | Partição (oficial = PhysioFlow) |
|---|---|---|---|
| `sk_crd1` | DIC | 4 | {tr-1, tr-2, tr-3} · {tr-4} |
| `sk_rcbd` | DBC | 5 | {A, B, C, D} · {E} |
| `sk_sorghum` | DBC | 16 | {1,2,3,4,5,7,8,9,14} · {6,10,11,12,13,15,16} |

O `sk_sorghum` é o exemplo de rendimento de sorgo do artigo de Jelihovschi,
Faria & Allaman (2014) — a mesma referência cuja formulação (σ²₀, λ, ν₀=k/(π−2))
o motor implementa. Reprodução em `tests/test_sample_datasets.py::TestScottKnottVsR`.

## 3c. Tukey, LSD, Duncan, Scheffé e Dunnett vs. R (2026-09-27)

Antes desta rodada, apenas o Scott-Knott (§3b) e os delineamentos (§0) tinham
referência externa; LSD, Duncan, Scheffé e Dunnett eram cobertos só por testes
de comportamento (ex.: "Scheffé é mais conservador que LSD"). Esta seção fecha
essa lacuna.

**Referências:** `TukeyHSD` (R base), `agricolae` 1.3.7 (`LSD.test`,
`duncan.test`, `scheffe.test`) e `multcomp` 1.4.32 (`glht`, Dunnett
*single-step*), em R 4.6.0. O critério comparado é a **decisão por par**
(difere / não difere a 5 %) — que é o que o usuário lê nas letras.

| Dataset | Delineamento | k | Pares | Tukey | LSD | Duncan | Scheffé |
|---|---|---|---|---|---|---|---|
| `sweetpotato` (agricolae) | DIC | 4 | 6 | ✅ | ✅ | ✅ | ✅ |
| `plantgrowth` (R base) | DIC | 3 | 3 | ✅ | ✅ | ✅ | ✅ |
| `penguins` (n desigual) | DIC | 3 | 3 | ✅ | ✅ | ✅ | ✅ |
| `sk_sorghum` | DBC | 16 | 120 | ✅ | ✅ | ✅ | ✅ |

**528 decisões pareadas conferidas, 100 % de concordância.** Os valores
críticos também batem: LSD, diferença crítica de Scheffé e as amplitudes de
Duncan (`Rp`, p = 2…k) — 26 valores, diferença relativa máxima **4,7×10⁻⁸**.

**Dunnett** (cada tratamento vs. controle), contra `multcomp::glht`:

| Dataset | Controle | Maior \|Δp\| | Decisões |
|---|---|---|---|
| `plantgrowth` | `ctrl` | 4,2×10⁻⁵ | iguais |
| `sweetpotato` | `cc` | 3,3×10⁻⁴ | iguais |
| `penguins` | `Adelie` | 2,7×10⁻⁶ | iguais |

A diferença vem da integração numérica da t multivariada, não de
especificação.

### 3d. Dunnett com bloco (`sk_rcbd`) — correção de 2026-09-27

O limite anterior está **corrigido**. Até a v1.0 (commit `bc69e10`, o citado no
artigo) `dunnett_test` era *one-way*: estimava a variância só entre as
repetições do tratamento, então num DBC a variação de bloco entrava no erro e
inflava o valor-p. Os demais métodos sempre receberam `ms_error`/`df_error` do
modelo ajustado; só o Dunnett ficou de fora.

Agora a função aceita `ms_error`/`df_error` e a página passa os do modelo. A
referência é `aov(y ~ tra + blk)` + `multcomp::glht(..., "Dunnett")` sobre o
`sk_rcbd` (5 tratamentos × 4 blocos), congelada em `_dunnett_rcbd`:

| Tratamento | p (R, com bloco) | p (corrigido) | p (comportamento antigo) |
|---|---|---|---|
| B | 0,7376 | 0,7376 | 0,7142 |
| C | 0,7361 | 0,7361 | 0,7127 |
| D | 0,9433 | 0,9433 | 0,9372 |
| E | **0,0539** | **0,0539** | **0,0385** |

O QMR bate com o do R (40,4811; 12 gl). O tratamento E mostra por que importa:
o comportamento antigo o declarava diferente do controle a 5 %, o correto não.

Sem `ms_error`/`df_error` a função continua caindo no erro *one-way*, que é o
certo no DIC — e há teste conferindo que esse caminho reproduz o
`scipy.stats.dunnett`.

**Reprodução.** As referências estão congeladas em
`data/sample/test/posthoc_reference_R.json` (a suíte **não** precisa do R):

```bash
pytest tests/test_sample_datasets.py::TestPostHocVsR -v   # usa o JSON
Rscript scripts/gerar_referencia_posthoc_R.R              # regenera o JSON
```

Fora de escopo (sem referência externa): **quadrado latino** e
**regressão de doses**, cobertos apenas por testes internos.

## 4. Soja multiambiente (`australia.soybean.txt`)

Ensaio com 8 ambientes, 58 genótipos e 6 variáveis. Usado para a validação de
**correlação** com um caso agronômico clássico — o *trade-off* proteína × óleo:

| Correlação | PhysioFlow | Cruzada (`scipy`) |
|---|---|---|
| protein × oil (Pearson) | **−0,758** | −0,758 |

## 5. Demais datasets

| Arquivo | Uso na ferramenta | Status |
|---|---|---|
| `BESAG_ELBATAN.txt` | DBC com bloco numérico (`col`), gl_erro = 98, p(gen) ≈ 0,0066 | ✅ |
| `SPRING_BARLEY.txt` | Ensaio row-column, 478 linhagens; análise espacial/mista | △ (futuro) |

> Cobertura externa por análise: **DIC/Tukey/correlação** → Penguins;
> **split-plot** → Oats (Yates); **DBC com bloco numérico** → BESAG;
> **correlação agronômica** → soja. ANCOVA e fatorial de 3 fatores são cobertos
> por testes herméticos em `tests/test_stats_utils.py`.

## Como reexecutar a validação

```bash
pytest tests/test_sample_datasets.py -v
```

## Fontes (Palmer Penguins)

- ANOVA examples using the Palmer penguins data set — https://eclass.duth.gr/modules/document/file.php/418345/ANOVApenguin.html
- INFO 2950, Cornell — Palmer Penguins regression — https://info2950.infosci.cornell.edu/ae/ae-14-palmerpenguins-A.html
- Palmer Penguins Size Analysis — https://sanjico.github.io/Palmer-Penguins-Analysis/
- T. Love, Data Science for Bio/Medical Research — https://thomaselove.github.io/431-2020-notes/looking-at-the-palmer-penguins.html
- Datasets do ASReml Cookbook — https://cookbook.asreml.vsni.co.uk/datasets.html
