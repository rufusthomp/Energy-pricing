#!/usr/bin/env bash
# Compile the paper: sections in order, citations from references.bib, PDF via XeLaTeX.
set -euo pipefail
cd "$(dirname "$0")"
pandoc metadata.yaml sections/*.md \
  --citeproc --pdf-engine=xelatex \
  --resource-path=.:figures \
  -o build/paper.pdf "$@"
echo "built paper/build/paper.pdf"
