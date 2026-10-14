# docs/ 索引

> 本文件是全部文档的目录。每份文档一行；校验状态由 `scripts/analysis/doc_lint.py` 机械检查（链接可解析、必填节齐全）。

## 根级地图

| 文档 | 内容 | 校验状态 |
|---|---|---|
| [../AGENTS.md](../AGENTS.md) | 入口地图（目录，非百科） | doc_lint PASS |
| [../ARCHITECTURE.md](../ARCHITECTURE.md) | 分层、依赖方向、设计决策、耦合面 | doc_lint PASS |

## docs/

| 文档 | 内容 | 校验状态 |
|---|---|---|
| [CI.md](CI.md) | 框架判定 + CI 决策记录 | doc_lint PASS |
| [QUALITY_SCORE.md](QUALITY_SCORE.md) | 按域质量评分与差距 | doc_lint PASS |
| [SECURITY.md](SECURITY.md) | 安全模型、信任边界、已知问题 | doc_lint PASS |
| [design-docs/index.md](design-docs/index.md) | 设计文档索引 | doc_lint PASS |
| [design-docs/core-beliefs.md](design-docs/core-beliefs.md) | 第一性原则与裁决依据 | doc_lint PASS |
| [exec-plans/active/harness-migration.md](exec-plans/active/harness-migration.md) | 进行中的改造计划（含决策日志） | doc_lint PASS |
| [exec-plans/tech-debt-tracker.md](exec-plans/tech-debt-tracker.md) | 技术债台账 | doc_lint PASS |
| [HARNESS-RULES.md](HARNESS-RULES.md) | harness 改造施工图（施工期常驻，竣工后归档） | 施工中，不参与门禁 |
| [turn-project-to-harness-rules.md](turn-project-to-harness-rules.md) | 施工图母本副本（D3 保留） | 施工中，不参与门禁 |

## 待建（随阶段推进）

- `gates.md`：门禁清单（每项：检查名/触发时机/失败含义/修复指引）——阶段 3
- `exec-plans/completed/`：已归档计划——阶段 4/5 逐批移入
