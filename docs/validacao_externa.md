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
