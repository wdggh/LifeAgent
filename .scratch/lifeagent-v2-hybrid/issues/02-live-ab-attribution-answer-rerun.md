# 02: Live A/B + 归因分类 + 13 条 answer 重跑

**What to build:** 在 v2.0.2 基线上跑 A=dense-only（应与基线一致）与
B=dense+sparse+RRF（expansion 关闭），产出 `experiment-v2.3-hybrid.json`；
按预注册标准判定，并对每个 case 记录四类归因：dense_hit_only /
sparse_new_recall / sparse_hit_but_fusion_missed / neither。重点观察
answer-013 对应的购买记录 p2/p3 是否被 sparse 新召回。随后重跑 13 条
answer（answer-013 为达标项、answer-010 仅跟踪）。

**Blocked by:** 01

**Status:** resolved

- [ ] A 与 baseline-v2.0.2 逐项一致（expansion/sparse 均关闭）
- [ ] B 产出 `experiment-v2.3-hybrid.json`（raw gitignore）
- [ ] 标准 (i)–(iv) 逐条判定；四类归因逐 case 记录（含 answer-013 的证据链）
- [ ] 13 条 answer transcripts 重跑；answer-013 / answer-010 分别记录
- [ ] 结论与未达标项写入 README/分析报告；如失败，同样先归因再决定下一步

## Comments

## Answer

实验完成，结论 **未通过**（4 条标准：1 条通过、3 条失败）：

- A（dense-only，工具路径，--reset）与 baseline-v2.0.2 逐项完全一致。
- B（dense top8 + sparse top8，等权 RRF + dense 优先 tie-break）：
  overall chunk MRR 0.8373→0.7733、NDCG 0.8061→0.7516、R5 0.85→0.83；
  hard-10 MRR 0.5867→0.5667、NDCG 0.4974→0.4410；easy-40 MRR
  0.9000→0.8250（回退 0.075）。
- 标准判定：(i) FAIL；(ii) FAIL（easy 回退 0.075）；(iii) reg-001/002 gate
  PASS；(iv) answer-013 source=1 FAIL（仍 0/0/0）。
- 四类归因（hard-10）：9 条 `dense_hit_only`、1 条 `neither`（v2-039）、
  0 条 `sparse_new_recall`（case 级）、0 条 `sparse_hit_but_fusion_missed`。
- answer-013 深挖（直接通道检查）：dense 命中 purchase p1(rank1)/p2(rank8)；
  sparse 新增 purchase p3（七日退货，rank3）并提升 p2；但等权 RRF 把
  bike_warranty p1 推为 rank1，purchase p3 落到 rank6（超出 Agent 每轮 4
  chunk 预算），最终仍只引用保修凭证并用通用退货话术 → 0/0/0。
- 根因：异构通道等权 RRF 稀释强通道——两列表交错使 dense rank r 落到
  fused ≈2r，dense rank8 gold 掉出 top5，同时在两路出现的错误 chunk 被加权
  提升。V2.2 等权规则在"高度相关分支"下安全，在异构通道下不成立。
- 纪律执行：**没有立即修改稀疏引擎/分词/RRF 权重**。下一步建议（待用户决策）
  先做 V2.3b 预注册融合策略消融：dense-priority supplement vs 加权 RRF
  (2.0/1.0) vs 现等权，再决定是否进入 V2.4 reranker。
- Answer-level：13 条评分与 V2.2 完全一致（11/13、10/13、11/13），
  `reviews/answer_review_v2.2.json` 沿用；answer-013 仍是主要词面回归目标。
- 产物：`experiment-v2.3-A-baseline.json`、`experiment-v2.3-hybrid.json`、
  `experiment-v2.3-analysis.md`；raw 输出 gitignore；README 增加 V2.3 段。
