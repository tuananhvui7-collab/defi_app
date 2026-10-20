#!/usr/bin/env bash
set -euo pipefail
# Build an official pinned Geth release. Go is infrastructure, not app code.
TOOLS_ROOT="${LAB_TOOLS_ROOT:-/workspace/.local}"
CACHE_ROOT="${LAB_CACHE_ROOT:-/workspace/.cache}"
mkdir -p "$TOOLS_ROOT/bin" "$CACHE_ROOT"
if [[ -x "$TOOLS_ROOT/bin/geth" ]] && "$TOOLS_ROOT/bin/geth" version | head -2 | grep -q '1.14.13'; then
  echo 'Pinned Geth already installed'; exit 0
fi
if [[ ! -x "$TOOLS_ROOT/go/bin/go" ]]; then
  if [[ "$(uname -s)/$(uname -m)" != Linux/x86_64 ]]; then
    echo 'Auto-bootstrap supports Linux x86_64; install Go 1.23.6 and Geth 1.14.13 manually on this platform.' >&2; exit 1
  fi
  curl -fL --retry 2 https://dl.google.com/go/go1.23.6.linux-amd64.tar.gz -o "$CACHE_ROOT/go1.23.6.tar.gz"
  python3 - "$CACHE_ROOT/go1.23.6.tar.gz" <<'PY'
import hashlib,sys
expected='9379441ea310de000f33a4dc767bd966e72ab2826270e038e78b2c53c2e7802d'
if hashlib.file_digest(open(sys.argv[1],'rb'),'sha256').hexdigest()!=expected:
    raise SystemExit('Go checksum mismatch; refusing to extract')
PY
  tar -xzf "$CACHE_ROOT/go1.23.6.tar.gz" -C "$TOOLS_ROOT"
fi
export GOBIN="$TOOLS_ROOT/bin" GOPATH="$CACHE_ROOT/go" GOMODCACHE="$CACHE_ROOT/go/pkg/mod" GOCACHE="$CACHE_ROOT/go-build"
export GOTOOLCHAIN=local GOMAXPROCS=4
# Pipe fallback also handles a registry redirect blocked by a cloud egress rule.
export GOPROXY="${GOPROXY:-https://proxy.golang.org|direct}"
# Keep Go checksum database verification enabled.
export GOSUMDB=sum.golang.org
"$TOOLS_ROOT/go/bin/go" install -p 4 github.com/ethereum/go-ethereum/cmd/geth@v1.14.13
"$GOBIN/geth" version
