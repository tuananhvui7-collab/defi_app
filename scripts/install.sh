#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export npm_config_cache="${npm_config_cache:-/workspace/.cache/npm}"
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir /workspace/.cache/pip -r requirements-lock.txt
npm ci --no-audit --no-fund
npm run compile
bash scripts/install_geth.sh
.venv/bin/python -m pytest tests/test_routing.py -q
