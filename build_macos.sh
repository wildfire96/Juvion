#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -x venv/bin/python ]]; then
    JUVION_PYTHON=venv/bin/python
elif [[ -x .venv/bin/python ]]; then
    JUVION_PYTHON=.venv/bin/python
else
    python3.11 -m venv venv
    JUVION_PYTHON=venv/bin/python
fi
"$JUVION_PYTHON" package_app.py --install-dependencies
