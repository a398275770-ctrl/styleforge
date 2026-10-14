# Harness 工程化改造计划

## 0. 元信息
- 项目 / 仓库：styleforge（`/home/admin/Projects/新提示词/styleforge`）
- 分支：harnessing（已于 2026-10-14 建立；main = 零改动基线快照 `59076a0`，harnessing 承载全部改造提交）
- 计划版本 / 日期：v1.1 / 2026-10-14
- 状态：**待确认**（D1–D3 已答复、批次 0 本地部分已执行；D4–D8 已向用户出具白话解释，待表态后整体确认）
- 规则依据：`docs/HARNESS-RULES.md` §5 五阶段流程；本计划为阶段 1 产出，按附录 A 结构编写
- 扫描方法：全量人工读码（仓库共 10 个文件、约 1000 行业务代码）+ AST 度量（`scripts/analysis/repo_metrics.py`）+ 沙箱实测（`STYLEFORGE_HOME=$(mktemp -d)` 隔离，未触碰真实 `~/.claude`）

## 1. 项目概况

- **是什么**：Claude Code 持久化提示词注入器（CLI 工具）。通过写入 `~/.claude/settings.json` 的 `outputStyle` 键 + `~/.claude/output-styles/<name>.md` 文件，把 pack 内容注入系统提示词。
- **技术栈**：Python 3 纯标准库（零第三方运行时依赖）+ 3 个平台入口（POSIX sh ×2、Windows cmd ×1）。
- **构建方式**：无构建（解释型脚本直跑）；无 pyproject.toml。
- **运行方式**：`python3 styleforge.py <command>`；或 `./one-click-install.sh` / `styleforge.cmd`。
- **部署方式**：无部署；本地安装到用户 home（写 `~/.claude/`）。
- **顶层模块与入口点**：
  - `styleforge.py`（347 行）— CLI 入口：argparse 解析、`Out` JSON/文本输出层、9 个子命令
  - `lib/sf_core.py`（425 行）— 核心库：路径解析 / JSON 原子读写 / 备份 / 名字校验 / pack 读取 / style 组装 / install-uninstall-restore 动作
  - `packs/default/` — 内容资产（2 个 md，CRLF，md5 与 README:158-159 登记一致）
  - `one-click-install.sh` / `one-click-uninstall.sh` / `styleforge.cmd` — 平台入口
  - `scripts/analysis/repo_metrics.py` — 本次阶段 1 新增的度量基线脚本
- **当前测试与 CI 现状**：**零测试、零 CI、零 hooks、零 lint**（TD-TEST-001 / TD-GATE-001，均 P0）。

## 2. 框架判定与 CI 现状（§3.2）

- **判定结果：其他类型（Python CLI 工具），非 Tauri。**
- **判定证据**（2026-10-14 实测 `ls`，逐条排除）：
  - `src-tauri/tauri.conf.json` — 不存在
  - `src-tauri/Cargo.toml` — 不存在（`src-tauri/` 目录本身不存在）
  - 根 `package.json` — 不存在（无从谈 `@tauri-apps/cli` / `@tauri-apps/api`）
  - `Cargo.toml` — 不存在
- **现有 `.github/workflows/` 清单**：`.github/` 目录不存在，无任何 CI 配置。
- **已有发布链路现状**：无 release/build 脚本（无 Makefile / package.json scripts / CI）；工具本身也非发布物（本地安装型）。唯一"发布面"是仓库拷贝分发。
- **流程后果**：按规则 §3.4，**跳过 §3.3 Tauri 三问**，不生成多平台打包与 Release 流水线；阶段 3 只建 lint + test + build 基础门禁。判定与证据已同步落盘 `docs/CI.md`。
- **遗留决策**：仓库无远程、无 git（D1/D8）→ 阶段 3 门禁的宿主形态（GitHub Actions vs 本地 hooks + 一条命令）待人工决策。

