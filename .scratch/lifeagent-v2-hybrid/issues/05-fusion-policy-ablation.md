# 05: 三臂融合策略消融 + 13 条 answer 重跑 + 分析

**What to build:** 在同一份 v2.0.2 基线数据、同一 dense、同一 BM25、同一候选
数（各 8）上跑三臂：A=equal_rrf（控制，可对照 experiment-v2.3-hybrid）、
B=dense_priority、C=weighted_rrf 2:1，各产出受控报告；按预注册标准判定
(i)–(iv)（hard ≥+0.03 / easy ≤0.01 / gate / answer-013 source=1），并做
per-arm 归因（dense_hit_only / sparse_new_recall_kept /
sparse_new_recall_dropped / sparse_hit_but_fusion_missed / neither）。
answer-013 作为诊断 case：记录 sparse p3 是否保留在 top-4、最终回答是否引用
购买记录。对表现最优（或全部）臂重跑 13 条 answer 并出评分草案。

**Blocked by:** 04

**Status:** resolved

- [ ] 三臂 live 运行，报告命名 `experiment-v2.3b-{equal_rrf,dense_priority,weighted_rrf}.json`（raw gitignore）
- [ ] 预注册标准逐臂判定；三臂归因表写入分析报告
- [ ] answer-013 诊断链（sparse p3 → 融合排名 → Agent top-4 → source）
- [ ] 13 条 answer 重跑并对最优臂出评分草案（如评分变化需用户确认）
- [ ] 结论（赢家/未达标项/是否进入 V2.4）写入 README/报告

## Comments

## Answer

三臂消融完成，结论：**融合策略本身不足以修复瓶颈**。

- 指标（chunk）：A 等权 hard MRR 0.5667 / NDCG 0.4410（easy −0.075）；
  B dense-priority 与 baseline **完全一致**（0 变化，是唯一无 easy 回退的臂）；
  C 加权 2:1 hard MRR 0.5833 / NDCG 0.4778（easy −0.0667）。
- 预注册判定：三臂 (i) 全部 FAIL；(ii) 仅 B 通过；(iii) gate 全 PASS；
  (iv) answer-013 三臂均 0/0/0 FAIL。
- 归因（hard-10，三臂一致）：9 `dense_hit_only`、1 `neither`、0
  `sparse_new_recall_kept/dropped`。
- answer-013 诊断：sparse 的 purchase p3（七日退货）在 equal/weighted 下落到
  rank6/9，dense-priority 下更落到位 9——**任何策略都无法进入 Agent top-4**；
  dense-priority 只是"不破坏"，无法把 lexical 证据带进预算内。
- answer-level（dense-priority 臂）：13 条评分与 V2.2 一致（11/13、10/13、
  11/13），answer-013 仍 0/0/0 → 沿用 `answer_review_v2.2.json`。
- 结论：瓶颈是"融合深度 × Agent 4-chunk 预算"的交互，而不是融合范式本身。
  下一步（待用户决策）：V2.3c 预留 sparse 槽位（dense top3 + sparse 补 1）
  或 V2.4 reranker（宽候选 + 精排到预算内）；两者都需先预注册。
- 产物：`experiment-v2.3b-{equal_rrf,dense_priority,weighted_rrf}.json`、
  `experiment-v2.3b-analysis.md`；raw 输出 gitignore；README 增加 V2.3b 段。
