#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .local
GETH_BIN="${GETH_BIN:-/workspace/.local/bin/geth}"
if [[ ! -x "$GETH_BIN" ]]; then GETH_BIN="$(command -v geth || true)"; fi
if [[ -z "$GETH_BIN" ]]; then echo 'Geth missing; run scripts/install_geth.sh' >&2; exit 1; fi
# Foreground process: terminate with Ctrl-C. RPC is deliberately loopback-only.
exec "$GETH_BIN" --dev --dev.period 1 --datadir "$PWD/.local/geth" \
  --http --http.addr 127.0.0.1 --http.port 8545 --http.api eth,net,web3 \
  --ipcdisable --nodiscover --maxpeers 0 --verbosity 3
