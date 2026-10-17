#!/usr/bin/env bash
# Run from any directory: bash scripts/setup-local.sh [--check-only]
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
bootstrap_python=""
for candidate in python3.13 python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))' 2>/dev/null; then
        bootstrap_python="$candidate"
        break
    fi
done
if [ -z "$bootstrap_python" ]; then
    if [[ " $* " == *" --check-only "* ]]; then
        echo 'FAIL: no Python >=3.9 available to run the checker. Run setup without --check-only.'
        exit 1
    elif command -v brew >/dev/null 2>&1; then
        brew install python@3.13
        bootstrap_python="$(brew --prefix python@3.13)/bin/python3.13"
    else
        echo 'Install Python 3.12 or 3.13 from python.org (or your OS package manager), then rerun this script.'
        echo 'Linux also needs the matching python3-venv package. No files were changed.'
        exit 1
    fi
fi
exec "$bootstrap_python" "$project_root/scripts/setup_local.py" "$@"
