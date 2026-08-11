#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f package.json ]]; then
  echo "package.json not found" >&2
  exit 1
fi

npm ci --ignore-scripts 2>/dev/null || npm install --ignore-scripts
