# ARCHITECTURE.md

styleforge 的领域与分层地图。改动任何代码前先读本文；与代码不一致时以代码为准并立刻修本文。

## 1. 分层与依赖方向（唯一允许的边）

```text
one-click-install.sh ─┐
one-click-uninstall.sh ├──→ styleforge.py ────→ lib/sf_core.py ────→ 标准库 + 文件系统
styleforge.cmd ───────┘     （CLI 层）          （core 层）            （~/.claude/ 与仓库内 packs/）
```

| 层 | 模块 | 职责 | 允许依赖 |
|---|---|---|---|
| 入口层 | `one-click-*.sh`、`styleforge.cmd` | 找到 Python，转发给 CLI；无任何业务逻辑 | CLI 层 |
| CLI 层 | `styleforge.py` | argparse 解析、`Out` 输出/退出码、命令编排、错误转译（`StyleForgeError` → 用户消息） | core 层、标准库 |
| core 层 | `lib/sf_core.py` | 全部业务：路径解析、settings 读写、备份、命名白名单、pack 读取、style 组装、install/uninstall/restore | 仅标准库 |
| 资产层 | `packs/<名>/*.md` | 提示词内容（CRLF，字节保真） | —（纯数据） |

**禁止的边**（阶段 3 结构测试将机械校验）：

- core 层 import CLI 层（反向依赖）
- CLI 层绕过 core 直接读写 `~/.claude/`
- 任何层引入第三方运行时依赖

横切关注点只有一个：错误通道。core 只抛 `StyleForgeError` 子类，CLI 统一捕获转译为 `Out.error` + 退出码 1。不存在第二个横切机制。

## 2. 关键设计决策（为什么）

1. **`outputStyle` 通道（而非 `systemPrompt` 族）**：同一机制实测（Claude Code 2.1.296），`settings.json` 里 `systemPrompt` / `appendSystemPrompt` / `systemPromptFile` / `env.CLAUDE_CODE_SYSTEM_PROMPT` 均被 harness 接受但忽略；只有 `outputStyle` 进入系统提示词层。见 README 通道对比表。
2. **键配对语义**：settings 的键匹配 style 文件 frontmatter 的 `name:` 字段（不是文件名）。frontmatter 由本工具生成（`style_frontmatter`），因此配对可控。
3. **单一管理键**：只写 `outputStyle` 一个键（`OWN_KEYS`），其余用户配置原样保留。这是本工具对原版 keysmith 的核心简化。
4. **原子写**：temp + `os.replace` + `fsync`，绝不留半截 JSON；备份在改动 settings 之前落盘（`backup_settings`，0600，时间戳命名）。
5. **CRLF 字节保真**：pack 读取一律 `read_bytes().decode('utf-8')`，禁止 `Path.read_text()`（universal-newline 会把 CRLF 静默翻译成 LF）。写入走二进制模式。README 的 md5 指纹依赖这一性质。
6. **`$HOME` 解析顺序**：`$STYLEFORGE_HOME`（测试沙箱）> `$HOME`（Claude Code 只认这个）> `expanduser('~')`。Windows 下 `$HOME` 优先于 USERPROFILE，因为 Git Bash 会导出 `$HOME`。
7. **frontmatter 解析能力边界（D7 决策，2026-10-14）**：`parse_frontmatter` 只支持单行 `key: value`，不支持数组/嵌套 YAML。这不升级为完整 YAML 解析——frontmatter 由本工具生成、格式自控，读取面仅影响 `status` 的展示信息。若未来需读取第三方 style 的复杂 meta，先在 `tech-debt-tracker.md` 立项再动。

## 3. 与 Claude Code 的耦合面

| 耦合点 | 风险 | 检测手段 |
|---|---|---|
| `outputStyle` 键语义 | Claude Code 升级改变解析规则 | `styleforge.py doctor`（每次升级后先跑） |
| frontmatter `name:` 配对 | 同上 | doctor + `status` 的 `[缺失]` 标记 |
| `~/.claude/output-styles/` 目录 | 路径变更 | doctor 的目录检查 |

## 4. 版本与兼容

- Python **3.10+**（2026-10-14 D6 决策；3.14 开发验证）。语法特性不得低于此承诺（阶段 3 CI 双版本矩阵背书）。
- 工具自身版本：`lib/sf_core.py` 的 `VERSION`（单点声明，安装时写入 frontmatter `styleforge:` 字段）。

## 5. 已知边界（不修复，登记在案）

- `atomic_write_text` 权限语义、uninstall 双备份、`--json` 子串误判等：见 `docs/exec-plans/tech-debt-tracker.md`（P0/P1 项将在阶段 4 批次 3 处理）。
