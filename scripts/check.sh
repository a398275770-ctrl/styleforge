#!/bin/sh
# styleforge 全部门禁一条命令（规则 §5 阶段 3：本地与 CI 跑同一脚本，零记忆依赖）。
# 依赖：Python 3.10+ 且已安装 ruff/mypy/pytest（CI 与 .venv 均满足）。
# 跳过（豁免）：SKIP_SF_CHECK=1 显式跳过，并在 commit message 注明原因（docs/gates.md）。
set -eu
cd "$(dirname "$0")/.."
# Python 解释器探测：显式 $PYTHON > 仓库 .venv > PATH 中的 python3。
# （零记忆依赖：用户无需激活 venv，hook/CI/手动行为一致）
if [ -n "${PYTHON:-}" ]; then
    PY="$PYTHON"
elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
else
    PY="python3"
fi

echo "== [1/6] ruff lint =="
"$PY" -m ruff check .

echo "== [2/6] ruff format =="
"$PY" -m ruff format --check .

echo "== [3/6] mypy 类型检查 =="
"$PY" -m mypy styleforge.py lib/sf_core.py scripts/analysis/repo_metrics.py scripts/analysis/doc_lint.py

echo "== [4/6] pytest 测试 =="
"$PY" -m pytest

echo "== [5/6] 度量与指纹（repo_metrics）+ 文档门禁（doc_lint） =="
"$PY" -I scripts/analysis/repo_metrics.py .
"$PY" -I scripts/analysis/doc_lint.py .

echo "== [6/6] 构建检查（py_compile + 沙箱冒烟） =="
"$PY" -m py_compile styleforge.py lib/sf_core.py
TMPHOME=$(mktemp -d)
trap 'rm -rf "$TMPHOME"' EXIT
STYLEFORGE_HOME="$TMPHOME" "$PY" -I styleforge.py install --pack default -q
STYLEFORGE_HOME="$TMPHOME" "$PY" -I styleforge.py status -q
STYLEFORGE_HOME="$TMPHOME" "$PY" -I styleforge.py uninstall -q

echo "全部门禁通过 ✓"
