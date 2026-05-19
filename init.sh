#!/usr/bin/env bash
set -euo pipefail

python -m unittest discover -s tests

if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/check-harness-docs.ps1
elif command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check-harness-docs.ps1
elif command -v powershell >/dev/null 2>&1; then
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check-harness-docs.ps1
else
  echo "PowerShell not found; cannot run scripts/check-harness-docs.ps1" >&2
  exit 1
fi

python scripts/run_baseline.py --version local --mode static --splits golden optimization honeypot