## 3. 现状诊断

### 3.1 架构现状（模块依赖图）

```text
one-click-install.sh ─┐
one-click-uninstall.sh ├─→ styleforge.py ──→ lib/sf_core.py ──→ 文件系统（~/.claude/ 与仓库内 packs/）
styleforge.cmd ───────┘        (CLI 层)         (core 层)            （标准库 only）
```

- 依赖方向严格单向（CLI → core → stdlib/FS），**无循环依赖、无越层依赖、无跨域直连**——天然接近规则 §4.1 的分层要求。
- 横切关注点：`Out`（输出/退出码）位于 CLI 层内聚，未泄漏到 core（core 只抛 `StyleForgeError`，CLI 统一转译）——分层干净。
- 结论：**架构无历史包袱，阶段 4 无需结构性重构**；工作重心在门禁与测试（见 3.5/3.6），重构仅剩小项（TD-CLI-001/002/003）。

### 3.2 复杂度热点（AST 实测，2026-10-14）

| 文件 | 行数 | 函数数 | 最长函数 | 判定 |
|---|---|---|---|---|
| lib/sf_core.py | 425 | 29 | `remove_style` 40 行 | 无热点（阈值：文件 500 / 函数 80） |
| styleforge.py | 347 | 20 | `build_parser` 56 行 | 无热点 |

- 无超长文件、无超大函数、无深嵌套热点、无 God Object。TODO/FIXME 标记：0。
- **热点文件数基线 = 0**（阶段 4 验收指标沿用此口径，基线不得恶化）。

### 3.3 重复代码

- `one-click-install.sh:9-20` 与 `one-click-uninstall.sh:9-17`：python 解释器探测 12 行逐字重复（TD-SCRIPTS-001，是否收敛待 D5）。
- Python 侧无跨模块重复实现（仓库仅两个模块、职责不重叠）。

### 3.4 文档缺口

- §2.1 必需四件（AGENTS.md / ARCHITECTURE.md / docs 结构 / QUALITY_SCORE.md）全部缺失（TD-DOCS-001）。
- 两处**文档与代码矛盾**：README「append 可选」vs 代码必读（TD-CORE-002，P1）；install.sh 注释 vs 参数行为（TD-SCRIPTS-002）。
- `docs/` 内两份完全相同的规则文档（TD-DOCS-002，母本/副本归属待 D3）。
- 无 LICENSE / CHANGELOG；`lib/sf_core.py:19-20` docstring「0600 permissions」声明与实测不符（并入 TD-CORE-003 证据）。
- 正面记录：README 质量高（机制实测表、通道对比、md5 指纹、已知限制），是阶段 2 改造的良好底稿。

### 3.5 测试缺口（TD-TEST-001，P0）

- **全仓零测试**。以下关键路径均无回归保护：settings.json 解析失败拒绝写入、`normalize_style_name` 路径穿越拦截、原子写、备份/恢复、install 幂等（noop）、uninstall/restore 全流程、`--json` 契约（schema `styleforge/v1`）。
- 红线 R3（无护栏不重构）因此被阻塞——阶段 4 前必须先落最小测试集（批次 2 前置）。
- 有利条件：`STYLEFORGE_HOME` 环境变量天然提供沙箱隔离，测试无需 mock 文件系统即可全流程验证（本阶段 1 沙箱实测已验证该通道可用）。

### 3.6 安全与性能审计

**安全（实测两项坐实）**
- TD-CORE-003（P0）：`atomic_write_text` 默认 `mode=0o644`，经 `os.replace` 覆盖后 **settings.json 权限 0600 → 0644 被放宽**（实测：chmod 600 → install → stat 644）。
- 其余面良好：无硬编码密钥；`normalize_style_name`/`pack_dir` 拦截路径穿越与 `..`（代码审读）；写前备份 + 原子写 + 幂等；备份文件 chmod 0600；损坏 JSON 拒绝写入。
- 依赖面：零第三方依赖 → 无依赖漏洞扫描面（阶段 3 仍建扫描门禁以约束未来引入）。

