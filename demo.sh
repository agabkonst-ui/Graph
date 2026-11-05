#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PYTHONPATH="$PWD/src"
export PYTHONUTF8=1
export PYTHONDONTWRITEBYTECODE=1
exec "${PYTHON_EXE:-python3}" -B scripts/demo.py
