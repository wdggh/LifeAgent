# 03: ADR/README/词表同步与 V2.3 收口

**What to build:** 校验 ADR-0011（混合检索 + RRF + 索引生命周期）；README
记录 V2.3 A/B/归因结论与对照基线；CONTEXT.md 判断是否新增术语
（"知识库"已有，"StoredChunk"已有；预期不加并记录理由）；resolve 本 feature
全部 ticket，并说明 V2.4（cross-encoder reranker）的衔接。

**Blocked by:** 05（V2.3b 结束后统一收口，覆盖 02 + V2.3b 的完整闭环）

**Status:** resolved

- [ ] ADR-0011 与实现一致（引擎/参数/失效机制/tie-break/fail-open）
- [ ] README V2.3 段：A/B 结果、四类归因、answer-013 证据、结论
- [ ] CONTEXT.md 决策记录（加或明确不加 + 理由）
- [ ] 全部 ticket resolved，frontier 清空

## Comments

## Answer

V2.3 闭环收口（02 + V2.3b + 03）：

- ADR-0011 增加 2026-09-11 更新段：等权 RRF 失败原因（异构通道稀释强通道）、
  V2.3b 三臂结论（dense-priority no-op、加权仍回退）、answer-013 的
  sparse p3 证据 → **融合策略本身不足以修复，绑定约束是"融合深度 ×
  Agent 4-chunk 预算"**；下一步预留 sparse 槽位（V2.3c）或 V2.4 reranker。
- README V2.3/V2.3b 段完整记录：指标、四类归因、answer-013 证据链、结论与
  下一步选项；避免了"指标变差但不知道为什么"的叙事。
- CONTEXT.md 无需新增术语：hybrid/sparse/fusion 属实现概念，不是产品领域
  词；结论记录在 ADR/README。
- 受控产物：`experiment-v2.3-A-baseline.json`、`experiment-v2.3-hybrid.json`、
  `experiment-v2.3b-{equal_rrf,dense_priority,weighted_rrf}.json`、
  `experiment-v2.3-analysis.md`、`experiment-v2.3b-analysis.md`；raw 输出
  gitignore。

V2.3 全部 ticket resolved（01/02/03/04/05）。下一步 V2.3c 或 V2.4 由用户决策。
