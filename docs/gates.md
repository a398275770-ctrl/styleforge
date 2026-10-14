# 门禁清单（gates）

> 一条命令复现全部门禁：`sh scripts/check.sh`（CI 与 pre-commit 跑的就是它）。
> Python 解释器自动探测：`$PYTHON` > 仓库 `.venv/bin/python` > PATH 的 `python3`。

## 测试策略与分层（阶段 5）

| 层 | 文件 | 职责 | 时长约束 |
|---|---|---|---|
| 单元 | `test_names` / `test_frontmatter` / `test_io` / `test_edge` / `test_permissions` | 纯函数与文件 IO 边界，无 CLI 依赖 | 每文件 < 1s |
| 集成 | `test_actions` | core 动作全流程（沙箱 home） | < 1s |
| 端到端 | `test_cli` | `main()` 入口、退出码、`--json` 契约、文本渲染 | < 1s |
| 结构 | `test_structure` | 依赖方向 / 版本单点（架构不变量，非行为） | < 1s |
| 资产 | `test_packs` | pack 指纹与 README 登记一致 | < 1s |

- 全量 124 用例 < 2s；覆盖 94%（sf_core 98% / cli 89%），门禁下限 90%
- **沙箱铁律**（conftest autouse）：一切写入强制 `STYLEFORGE_HOME` → tmp，物理隔离真实 `~/.claude`
- 可维护性规则：用例名描述行为；禁止魔法数字（用常量/具名 fixture）；禁止顺序依赖（每用例独立沙箱）
- 防假测试：注入缺陷抽查累计 4 处全有效（名字校验禁用→6 红；损坏 JSON 检测失效→2 红；pack 篡改→指纹红；TD-CLI-004 即由断言发现）

## 检查项

| # | 检查 | 触发时机 | 失败含义 | 修复指引 |
|---|---|---|---|---|
| 1 | `ruff check`（lint） | check.sh / pre-commit / CI | 代码规范违规（未用变量、import 顺序、歧义命名等） | 报错行号处按提示改；多数可 `ruff check --fix` 自动修 |
| 2 | `ruff format --check` | 同上 | 格式与标准不一致 | `ruff format <文件>` 一键修复 |
| 3 | `mypy`（类型，py3.10 语义） | 同上 | 类型不匹配 / Optional 未处理 | 按报错补类型收窄或注解；禁止用 `Any` 糊弄 |
| 4 | `pytest`（88 用例，沙箱强制） | 同上 | 行为回归或结构违规 | **结构测试失败** = 架构越层，见下「结构规则」；行为失败看断言信息 |
| 5 | `repo_metrics.py` | 同上 | 文件>500 行 / 函数>80 行 / 缓存产物被 git 追踪 | 按 FAIL 行附带的修复说明处理 |
| 6 | `doc_lint.py` | 同上 | 文档死链 / 缺必填节 / 索引漏条目 / AGENTS.md>200 行 | 按 FAIL 行指引补链补节 |
| 7 | `py_compile` + 沙箱冒烟 | 同上 | 语法破坏或 install/status/uninstall 基本流断裂 | 看堆栈定位 |
| 8 | `pip-audit` | 仅 CI | dev 工具链存在已知漏洞 | 升级报漏洞的包（运行时零依赖，不受影响） |

## 结构规则（pytest 内 `tests/test_structure.py` 机械强制）

| 规则 | 违反后果 | 修复方向 |
|---|---|---|
| `lib/sf_core.py` 仅标准库 import | 测试红 | 移除第三方依赖（core-beliefs #16） |
| core 不得 import CLI | 测试红 | 逻辑上移到 CLI 层 |
| CLI 仅标准库 + sf_core | 测试红 | 新依赖先过 core-beliefs 裁决 |
| 入口脚本只调 styleforge.py | 测试红 | 业务逻辑移入 core |
| 版本唯一声明点（sf_core `VERSION`） | 测试红 | 删除多余声明点（规则 §6.1） |
| README md5 指纹 = pack 实际字节 | 测试红 | 改 pack 就同步改 README 登记行 |

## 豁免机制（显式、带原因、可审计）

| 方式 | 适用 | 记录位置 |
|---|---|---|
| `SKIP_SF_CHECK=1 git commit` | 临时跳过 pre-commit（如 WIP 提交） | 必须在 commit message 写 `[跳过门禁:原因]`；CI 仍会拦截，无法绕过 |
| `pyproject.toml` 的 `ignore` + 注释理由 | 规则本身不适用（如 BLE001） | pyproject 内注释（有理由、无到期时间，评审可查） |
| 行内 `# noqa: CODEX` | 单行特例 | 过期 noqa 会被 RUF100 自动抓出 |

## 版本一致性

本项目版本唯一声明点是 `lib/sf_core.py` 的 `VERSION`（结构测试强制单点）。
`pyproject.toml` 刻意不声明版本——不存在多声明点，也就不需要 bump 脚本与 tag guard（规则 §6.1 的前置条件不成立时，不引入多余机制）。
