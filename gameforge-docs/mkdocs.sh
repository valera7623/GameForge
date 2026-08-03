#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

DOCS_PORT="${DOCS_PORT:-8001}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

if [[ "${1:-}" == "serve" ]]; then
  shift
  has_addr=false
  for arg in "$@"; do
    if [[ "$arg" == "-a" || "$arg" == "--dev-addr" ]]; then
      has_addr=true
      break
    fi
  done
  if [[ "$has_addr" == false ]]; then
    set -- serve -a "127.0.0.1:${DOCS_PORT}" "$@"
  else
    set -- serve "$@"
  fi
fi

exec .venv/bin/mkdocs "$@"
