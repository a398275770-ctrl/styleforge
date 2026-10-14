# styleforge

Claude Code **持久化提示词注入器**。基于 `settings.json` 的 `outputStyle` 官方通道，
不需要 shell wrapper、不需要 CLI flag、不需要接管 `claude` 命令。

原版工具（keysmith-claude.exe v7.2）靠劫持 `~/.zshrc` / PowerShell `$PROFILE`
里的 `claude()` 函数，每次调用强加 `--system-prompt-file` 和
`--append-system-prompt-file`。styleforge 用官方配置通道达到同一层级的注入。

## 机制（已在 Claude Code 2.1.296 实测）

```
~/.claude/settings.json            { "outputStyle": "default" }
~/.claude/output-styles/default.md  ← frontmatter 的 name: 必须与上面的键相同
                     ↓
        系统提示词里的 "Output Style: default" 段
        （与内置工具定义同级，保留全部工具说明）
```

### 为什么不是别的通道

同一台机器上用 canary 字符串逐条实测的结果：

| 通道 | 进入系统提示词 |
|---|---|
| `--system-prompt` (CLI) | 是 |
| `--append-system-prompt` (CLI) | 是 |
| **`settings.json` → `outputStyle`** | **是** |
| `settings.json` → `systemPrompt` | 否 |
| `settings.json` → `appendSystemPrompt` | 否 |
| `settings.json` → `systemPromptFile` | 否 |
| `settings.json` → `appendSystemPromptFile` | 否 |
| `settings.json` → `env.CLAUDE_CODE_SYSTEM_PROMPT` | 否 |

`settings.systemPrompt` 一族被 harness 接受但忽略——这正是原版作者注释里
`settings.systemPrompt alone does not unlock hard NSFW` 的由来。他的判断没错，
只是当时没有 `outputStyle` 这条路。

### 两个必须注意的语义

1. **键匹配的是 frontmatter 的 `name:` 字段，不是文件名。**
   两者不一致时以 `name:` 为准；文件没有 frontmatter 时回落到文件名。
2. **Claude Code 只认 `$HOME`。** styleforge 支持 `$STYLEFORGE_HOME` 覆盖
   home 目录（方便测试），但 Claude Code 本身读的是 `$HOME`，所以想换 home
   必须改 `$HOME`。

## 快速开始

```bash
# 一键安装（默认 pack）
./one-click-install.sh

# 或显式指定
python3 styleforge.py install --pack default

# 查看状态
python3 styleforge.py status

# 自检本机机制是否可用
python3 styleforge.py doctor

# 一键卸载
./one-click-uninstall.sh
```

安装后**新开一个会话**生效。

### Windows

```bat
styleforge.cmd              :: 安装默认 pack
styleforge.cmd install mypack
styleforge.cmd uninstall
styleforge.cmd status
styleforge.cmd doctor
```

或装 Git Bash / MSYS2 后用 `one-click-install.sh`。

## 命令

| 命令 | 作用 |
|---|---|
| `install --pack <p> [--name <n>] [--description <d>]` | 安装 pack 为激活 style |
| `status` | 当前激活 style、来源 pack、备份数 |
| `doctor` | 检查 home / settings / styles 目录 / pack 是否就绪 |
| `uninstall [--name <n>]` | 一键卸载，移除键和文件，保留备份 |
| `restore --backup <path>` | 从备份恢复 settings.json |
| `backups` | 列出所有 settings.json 备份 |
| `packs` | 列出可用 pack |
| `preview --pack <p> [--raw]` | 预览将写入的内容 |

全局选项：`--json`（稳定 JSON 输出，schema `styleforge/v1`）、`-q/--quiet`。
两种位置都支持：`styleforge -q install` 和 `styleforge install -q`。

## 安全性

- **只动一个键。** `settings.json` 里的其他内容（model / language / env /
  permissions / hooks / ...）原样保留，已验证。
- **写入前自动备份** 为 `settings.json.styleforge-bak.<时间戳>`，权限 0600。
- **原子写**：临时文件 + `os.replace`，不会留下半截 JSON。
- **幂等**：内容没变就不写、不备份。
- **可完全回退**：`uninstall` 删键删文件，`restore` 从备份还原。
- **settings.json 损坏时不乱动**：解析失败直接报错退出，不覆盖。
- **style 名白名单**：拒绝路径分隔符、`..`、shell 特殊字符。

## 自定义 pack

```
packs/<pack名>/
├── claude-project-rules.md     ← 必填，system 层内容
└── claude-append-prompt.md     ← 可选，append 层内容
```

两个文件会按此顺序拼成 style 正文，各自剥掉开头的 `# H1`。
文件是 CRLF 也不会被改写（读取走 `read_bytes().decode()`，写入走二进制模式）。

```bash
mkdir -p packs/mypack
echo '# 我的规则' > packs/mypack/claude-project-rules.md
python3 styleforge.py install --pack mypack --name my-style --description "我的规则"
```

## 与原版 keysmith 的差异

| | keysmith.exe | styleforge |
|---|---|---|
| 注入通道 | shell wrapper + CLI flag | `settings.json` 的 `outputStyle` |
| 接管 `claude` 命令 | 是（zsh + PowerShell 双平台） | 否 |
| 改 shell 配置文件 | 是 | 否 |
| 改 settings.json | 4 个字段 | 1 个键 |
| 原子写 / 备份 | 有 | 有 |
| 锁 + 两阶段事务日志 + 回滚机 | 有 | 无（单键幂等写不需要） |
| 旧 launcher 迁移 | 有 | 无 |
| 按项目切换不同规则 | 做不到 | 项目级 settings 可覆盖 `outputStyle` |
| 卸载残留 | 需跑 uninstall | 删一键，零残留 |

原版那套锁和事务机制，全是为了安全地改 `~/.zshrc` 和 `~/.local/bin` 才被迫上的；
styleforge 只写一个 JSON 键，复杂度掉一个数量级。

## 环境变量

| 变量 | 作用 |
|---|---|
| `STYLEFORGE_HOME` | 覆盖 styleforge 自己解析的 home（**不影响 Claude Code**） |
| `HOME` | Claude Code 实际读取的 home；两个工具都认这个 |

## 文件

```
styleforge/
├── styleforge.py              CLI 主程序
├── one-click-install.sh       一键安装
├── one-click-uninstall.sh     一键卸载
├── styleforge.cmd             Windows 一键入口
├── lib/sf_core.py             核心库
├── packs/default/             默认 pack（与原版 exe 内 payload 逐字节相同）
│   ├── claude-project-rules.md     770 B  md5 0164424cca30ee1961d273ce8091649b
│   └── claude-append-prompt.md     202 B  md5 80ef73f84f2c589b524108dfecf01f90
└── packs/<你的>/              自定义 pack
```

## 已知限制

- `outputStyle` 写入的是**用户级** settings.json，对该用户所有项目生效。
  要按项目区分，在项目 `.claude/settings.json` 里写不同的 `outputStyle` 覆盖它。
- Claude Code 升级若改动 output style 的解析规则，先跑 `styleforge.py doctor`，
  再用 `preview --raw` 对比实际内容。