**性能与可靠性**：CLI 小工具，无 N+1/并发/长驻进程类问题，审计项标记**不适用**；可靠性关注点已在 TD-CLI-003（install 半完成无补偿）登记。

### 3.7 提交门禁现状（TD-GATE-001，P0）

- 无 `.github/workflows/`、无 git hooks、无 pre-commit/husky、无任何 lint/format/type-check/coverage 配置；且**无 git 仓库本身**（TD-REPO-001）——「提交门禁」目前无从谈起，这是本改造的第一块地基。

## 4. 改造批次划分

| 批次 | 覆盖业务域 | 主要目标 | 依赖前置 | 回滚方案 |
|---|---|---|---|---|
| 0 | 仓库基础设施 | git init + `.gitignore` + 首提交 + `harnessing` 分支；关闭 TD-REPO-001/002 | 本计划获确认（D1） | 删除 `.git/` 目录即完全回退（对工作区文件零影响） |
| 1（=阶段 2） | 文档域 | AGENTS.md / ARCHITECTURE.md / docs 全结构 / QUALITY_SCORE.md / 文档 linter；修正 TD-DOCS-001/002/003、TD-SCRIPTS-002 及 TD-CORE-002 文档面（按 D2） | 批次 0 | `git revert` 对应 docs 提交 |
| 2（=阶段 3） | 门禁域 | lint+test+build 三件套 + 最小测试集 + 品味不变量 linter + 文档门禁 + pack 指纹校验；关闭 TD-GATE-001/002、TD-TEST-001（最小集）、TD-PACKS-001 | 批次 1 | 禁用/删除 hook 与 workflow 文件；门禁脚本全部是新增文件，revert 即回退 |
| 3 | core 域 · bug 修复 | TD-CORE-003（权限）→ TD-CORE-001（双备份）→（若 D2 选 a）TD-CORE-002 代码面；**每项独立提交 + 回归测试先行** | 批次 2（护栏就位） | 每项单提交，`git revert <commit>` 精确回退；修复均附回归测试证明 |
| 4 | core/cli 域 · 纯重构 | TD-CLI-001/002/003、TD-CORE-004（按 D7）、TD-SCRIPTS-001（按 D5）；行为守恒对拍 | 批次 3 | 单提交 revert + 行为对拍脚本输出一致 |
| 5（=阶段 5） | 测试域 | 边界/异常/注入缺陷用例补全、覆盖率门禁、结构测试接入；TD-TEST-001 关闭 | 批次 4 | 新增测试文件 revert 即回退 |

## 5. 五阶段任务拆解

> 负责人角色约定（规则总纲「人类掌舵，智能体执行」）：**人类** = 确认/决策/验收；**智能体** = 产出全部代码、配置、文档并自验。下表「角色」列只标注需要人类介入的节点，其余默认智能体执行。

### 阶段 1 · 全量扫描与问题清单（本计划）

| # | 子任务 | 角色 | 产出物路径 | 可机械检查的验收标准 |
|---|---|---|---|---|
| 1.1 | 仓库地图 / 框架判定 / 架构 / 复杂度 / 重复 / 文档 / 测试 / 安全 / 性能 / 门禁 十项扫描 | 智能体 | 本文档 §1–§3；`docs/CI.md` | 本文档无空条目；`docs/CI.md` 含判定证据文件列表 |
| 1.2 | 风险分级与问题登记 | 智能体 | `docs/exec-plans/tech-debt-tracker.md` | 每条含 ID/位置/类别/严重度/证据/修复建议/行为影响；bug 类与重构类分列 |
| 1.3 | 度量基线固化 | 智能体 | `scripts/analysis/repo_metrics.py` | `python3 -I scripts/analysis/repo_metrics.py .` 退出码语义明确（0/1），输出含基线表 |
| 1.4 | **计划确认** | **人类** | 本文档状态字段 | 状态由「待确认」改「已确认」 |

