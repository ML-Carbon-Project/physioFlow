#!/usr/bin/env Rscript
# Gera as referências de comparação de médias usadas por
# tests/test_sample_datasets.py::TestPostHocVsR.
#
# Saída: data/sample/test/posthoc_reference_R.json (decisões pareadas por
# método/dataset + p-valores de Dunnett). O JSON fica versionado, de modo que a
# suíte de testes não precisa do R para rodar; este script só é necessário para
# regenerar as referências.
#
# Uso (da raiz do repositório):
#   Rscript scripts/gerar_referencia_posthoc_R.R
#
# Requer: agricolae, multcomp (CRAN). TukeyHSD vem do R base.

suppressMessages({
  library(agricolae)
  library(multcomp)
  library(jsonlite)
})

T <- "data/sample/test"

# --- datasets -------------------------------------------------------------
# sweetpotato acompanha o agricolae (GPL); PlantGrowth vem do R base.
# Ambos são exportados para CSV para que o lado Python use exatamente as
# mesmas linhas, sem depender do R.
data(sweetpotato)
write.csv(sweetpotato, file.path(T, "sweetpotato.csv"), row.names = FALSE)
write.csv(PlantGrowth, file.path(T, "plantgrowth.csv"), row.names = FALSE)

peng <- read.csv(file.path(T, "penguins.csv"))
peng <- peng[!is.na(peng$body_mass_g) & peng$species != "", ]
sor <- read.csv(file.path(T, "sk_sorghum.csv"))
sor$x <- factor(sor$x); sor$r <- factor(sor$r)

# DIC para os três primeiros; DBC (bloco r) para o sorgo.
sets <- list(
  sweetpotato = list(m = aov(yield ~ virus, sweetpotato),        trt = "virus"),
  plantgrowth = list(m = aov(weight ~ group, PlantGrowth),       trt = "group"),
  penguins    = list(m = aov(body_mass_g ~ species, peng),       trt = "species"),
  sorghum     = list(m = aov(y ~ x + r, sor),                    trt = "x")
)

ref <- list()

# --- Tukey (R base), LSD / Duncan / Scheffé (agricolae) --------------------
for (nm in names(sets)) {
  s <- sets[[nm]]
  out <- list()

  tk <- TukeyHSD(s$m, s$trt)[[1]]
  pr <- do.call(rbind, strsplit(rownames(tk), "-"))
  out[["tukey"]] <- lapply(seq_len(nrow(tk)), function(i)
    list(trimws(pr[i, 1]), trimws(pr[i, 2]), unname(tk[i, "p adj"]) < 0.05))

  for (me in c("lsd", "duncan", "scheffe")) {
    r <- switch(me,
      lsd     = LSD.test(s$m, s$trt, p.adj = "none", group = FALSE, console = FALSE),
      duncan  = duncan.test(s$m, s$trt, group = FALSE, console = FALSE),
      scheffe = scheffe.test(s$m, s$trt, group = FALSE, console = FALSE))
    cmp <- r$comparison
    pr <- do.call(rbind, strsplit(rownames(cmp), " - "))
    out[[me]] <- lapply(seq_len(nrow(cmp)), function(i)
      list(trimws(pr[i, 1]), trimws(pr[i, 2]), cmp$pvalue[i] < 0.05))
  }
  ref[[nm]] <- out
}

# --- Dunnett (multcomp::glht, single-step) --------------------------------
dsets <- list(
  plantgrowth = list(d = PlantGrowth, y = "weight",      g = "group",   c = "ctrl"),
  sweetpotato = list(d = sweetpotato, y = "yield",       g = "virus",   c = "cc"),
  penguins    = list(d = peng,        y = "body_mass_g", g = "species", c = "Adelie")
)
dn <- list()
for (nm in names(dsets)) {
  s <- dsets[[nm]]; d <- s$d
  d[[s$g]] <- relevel(factor(d[[s$g]]), ref = s$c)
  fit <- aov(as.formula(paste(s$y, "~", s$g)), d)
  sm <- summary(glht(fit, linfct = do.call(mcp, setNames(list("Dunnett"), s$g))))
  nms <- sub(" - .*", "", names(sm$test$coefficients))
  dn[[nm]] <- setNames(as.list(round(as.numeric(sm$test$pvalues), 6)), nms)
}
ref[["_dunnett"]] <- dn
ref[["_meta"]] <- list(
  R = as.character(getRversion()),
  agricolae = as.character(packageVersion("agricolae")),
  multcomp = as.character(packageVersion("multcomp")),
  generated = format(Sys.Date())
)

write(toJSON(ref, auto_unbox = TRUE, pretty = TRUE),
      file.path(T, "posthoc_reference_R.json"))
cat("OK:", file.path(T, "posthoc_reference_R.json"), "\n")
