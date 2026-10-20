#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
# All tests send real transactions only when explicitly enabled here.
RUN_INTEGRATION=1 .venv/bin/python -m pytest -q --junitxml=.local/test-results.xml
