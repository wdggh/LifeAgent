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

**Status:** claimed

- [ ] 三臂 live 运行，报告命名 `experiment-v2.3b-{equal_rrf,dense_priority,weighted_rrf}.json`（raw gitignore）
- [ ] 预注册标准逐臂判定；三臂归因表写入分析报告
- [ ] answer-013 诊断链（sparse p3 → 融合排名 → Agent top-4 → source）
- [ ] 13 条 answer 重跑并对最优臂出评分草案（如评分变化需用户确认）
- [ ] 结论（赢家/未达标项/是否进入 V2.4）写入 README/报告

## Comments
