# 01: Query Expansion + 加权 RRF 端到端接入 search_knowledge

**What to build:** 开启配置后，`search_knowledge` 用"原查询（永远存在）+
1 条变体"并行检索，按等权 RRF（k=60，original 同分优先）融合去重后返回；
变体生成失败时只用原查询（fail-open）。变体生成器并入 V2.1 的两个缺陷修复：
仅在显式相对日期词存在时解析日期、必须保留实体/编号/数字/判别性名词，
且生成确定可复现。完成即可验证：用脚本化假 LLM 与记录型假检索器，
可以看到实际发起的分支、融合顺序、trace 字段，以及关闭配置时与
v2.0.2 基线完全一致。

**Blocked by:** None（V2.1 已结案，默认关闭）

**Status:** resolved

- [ ] 变体生成器：缺陷修复（显式日期才解析、实体/术语保护、确定性）+ 2 条变体 + 单行 ≤120 字符 + fail-open
- [ ] 原查询恒在；变体只做补充，任何失败都不阻断检索
- [ ] 并行检索（每路候选 8）→ 去重 → 等权 RRF（k=60，original 同分优先）→ 截断（评测 10 / Agent 预算内）
- [ ] 配置项（enabled/variants=1/candidate_k/rrf_k/timeout/max_tokens；weight 字段保留默认 1.0 供后续阶段）+ .env.example
- [ ] trace：query_original / query_variants / expansion_fallback(_reason) / expansion_duration_ms / per_variant_hits / fusion_candidates / fusion_top / rrf_k / original_weight
- [ ] `retrieval_count` 与每轮 chunk 预算语义不变；关闭配置时与基线一致
- [ ] 单测：双路同分反例（原查询 rank1 正确 vs 改写 rank1 错误 → 同分 → original 胜出）、去重、截断、fail-open、禁用等价基线

## Comments

## Answer

已实现并验证：

- `app/rag/query/expansion.py`：QueryExpander 生成 1 条补充查询；两个 V2.1
  缺陷已修：仅当问题包含显式相对日期词时才注入当前日期；变体必须保留编号/
  数字等受保护 token（丢失则丢弃，reason=entity_lost）。temperature=0、
  ≤120 字符单行、超时/异常/空输出一律 fail-open 返回零变体。
- `app/rag/retrieval/fusion.py`：等权 RRF（k=60）+ **original 优先级
  tie-break**（同分时原查询分支胜出）；按 chunk_id 去重、跨分支累加分数、
  支持 limit 截断。
- `search_knowledge`：扩展开启时并行检索（原查询 + 变体，每路候选 8），
  融合后按 Tool 预算截断（评测 10 / Agent ≤4）；metadata 记录
  query_original / query_variants / expansion_fallback(_reason) /
  expansion_duration_ms / per_variant_hits / fusion_candidates / fusion_top /
  rrf_k / original_weight，经 Agent 合并进 `agent_runs.steps`。
- 配置：query_expansion_enabled=false（默认关闭，实验通过前不启用）、
  variants=1、candidate_k=8、rrf_k=60、original_weight=1.0、timeout=8、
  max_tokens=200（config + .env.example）；V2.1 rewrite 开关保留但默认关闭。
- `retrieval_count`、Tool 签名与预算语义不变；关闭配置时行为与 v2.0.2 基线一致。
- 测试：`tests/test_query_expansion.py` 10 个用例全绿（无相对日期不注入日期、
  显式日期才解析、受保护 token 丢失丢弃、error/empty/timeout fail-open、
  RRF 同分 original 胜出、跨分支去重累加、Tool 双路/trace、失败单路、
  禁用等价基线、预算截断）；全量 pytest 通过。

验收清单满足。下一步 V2.2-02 Live A/B（关闭 vs 双路）与 13 条 answer 重跑。
