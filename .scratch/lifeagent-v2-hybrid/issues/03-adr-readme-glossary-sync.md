# 03: ADR/README/词表同步与 V2.3 收口

**What to build:** 校验 ADR-0011（混合检索 + RRF + 索引生命周期）；README
记录 V2.3 A/B/归因结论与对照基线；CONTEXT.md 判断是否新增术语
（"知识库"已有，"StoredChunk"已有；预期不加并记录理由）；resolve 本 feature
全部 ticket，并说明 V2.4（cross-encoder reranker）的衔接。

**Blocked by:** 05（V2.3b 结束后统一收口，覆盖 02 + V2.3b 的完整闭环）

**Status:** ready-for-agent

- [ ] ADR-0011 与实现一致（引擎/参数/失效机制/tie-break/fail-open）
- [ ] README V2.3 段：A/B 结果、四类归因、answer-013 证据、结论
- [ ] CONTEXT.md 决策记录（加或明确不加 + 理由）
- [ ] 全部 ticket resolved，frontier 清空

## Comments
