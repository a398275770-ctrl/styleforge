# 安全模型（SECURITY）

styleforge 直接修改用户的 `~/.claude/settings.json` 并在 home 下落文件——安全是本工具的核心契约，不是附属品。

## 安全承诺（已实现，机械可验）

| 承诺 | 实现位置 | 验证方式 |
|---|---|---|
| 只动 `outputStyle` 一个键，其余用户配置原样保留 | `lib/sf_core.py` `OWN_KEYS` | 沙箱对拍（阶段 5 补回归测试） |
| 写前备份，权限 0600 | `backup_settings` | 测试断言 |
| 原子写，不留半截 JSON | `atomic_write_text`（temp + `os.replace` + fsync） | 测试断言 |
| settings 损坏时拒绝写入并报错 | `load_settings_raw` 抛 `SettingsCorrupt` | 测试断言 |
| style/pack 名白名单（拒路径穿越、`..`、shell 特殊字符） | `normalize_style_name` / `pack_dir` | 测试断言 |
| 幂等：内容没变不写不备份 | `apply_style` noop 分支 | 测试断言 |

## 已知问题（在册，勿重复登记）

- **TD-CORE-003（P0）**：`atomic_write_text` 默认 mode 0644，经 `os.replace` 覆盖后 settings.json 原有 0600 权限被放宽（2026-10-14 实测 600→644）。批次 3 修复：写前保留原文件权限。修复前，多用户机器上的用户请注意 settings.json 权限。

## 上游输入面（信任边界）

- `packs/`：仓库内资产，md5 指纹登记于 README 并可复算（`repo_metrics.py`）。自定义 pack 属用户自担内容。
- `~/.claude/settings.json`：只读解析 + 单键写入；解析失败即拒绝一切写操作。
- frontmatter：仅解析本工具生成的简单格式（见 ARCHITECTURE.md §2.7 能力边界），不信任复杂结构。

## 依赖面

- 零第三方运行时依赖（core-beliefs #16），无供应链扫描面；阶段 3 起仍建依赖扫描门禁以约束未来引入。

## 漏洞上报

公开仓库 issue：https://github.com/a398275770-ctrl/styleforge/issues
