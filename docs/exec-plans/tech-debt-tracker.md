# 技术债台账（tech-debt-tracker）

> 字段定义见施工图附录 B（已归档：`completed/harness-2026-10-14.md`）；本表头即长期约定。
> 状态流转：待处理 → 处理中 → 已完成 / 已豁免（须附理由与到期时间）。
> 登记纪律（规则 §5 阶段 1）：只登记不顺手修；每条必须有文件:行级证据；「bug 修复」与「业务变更」与纯重构严格分列。
> 基线度量：`python3 -I scripts/analysis/repo_metrics.py .`（2026-10-14 基线：业务代码零超长热点，`lib/__pycache__` 1 处 FAIL）。

## 问题清单

| ID | 标题 | 位置 | 类别 | 严重度 | 证据 | 修复建议 | 业务行为影响 | 关联批次 | 验收方式 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|
| TD-REPO-001 | 仓库无版本管理（不是 git 仓库） | 仓库根 | 依赖 | **P0** | `git rev-parse --is-inside-work-tree` 于 2026-10-14 实测报「不是 Git 仓库」 | `git init` + 首次全量提交 + 建 `harnessing` 分支（规则 §7.1）；待 D1 决策（含是否配远程） | 无 | 批次 0 | `git log` 可见首提交与 harnessing 分支；`git status` 干净 | **已完成**（commit `59076a0`，2026-10-14；远程 `https://github.com/a398275770-ctrl/styleforge` 已建并推送，main + harnessing 双分支跟踪） |
| TD-REPO-002 | 无 `.gitignore`，且存在字节码缓存产物 | `lib/__pycache__/sf_core.cpython-314.pyc` | 依赖 | P1 | 2026-10-14 实测存在该 .pyc（早于本改造会话生成）；`repo_metrics.py` 基线报告 FAIL 1 处 | 批次 0 建立 `.gitignore`（至少含 `__pycache__/`、`*.pyc`、`prompt-history.txt`，见规则 §6.3） | 无 | 批次 0 | `repo_metrics.py` 应忽略产物检查转 PASS；`git status` 不出现缓存文件 | **已完成**（git 层面：commit `59076a0` 的 `.gitignore` 生效，`git status` 干净；`repo_metrics.py` 的 PASS 判定待阶段 3 让脚本尊重 `.gitignore`，并入 TD-GATE-001 实现细节） |
| TD-CORE-001 | uninstall 一次产生两份完全相同的备份 | `lib/sf_core.py:384-387`、`lib/sf_core.py:393-396` | 复杂度 | P2 | 2026-10-14 沙箱实测（`STYLEFORGE_HOME=$(mktemp -d)`）：一次 uninstall 生成 `settings.json.styleforge-bak.20261014_085139-uninstall` 与 `-uninstall.2` 两份同秒同内容备份 | `remove_style` 内统一只做一次卸载前备份（删 style 文件与改 settings 共用同一份） | **修复 bug**（消除冗余产物，须单独提交并附回归测试） | 批次 3 | 回归测试断言：uninstall 后备份目录仅新增 1 个文件 | **已完成**（commit `e6c16fa`：统一一份卸载前备份；四组合行为对照，唯一行为 diff=正常场景备份 2→1，全命令对拍留证） |
| TD-CORE-002 | README 称 `claude-append-prompt.md` 可选，代码缺失即报错 | `README.md:112` vs `lib/sf_core.py:289-290` | 文档 | P1 | 2026-10-14 实测：构造仅含 `claude-project-rules.md` 的 pack，`build_style_body` 抛 `文件不存在: .../claude-append-prompt.md`（probe pack 已清理，仓库无残留） | 已决策（D2=选 b，2026-10-14）：修正 README 为必填（纯文档），代码行为保持不变 | 无（b 方案：纯文档修正） | 批次 1 | 机械用例：缺 append 的 pack 上 `preview`/`install` 行为与文档声明一致 | **已完成**（commit `0872510`，2026-10-14：README 改为两文件均必填，与实测行为一致） |
| TD-CORE-003 | 重写 settings.json 时权限被放宽（0600 → 0644） | `lib/sf_core.py:122`（`mode=0o644` 默认值）、`lib/sf_core.py:359`、`lib/sf_core.py:399`、`lib/sf_core.py:419` | 安全 | **P0** | 2026-10-14 沙箱实测：`chmod 600 settings.json` 后执行 install，`stat -c '%a'` 由 600 变 644；且 `lib/sf_core.py:19-20` 模块 docstring 声称「0600 permissions」与实现不符。settings.json 可含 env/hooks 等敏感配置 | `atomic_write_text` 写 settings.json 前保留原文件 mode（`stat` 复制），新建时用 0600；同步修正 docstring | **修复 bug**（权限收窄为正确行为，须单独提交并附回归测试） | 批次 3 | 回归测试断言：install/uninstall/restore 前后 settings.json 权限不变；docstring 与实测一致 | **已完成**（commit `fef3456`：atomic_write_text 沿用已有权限、新建一律 0600、docstring 一致化；8 用例 TDD，实测 chmod600→install→仍 600） |
| TD-CORE-004 | frontmatter 解析为简化实现，不支持数组/嵌套 YAML | `lib/sf_core.py:259-270` | 架构 | P2 | 实现仅 `partition(':')` + 引号 strip，无 YAML 库；读取非本工具生成的 style 文件 meta 时可能失真 | 已决策（D7=文档化，2026-10-14）：不改代码，在 docs 写明解析能力边界（仅支持单行 `key: value`，不支持数组/嵌套 YAML；读取面只影响 `status` 展示） | 无 | 批次 1 | docs 中存在「解析能力边界」节且与代码一致 | **已完成**（commit `481c9be`，2026-10-14：ARCHITECTURE.md §2.7 落地能力边界与不升级的理由） |
| TD-CLI-001 | `cmd_doctor` 直接访问 `Out` 私有成员 `out._exit` | `styleforge.py:209`、`styleforge.py:239` | 架构 | P2 | 代码两处引用私有属性完成置错，封装泄漏 | `Out` 增加公有 `fail()` 方法，`check()` 闭包改走公有接口 | 无（纯重构） | 批次 4 | `grep -n '_exit' styleforge.py` 仅剩 `Out` 内部定义；doctor 输出对拍一致 | **已完成**（commit `a0d5df8`：公有 fail()/is_blocked()；grep 验证 _exit 仅存 Out 类内；对拍逐字节一致） |
| TD-CLI-002 | `main()` 以子串匹配判断 JSON 模式 | `styleforge.py:327` | 复杂度 | P2 | `'--json' in argv` 对任意参数值做子串匹配：`restore --backup /tmp/--json` 会误触发 JSON 输出 | 改为解析后扫描 `argparse` 命名空间，或对 argv 元素做全等匹配 | 无（纯重构） | 批次 4 | 构造 `--backup <含--json子串路径>` 用例断言非 JSON 输出 | **已完成（误报关闭，2026-10-14 实测证伪）**：`'--json' in argv` 是列表成员判断（精确全等）而非子串匹配，`restore --backup /tmp/--json-looks-like-flag` 实测输出文本错误非 JSON。阶段 1 登记时分析有误；原防御逻辑无害，保留不动 |
| TD-CLI-004 | `preview --raw` 泄漏 header 行：重定向产物首行是 `preview` 标题 | `styleforge.py` cmd_preview（`out.header` 先于 `--raw` 分支执行） | 复杂度 | P1 | 2026-10-14 阶段 5 补测时实测发现：`preview --pack default --raw \| od -c` 首字节为 `p r e v i e w \n`，与帮助文本「只输出原始内容（便于重定向）」不符 | raw 分支不再调用 header（JSON payload 的 operation 字段保留） | **修复 bug**（--raw 输出内容变化：去掉首行泄漏） | 批次 5 | 测试断言 raw 输出以 `---` 开头 | **已完成**（commit `4ba9ce3`：raw 分支不再调 header；回归断言即发现者） |
| TD-CLI-003 | install 半完成无补偿：先写 style 文件，settings 写失败会留孤儿文件 | `lib/sf_core.py:352-359` | 架构 | P2 | 代码顺序：`atomic_write_text(target...)` 先于 settings 写入；settings 阶段抛错时 style 文件已落盘 | settings 写失败时回删本次写入的 style 文件（补偿式回滚），或调整写入顺序 | 无（异常路径行为，非正常路径） | 批次 4 | 注入 settings 写失败（只读目录）用例，断言无孤儿 style 文件 | **已完成**（commit `7eee9bc`：新建回删 + 覆写恢复原内容 + settings 不被半改；2 注入用例 TDD；正常路径对拍逐字节一致） |
| TD-SCRIPTS-001 | 两个 one-shot 脚本重复 12 行 python 探测逻辑 | `one-click-install.sh:9-20` vs `one-click-uninstall.sh:9-17` | 重复 | P2 | 两段逐字相同（T6 共享工具优先）；`styleforge.cmd:11-14` 为平台差异无法共享 | 已决策（D5=保持两份，2026-10-14）：接受现状（one-shot 自包含是合理取舍），两个脚本各加注释说明系有意为之 | 无 | 批次 1 | 注释存在且说明理由 | **已完成**（commit `0872510`，2026-10-14：两脚本探测块各加 NOTE） |
| TD-SCRIPTS-002 | `one-click-install.sh` 注释称 "no arguments" 但实际接受 pack 参数 | `one-click-install.sh:2` vs `one-click-install.sh:22-23` | 文档 | P2 | 注释与 `PACK="${1:-default}"` 实现矛盾 | 修正注释为 `install [pack]`（纯文档） | 无 | 批次 1 | 注释与实测行为一致（人工核对 + 文档门禁） | **已完成**（commit `0872510`，2026-10-14：注释改为 `Usage: one-click-install.sh [pack]`） |
| TD-DOCS-001 | 缺 §2.1 必需四件：AGENTS.md / ARCHITECTURE.md / docs 结构 / QUALITY_SCORE.md | 仓库根、`docs/` | 文档 | P1 | 2026-10-14 全仓 `find`：无上述文件；`docs/` 仅有两份规则文档 | 阶段 2 按附录 E/F 模板落地全量结构（含 `docs/exec-plans/` 本目录即首批产出） | 无 | 批次 1 | 文档 linter：链接可解析、必填节齐全、AGENTS.md ≤200 行 | **已完成**（commit `481c9be`+`fd7a672`，2026-10-14：AGENTS.md 60 行、ARCHITECTURE.md、docs 全结构、QUALITY_SCORE.md；`doc_lint.py` 死链/缺节反向实测均拦截） |
| TD-DOCS-002 | `docs/` 存在两份内容完全相同的规则文档 | `docs/HARNESS-RULES.md`、`docs/turn-project-to-harness-rules.md` | 文档 | P2 | 2026-10-14 `diff -q` 无差异；规则 §14.5 要求母本与仓库副本分开管理 | 按 D3 决策：保留 `docs/HARNESS-RULES.md` 为施工图副本，另一份的去向（删除/移出仓库/作为母本入库 `docs/templates/`）由用户定 | 无 | 批次 1 | 仓库内施工图副本唯一，且母本位置有显式指针（§14.5） | **已豁免**（用户 2026-10-14 决定：两份均保留、不处理；到期时间：无，长期豁免） |
| TD-DOCS-003 | 无 LICENSE / CHANGELOG；Python 3.8+ 兼容声明从未验证 | 仓库根、`one-click-install.sh:18`、`one-click-uninstall.sh:18` | 文档 | P2 | 全仓无 LICENSE/CHANGELOG；本机仅 Python 3.14，3.8+ 声明无 CI 矩阵背书 | 已决策（2026-10-14）：D4=加 MIT LICENSE；D6=Python 最低版本改为 3.10+（3.14 开发验证），README 与两个 shell 脚本提示语同步修改 | 无 | 批次 1 | LICENSE 存在；版本声明与 CI 矩阵一致 | **已完成**（commit `481c9be`+`0872510`，2026-10-14：MIT 建立；3.10+ 声明落 README/2×sh/1×cmd。CI 矩阵背书随 TD-GATE-001 在批次 2 接入） |
| TD-TEST-001 | 全仓零测试 | 全仓 | 测试 | **P0** | 2026-10-14 全仓 `find`：无 tests/、无 `*test*.py`；doctor 自称「检查机制可用」但无回归用例。阻塞规则红线 R3（无护栏不得重构） | 阶段 3 前置最小测试集（apply/remove/restore/backup/normalize_style_name/atomic_write/parse_frontmatter，全部可用 `STYLEFORGE_HOME` 沙箱隔离）；阶段 5 补全边界与注入用例并接覆盖率门禁 | 无 | 批次 2（最小集）/ 批次 5（补全） | pytest 全绿；覆盖率 ≥ 门禁值；注入缺陷用例必须失败（阶段 5 抽查 ≥3 处） | **处理中**（2026-10-14 最小集落地：88 用例全绿、沙箱铁律 autouse、注入缺陷抽查 2/3 处有效；边界/异常补全与覆盖率门禁留批次 5） | **已完成**（2026-10-14：124 用例 / 覆盖 94% 门禁 90 / 注入抽查 4 处全有效 / 3 连跑无失败，commit `c2f50a2`+`88c35c2`） |
| TD-GATE-001 | 零提交门禁：无 CI、无 hooks、无 lint/format/type-check | 仓库根 | 门禁 | **P0** | 2026-10-14 实测：`.github/` 不存在；无 pre-commit/husky 配置；无 ruff/flake8/mypy/black 配置文件 | 阶段 3 按规则 §3.4（框架=其他类型）落地 lint+test+build 三件套 + 品味不变量 linter + 文档门禁；形态按 D1/D8（有远程→Actions；无远程→本地一条命令 + git hooks） | 无 | 批次 2（=阶段 3） | 干净环境一条命令全绿；故意违规（越层/超长/死链）实测被拦截 | **已完成**（2026-10-14：`scripts/check.sh` 六步 + `.githooks/pre-commit` + `ci.yml`（py3.10/3.14 矩阵）；四类违规注入实测全部拦截，记录于计划 §7） |
| TD-GATE-002 | 无工具链声明（无 pyproject.toml），依赖隐式 `sys.path` hack | `styleforge.py:11` | 门禁 | P1 | 2026-10-14 实测：无 pyproject.toml/setup.cfg/requirements*；`sys.path.insert` 手工注入 lib | 阶段 3 决策：建议最小 `pyproject.toml`（仅声明 lint/test 工具链与 Python 版本，不发布包），保留零第三方运行时依赖（R6） | 无 | 批次 2 | `pyproject.toml` 存在且工具链一条命令可装可跑 | **已完成**（commit `f05ea8b`：pyproject 纯 tool 配置、零运行时依赖保持、版本单点声明由结构测试强制） |
| TD-PACKS-001 | packs 资产指纹仅手工记录在 README，无机械校验 | `README.md:158-159` | 文档 | P2 | README 手工登记 md5；改动 pack 内容无法被机器发现（README 声称「与原版 exe payload 逐字节相同」需可持续验证） | 阶段 3 把 `repo_metrics.py` 的指纹输出固化为断言脚本（改动即 FAIL，错误信息含修复指引） | 无 | 批次 2 | 篡改 pack 内容时校验脚本退出码非 0 | **已完成**（2026-10-14：`tests/test_packs.py` 三断言——README 登记完整性 / md5 与字节一致 / CRLF 存活，指纹漂移即测试红） |

