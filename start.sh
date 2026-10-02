#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export KMP_DUPLICATE_LIB_OK=TRUE
if [[ -x venv/bin/python ]]; then
    exec venv/bin/python main.py
elif [[ -x .venv/bin/python ]]; then
    exec .venv/bin/python main.py
else
    echo "Ambiente do Juvion ausente. Execute bash setup_writingway.sh primeiro."
    exit 1
fi
