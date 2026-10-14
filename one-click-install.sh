#!/bin/sh
# styleforge one-shot: install the default pack, no arguments, no questions.
#
# POSIX sh so it runs under bash, zsh, dash, and Git Bash / MSYS2 on Windows.
# On Windows without a POSIX shell, use styleforge.cmd instead.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY=""
for candidate in python3 python py; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "未找到 python3。请先安装 Python 3.8+，或用 Windows 的 styleforge.cmd。" >&2
    exit 127
fi

PACK="${1:-default}"
exec "$PY" "$SCRIPT_DIR/styleforge.py" install --pack "$PACK"
