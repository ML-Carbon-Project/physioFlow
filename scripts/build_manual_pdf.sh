#!/usr/bin/env bash
# Gera o manual de operação em PDF a partir de docs/manual.pt.md.
#
# Uso:
#   scripts/build_manual_pdf.sh                          # PDF em docs/manual.pt.pdf
#   scripts/build_manual_pdf.sh --lang en                # usa docs/manual.en.md
#   scripts/build_manual_pdf.sh --output /tmp/out.pdf    # caminho customizado
#
# Pré-requisitos:
#   * pandoc           (https://pandoc.org)
#   * xelatex          (TeX Live com pacote xetex)
#
# Instalação rápida:
#   macOS:  brew install pandoc && brew install --cask basictex
#   Ubuntu: sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-recommended
set -euo pipefail

# ------------------------------------------------------------------
# Parsing de argumentos
# ------------------------------------------------------------------
LANG_CODE="pt"
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang)
      LANG_CODE="$2"
      shift 2
      ;;
    --output)
      OUTPUT="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '1,/^set/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Argumento desconhecido: $1" >&2
      exit 64
      ;;
  esac
done

# ------------------------------------------------------------------
# Caminhos
# ------------------------------------------------------------------
ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
INPUT="$ROOT_DIR/docs/manual.${LANG_CODE}.md"
METADATA="$ROOT_DIR/docs/manual_metadata.yaml"
[[ -z "$OUTPUT" ]] && OUTPUT="$ROOT_DIR/docs/manual.${LANG_CODE}.pdf"

# ------------------------------------------------------------------
# Verificações pré-execução
# ------------------------------------------------------------------
if [[ ! -f "$INPUT" ]]; then
  echo "❌ Manual não encontrado: $INPUT" >&2
  echo "   Crie o arquivo ou rode com outro --lang." >&2
  exit 65
fi

if ! command -v pandoc >/dev/null 2>&1; then
  cat >&2 <<'EOF'
❌ pandoc não está instalado.

Instalação rápida:
  macOS:  brew install pandoc && brew install --cask basictex
  Ubuntu: sudo apt-get install pandoc texlive-xetex texlive-fonts-recommended texlive-latex-recommended
EOF
  exit 127
fi

if ! command -v xelatex >/dev/null 2>&1; then
  cat >&2 <<'EOF'
❌ xelatex não encontrado.

Instalação rápida:
  macOS:  brew install --cask basictex
          (depois rode `sudo tlmgr install fancyhdr xurl booktabs longtable`)
  Ubuntu: sudo apt-get install texlive-xetex texlive-fonts-recommended texlive-latex-recommended
EOF
  exit 127
fi

# ------------------------------------------------------------------
# Geração
# ------------------------------------------------------------------
echo "→ Gerando PDF a partir de $INPUT"
echo "→ Saída:               $OUTPUT"

# `resource-path` permite que imagens referenciadas como `img/manual/x.png`
# sejam resolvidas a partir de `docs/`.
pandoc "$INPUT" \
  --from=gfm+yaml_metadata_block \
  --to=pdf \
  --pdf-engine=xelatex \
  --metadata-file="$METADATA" \
  --resource-path="$ROOT_DIR/docs" \
  --output="$OUTPUT"

echo "✅ PDF gerado: $OUTPUT"
echo "   Tamanho:    $(du -h "$OUTPUT" | cut -f1)"
