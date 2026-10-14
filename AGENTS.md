# AGENTS.md

> 本文件是**内容目录**，不是百科全书。需要细节时，按下方指引跳转。

## 这是什么项目

styleforge：Claude Code 持久化提示词注入器。把 `packs/` 里的提示词包安装为
`~/.claude/settings.json` 的 `outputStyle` + `~/.claude/output-styles/<name>.md`，
新开会话即注入系统提示词。纯 Python 标准库，零第三方依赖。

## 常用命令

```bash
python3 styleforge.py install --pack default   # 安装（写入 style + settings 键）
python3 styleforge.py status                   # 当前激活 style / 来源 / 备份数
python3 styleforge.py doctor                   # 自检本机机制是否可用
python3 styleforge.py preview --pack default --raw  # 预览将写入的字节
python3 styleforge.py uninstall                # 删键删文件，保留备份
python3 styleforge.py restore --backup <path>  # 从备份恢复 settings.json
./one-click-install.sh / ./one-click-uninstall.sh  # POSIX 一键入口
sh scripts/check.sh            # 全部门禁一条命令（lint/类型/测试/度量/文档/冒烟）
```

工具链：`python3 -m venv .venv && .venv/bin/pip install ruff mypy pytest pytest-cov pip-audit`。
pre-commit hook 已挂载（`.githooks/`）；豁免与各检查的修复指引见 `docs/gates.md`。

## 目录地图

| 路径 | 职责 |
|---|---|
| `styleforge.py` | CLI 入口：argparse、9 个子命令、JSON/文本输出层（`Out`） |
| `lib/sf_core.py` | 核心库：路径/JSON 原子读写/备份/名字校验/pack 读取/style 组装/装卸恢复 |
| `packs/<名>/` | 提示词包资产（`claude-project-rules.md` 必填，`claude-append-prompt.md` 必填） |
| `scripts/analysis/` | 度量与文档校验脚本（门禁雏形） |
| `docs/` | 记录系统：架构、决策、计划、技术债、CI 决定 |
| `one-click-*.sh` / `styleforge.cmd` | 平台一键入口（POSIX / Windows） |

## 硬性约束（不可违反）

- 分层依赖只准单向：入口脚本 → `styleforge.py`（CLI）→ `lib/sf_core.py`（core）→ 标准库/文件系统；禁止反向 import、禁止 CLI 层直接写 `~/.claude`
- `settings.json` 只许动 `outputStyle` 一个键；写前必备份、原子写（temp + `os.replace`）
- pack 读取必须 `read_bytes().decode()`（CRLF 字节保真），禁止 `read_text()`（会静默翻译换行）
- style/pack 名必须过 `normalize_style_name` / `pack_dir` 白名单（拒绝路径分隔符、`..`）
- 零第三方运行时依赖；新增依赖须先过 `docs/design-docs/core-beliefs.md` 的裁决
- 违反以上将被结构测试 / linter 拦截（阶段 3 起生效）

## 开始工作前先看

- 架构与设计决策：`ARCHITECTURE.md`
- 第一性原则与争议裁决：`docs/design-docs/core-beliefs.md`
- 当前执行计划：`docs/exec-plans/active/`
- 已知技术债：`docs/exec-plans/tech-debt-tracker.md`
- CI 与发布决策：`docs/CI.md`
- 全部文档索引：`docs/index.md`

## 工作方式

- 改动前读相关 `docs/`，改动后同步更新对应文档与 `docs/index.md`
- 提交粒度单一职责（Conventional Commits 前缀）；bug 修复与纯重构严格分开提交（重构红线见 core-beliefs.md）
- 会话最后一次提交必须过全部本地门禁，message 注明 `[已测试]` / `[未测试]` 及验证方式
- 交互式决策确认后必须落盘到仓库文档（对话里说过 = 不存在）
- 计划写在 `docs/exec-plans/active/`，完成后移入 `completed/`
- `prompt-history.txt`：用户私有提示词记录（已 gitignore，不入库）。每轮把用户提示词结构化追加到文件末尾，纯 append 不改写历史；少于 10 字的寒暄不记录；智能体只写不读
