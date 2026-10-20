#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
"$PY" -m defi_lab.cli status
# Deployment commands are explicit: demo never silently overwrites a manifest.
"$PY" -m defi_lab.cli swap --path A B --amount 10
"$PY" -m defi_lab.cli swap --path A B C D --amount 10
"$PY" -m defi_lab.cli route --amount 10 --execute
"$PY" -m defi_lab.cli flash --amount 100 --min-profit 1
