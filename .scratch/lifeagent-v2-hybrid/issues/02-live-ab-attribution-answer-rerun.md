# 02: Live A/B + 归因分类 + 13 条 answer 重跑

**What to build:** 在 v2.0.2 基线上跑 A=dense-only（应与基线一致）与
B=dense+sparse+RRF（expansion 关闭），产出 `experiment-v2.3-hybrid.json`；
按预注册标准判定，并对每个 case 记录四类归因：dense_hit_only /
sparse_new_recall / sparse_hit_but_fusion_missed / neither。重点观察
answer-013 对应的购买记录 p2/p3 是否被 sparse 新召回。随后重跑 13 条
answer（answer-013 为达标项、answer-010 仅跟踪）。

**Blocked by:** 01

**Status:** claimed

- [ ] A 与 baseline-v2.0.2 逐项一致（expansion/sparse 均关闭）
- [ ] B 产出 `experiment-v2.3-hybrid.json`（raw gitignore）
- [ ] 标准 (i)–(iv) 逐条判定；四类归因逐 case 记录（含 answer-013 的证据链）
- [ ] 13 条 answer transcripts 重跑；answer-013 / answer-010 分别记录
- [ ] 结论与未达标项写入 README/分析报告；如失败，同样先归因再决定下一步

## Comments