### 阶段 2 · 文档对齐（批次 1）

| # | 子任务 | 角色 | 产出物路径 | 可机械检查的验收标准 |
|---|---|---|---|---|
| 2.1 | 按附录 E 写 `AGENTS.md`（≤100 行地图） | 智能体 | `AGENTS.md` | `wc -l` ≤ 200；含常用命令/目录地图/硬约束/下一站指针 |
| 2.2 | 写 `ARCHITECTURE.md`（分层与依赖方向白名单） | 智能体 | `ARCHITECTURE.md` | 与实际 import 图抽样比对 ≥3 处一致 |
| 2.3 | 建 docs 结构 + 索引 + `QUALITY_SCORE.md` + `core-beliefs.md`（附录 F） | 智能体 | `docs/**` | 文档 linter：`docs/index.md` 链接全部可解析；每个业务域有分数与复算依据 |
| 2.4 | 修正文档-代码矛盾（TD-SCRIPTS-002；TD-CORE-002 文档面按 D2） | 智能体 | `README.md`、`one-click-install.sh` 注释、`docs/**` | 矛盾点逐条复测关闭（沙箱用例） |
| 2.5 | 规则文档副本唯一化（按 D3） | **人类决策 → 智能体执行** | `docs/HARNESS-RULES.md`（+ 母本指针） | `diff -q` 无重复副本；母本位置有显式记录 |
| 2.6 | LICENSE / 版本声明（按 D4/D6） | **人类决策 → 智能体执行** | `LICENSE`（或决策记录）、README | 文件存在，或 `docs/CI.md`/计划中记录「决定不加」及理由 |

### 阶段 3 · 门禁审计与自动化质量校验（批次 2）

| # | 子任务 | 角色 | 产出物路径 | 可机械检查的验收标准 |
|---|---|---|---|---|
| 3.1 | 门禁宿主形态落地（按 D1/D8：Actions 或本地 hooks+一条命令） | **人类决策 → 智能体执行** | `docs/CI.md` 落地节；`.github/workflows/` 或 `Makefile`/脚本 | 干净环境（新 clone / 新目录）一条命令安装→构建→测试全绿 |
| 3.2 | 最小测试集（TD-TEST-001 前置） | 智能体 | `tests/` | pytest 全绿；覆盖 apply/remove/restore/backup/normalize/atomic_write/frontmatter |
| 3.3 | lint+test+build 三件套 + `pyproject.toml` 工具链声明（TD-GATE-002） | 智能体 | `pyproject.toml`、lint 配置 | 一条命令跑通三件套；零第三方运行时依赖不被破坏 |
| 3.4 | 品味不变量 linter（T1 文件/函数上限、T6 重复、pack 指纹断言） | 智能体 | `scripts/analysis/` 或 tests | 故意超长文件/篡改 pack → 门禁 FAIL 且报错含修复指引（实测留记录） |
| 3.5 | 文档门禁（死链/必填节/索引完整） | 智能体 | 文档 linter 脚本 + CI 作业 | 故意留死链 → FAIL（实测留记录） |
| 3.6 | `docs/CI.md` 收口：框架判定+门禁清单（每项：检查名/触发时机/失败含义/修复指引） | 智能体 | `docs/CI.md` | 清单覆盖全部已落地门禁 |

### 阶段 4 · 问题修复与重构（批次 3 + 4）

