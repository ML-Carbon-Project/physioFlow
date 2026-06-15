# Validação externa do módulo de Estatística Experimental

Este documento registra a comparação entre os resultados da ferramenta
PhysioFlow (página **Estatística Experimental**) e resultados **publicados**
para datasets clássicos de domínio público. Serve como evidência de corretude
para o software paper e como roteiro de re-validação.

Os dados ficam em `data/sample/` e os testes automatizados que travam estes
números estão em `tests/test_sample_datasets.py`.

> **Natureza da validação.** Vários datasets vêm do *ASReml Cookbook*, cujos
> resultados "oficiais" usam **modelos mistos/espaciais (REML)**. A ferramenta
> faz **ANOVA clássica**, então a comparação justa é contra a mesma ANOVA
> clássica (R/Rbio/seaborn), não contra a saída espacial. O caso mais forte de
> validação independente é o **Palmer Penguins**, fartamente documentado.

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

## 3. Demais datasets (ASReml Cookbook)

| Arquivo | Uso na ferramenta | Status |
|---|---|---|
| `RATPUP.txt` | DIC, Fatorial (`treatment × sex`) e **ANCOVA** (covariável `lsize`: inclinação ≈ −0,08, p<0,001 — ninhada maior → filhote mais leve) | ✅ |
| `SALMON.txt` | Correlação (cruzada vs `scipy.pearsonr`, r≈−0,82) e regressão | ✅ |
| `BESAG_ELBATAN.txt` | DBC com bloco numérico (`col`), gl_erro = 98, p(gen) ≈ 0,0066 | ✅ |
| `DURBAN_ROWCOL.txt` | DBC (gen+rep), 272 tratamentos; análise espacial → fora do escopo | △ |
| `SPRING_BARLEY.txt` | Ensaio row-column, 478 linhagens; análise espacial/mista | △ (Lote 3) |

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
