# 01: Query Expansion + 加权 RRF 端到端接入 search_knowledge

**What to build:** 开启配置后，`search_knowledge` 用"原查询（永远存在）+
1 条变体"并行检索，按等权 RRF（k=60，original 同分优先）融合去重后返回；
变体生成失败时只用原查询（fail-open）。变体生成器并入 V2.1 的两个缺陷修复：
仅在显式相对日期词存在时解析日期、必须保留实体/编号/数字/判别性名词，
且生成确定可复现。完成即可验证：用脚本化假 LLM 与记录型假检索器，
可以看到实际发起的分支、融合顺序、trace 字段，以及关闭配置时与
v2.0.2 基线完全一致。

**Blocked by:** None（V2.1 已结案，默认关闭）

**Status:** ready-for-agent

- [ ] 变体生成器：缺陷修复（显式日期才解析、实体/术语保护、确定性）+ 2 条变体 + 单行 ≤120 字符 + fail-open
- [ ] 原查询恒在；变体只做补充，任何失败都不阻断检索
- [ ] 并行检索（每路候选 8）→ 去重 → 等权 RRF（k=60，original 同分优先）→ 截断（评测 10 / Agent 预算内）
- [ ] 配置项（enabled/variants=1/candidate_k/rrf_k/timeout/max_tokens；weight 字段保留默认 1.0 供后续阶段）+ .env.example
- [ ] trace：query_original / query_variants / expansion_fallback(_reason) / expansion_duration_ms / per_variant_hits / fusion_candidates / fusion_top / rrf_k / original_weight
- [ ] `retrieval_count` 与每轮 chunk 预算语义不变；关闭配置时与基线一致
- [ ] 单测：双路同分反例（原查询 rank1 正确 vs 改写 rank1 错误 → 同分 → original 胜出）、去重、截断、fail-open、禁用等价基线

## Comments