## 优先级定义（附录 B）

| 级别 | 判定标准 | 处理时限 |
|---|---|---|
| **P0** | 影响正确性/安全性/可用性；或阻塞后续所有改造 | 当前批次内必须解决 |
| **P1** | 显著抬升维护成本或缺陷概率；不立即阻断 | 计划内排期 |
| **P2** | 体验与整洁度问题，可延后 | 有空再做，登记不丢 |

## 统计与趋势

| 日期 | P0 | P1 | P2 | 合计 | 备注 |
|---|---|---|---|---|---|
| 2026-10-14（阶段 1 基线） | 4 | 5 | 9 | 18 | 首次登记；P0 = TD-REPO-001 / TD-CORE-003 / TD-TEST-001 / TD-GATE-001 |
| 2026-10-14（批次 0 后） | 3 | 4 | 8 | 15 | 关闭 TD-REPO-001/002；豁免 TD-DOCS-002；TD-CORE-002 定向 b 方案（仍在册，批次 1） |
| 2026-10-14（阶段 2 后） | 3 | 1 | 4 | 8 | 关闭 6 项：TD-CORE-002/004、TD-SCRIPTS-001/002、TD-DOCS-001/003；在册 P0 = TD-CORE-003 / TD-TEST-001 / TD-GATE-001（全部批次 2/3 处理） |
| 2026-10-14（阶段 3 后） | 2 | 0 | 4 | 6 | 关闭 TD-GATE-001/002、TD-PACKS-001；TD-TEST-001 转处理中（最小集 88 用例就位）；在册 P0 = TD-CORE-003（批次 3 修复）/ TD-TEST-001 补全（批次 5） |
| 2026-10-14（阶段 4 后） | 1 | 0 | 0 | 1 | 关闭 5 项：TD-CORE-003/001（bug 修复，独立提交）、TD-CLI-001/003（纯重构，对拍守恒）、TD-CLI-002（误报证伪关闭）；唯一在册 = TD-TEST-001（处理中，批次 5 补全） |
| 2026-10-14（阶段 5 后·竣工） | 0 | 0 | 0 | 0 | **台账清零**：TD-TEST-001 关闭（124 用例/94%/门禁 90）；阶段 5 新发现的 TD-CLI-004 已发现即修复关闭。长期豁免 1 项不计在册：TD-DOCS-002（D3 用户决策） |