| # | 子任务 | 角色 | 产出物路径 | 可机械检查的验收标准 |
|---|---|---|---|---|
| 4.1 | TD-CORE-003 权限修复（bug 类，单独提交） | 智能体 | `lib/sf_core.py` + 回归测试 | 测试断言 install/uninstall/restore 前后权限不变（0600 保持） |
| 4.2 | TD-CORE-001 双备份修复（bug 类，单独提交） | 智能体 | `lib/sf_core.py` + 回归测试 | 测试断言 uninstall 仅新增 1 份备份 |
| 4.3 | TD-CORE-002 代码面（仅当 D2 选 a；bug 类，单独提交） | 智能体 | `lib/sf_core.py` + 回归测试 | 缺 append 的 pack 可安装/预览，与文档声明一致 |
| 4.4 | 纯重构：TD-CLI-001/002/003 + TD-CORE-004（按 D7）+ TD-SCRIPTS-001（按 D5） | 智能体 | `styleforge.py`、`lib/sf_core.py`、shell 脚本 | 行为对拍：重构前后 `--json` 输出逐字节一致（沙箱全命令对拍）；门禁全绿 |
| 4.5 | 台账与文档同步（结清移除、新发现登记、QUALITY_SCORE 更新） | 智能体 | tracker、计划 §7、`docs/QUALITY_SCORE.md` | 进度日志逐条可对应 commit（`git log --oneline` 核对） |

### 阶段 5 · 测试补全与门禁接入（批次 5）

| # | 子任务 | 角色 | 产出物路径 | 可机械检查的验收标准 |
|---|---|---|---|---|
| 5.1 | 边界/异常用例（空 settings、损坏 JSON、非法名、缺文件、只读目录、CRLF 往返） | 智能体 | `tests/` | 全绿；CRLF 字节往返断言（README:116 承诺的 byte-exact） |
| 5.2 | 注入缺陷抽查（防假测试） | 智能体 | 测试记录进计划 §7 | 随机注释掉 ≥3 处实现断言，对应测试必须转红（留记录） |
| 5.3 | 覆盖率门禁接入（整体下限 + 关键模块 sf_core 下限） | 智能体 | coverage 配置 + CI | 低于下限 FAIL（实测：临时调高下限验证拦截） |
| 5.4 | 全量测试连跑 3 次无失败（flaky 检查） | 智能体 | 计划 §7 记录 | 3 次 `pytest` 退出码均 0 |
| 5.5 | 收官拆解（规则 §14：归档施工图、长效契约迁入常驻文档） | **人类确认 → 智能体执行** | `docs/exec-plans/completed/harness-<日期>.md` | §14.6 自检：移除规则文档后仅凭 AGENTS/core-beliefs/ARCHITECTURE 仍能守住全部硬约束 |

## 6. 待人工决策清单

> **2026-10-14 答复记录**：D1=全干（git init + 远程，本地部分已执行完毕）；D2=选 b（修正 README 为必填，纯文档）；D3=保留两份规则文档、不处理（TD-DOCS-002 据此豁免）；D4/D5/D6/D7/D8=用户要求先获得通俗解释再决定，解释已在本轮对话出具，答复待回填。

| 编号 | 问题 | 为什么需要人判断 | 影响范围 |
|---|---|---|---|
| D1 | **是否 `git init`？是否配远程仓库（GitHub/私有）？** | 规则 C5/C6/§7 的可追溯性全部建立在版本管理上；仓库目前无 git。远程有无直接决定 CI 宿主形态 | 批次 0 全部、阶段 3 形态 |
| D2 | TD-CORE-002 修复方向：**a) 改代码**（缺 `claude-append-prompt.md` 视为空段，README 不动）还是 **b) 改文档**（README 改为必填，代码不动）？ | 「append 文件可选」是产品语义，无法从代码推断哪个是本意 | 批次 1/批次 3 |
| D3 | `docs/` 两份相同规则文档的取舍：`turn-project-to-harness-rules.md` 是母本误入还是应删副本？母本去向（模板库 / `docs/templates/`）？ | 母本是用户资产（规则 §14.5），智能体不应删除 | 批次 1 |
| D4 | 是否添加 LICENSE？何种协议？ | 法律决策 | 批次 1 |
| D5 | shell 探测逻辑是否收敛为共享脚本（TD-SCRIPTS-001）？ | one-shot 自包含 vs DRY 的取舍偏好 | 批次 4 |
| D6 | Python 最低版本：保留「3.8+」声明并纳入测试矩阵，还是提升到现实可测版本（本机 3.14）？ | 兼容承诺 = 维护成本，无法从代码推断用户意图 | 批次 1/2 |
| D7 | frontmatter 简化解析（TD-CORE-004）：仅文档化能力边界，还是增强实现？ | 取决于是否需要读取第三方 style 文件 meta 的真实场景 | 批次 4 |
| D8 | （依赖 D1）若配 GitHub 远程：是否生成 GitHub Actions CI（等效 §3.3 问 1 的本地化版本）？ | 规则 §3.3 明确"是否上 CI"是不可推断的产品决策，虽非 Tauri，是否生成远程 CI 仍应问 | 阶段 3 |

