#!/bin/sh
# styleforge one-shot uninstall. No arguments, no questions.
# Backups are kept; use `styleforge.py backups` to list them.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# NOTE: the python-detection block below is intentionally duplicated in both
# one-click scripts (self-contained one-shots; D5 decision, 2026-10-14).
PY=""
for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "未找到 python3。请先安装 Python 3.10+，或用 Windows 的 styleforge.cmd。" >&2
    exit 127
fi

exec "$PY" "$SCRIPT_DIR/styleforge.py" uninstall