## 7. 进度与决策日志

| 日期 | 阶段 | 动作 | 关联 commit | 决策与理由 |
|---|---|---|---|---|
| 2026-10-14 | 1 | 全量扫描完成：10 项子任务（§5 阶段 1.1）、18 项问题登记、度量基线固化、框架判定=其他类型（非 Tauri，证据落盘 `docs/CI.md`） | —（尚无 git，D1 待决） | 沙箱实测坐实 3 个 bug 类问题（TD-CORE-001/002/003）；业务代码零改动声明见下 |
| 2026-10-14 | 1→批次 0 | 用户答复 D1=全干 / D2=b / D3=保留；执行 git init + `.gitignore` + 基线提交 `59076a0`（main，零改动快照）+ `harnessing` 分支 + 阶段 1 产出提交 `2fecb40`；TD-REPO-001/002 关闭、TD-DOCS-002 豁免、TD-CORE-002 定向（b 方案） | `59076a0`、`2fecb40` | 基线快照即「未改业务代码」的 git 自证；gh CLI 已装但认证超时（keyring），远程创建待用户提供途径（见 §6 答复记录） |
| 2026-10-14 | 1 | 向用户出具 D4–D8 白话解释与推荐（对话内），等待表态后回填本表并切换计划状态 | — | 用户明确要求解释后再决策（C7：不确定就提问） |
| | | | | **未改业务代码自证**：本阶段仅新增 `docs/exec-plans/`、`docs/CI.md`、`scripts/analysis/repo_metrics.py`、`prompt-history.txt` 四类文档/分析文件；`styleforge.py`、`lib/sf_core.py`、`one-click-*.sh`、`styleforge.cmd`、`README.md`、`packs/**`、`docs/HARNESS-RULES.md` 均未触碰（git 就位后首批提交可用 `git diff` 复核）。沙箱实验（临时 pack `__td_probe__` 与 `/tmp` 下 `STYLEFORGE_HOME`）已全部清理，仓库无残留 |

---

**阶段 1 验收对照**（规则 §5）：

- [x] 五个阶段全部拆解：§5 每个子任务有角色 / 产出物路径 / 可机械检查的验收标准
- [x] 框架判定已完成，命中证据（文件路径）已写入 `docs/CI.md`
- [x] 问题清单每条含 ID / 位置（文件:行）/ 类别 / 严重度 / 证据 / 修复建议 / 业务行为影响（`tech-debt-tracker.md`）
- [x] bug 修复（TD-CORE-001/002/003 标注「修复 bug」）与纯重构（TD-CLI-001/002/003 等）严格分列，且 bug 类均要求单独提交
- [x] 每批改造有独立回滚方案（§4 表）
- [x] 无只有标题没有分析的条目
- [x] 未修改任何业务代码（无 git 无法跑 `git diff --stat`，以 §7 自证声明 + 上述文件清单代替；git 就位后首批提交复核）
