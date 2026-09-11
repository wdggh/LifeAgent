# 03: ADR/README/词表同步与 V2.3c 收口

**What to build:** 校验 ADR-0012（预留槽位策略与预注册标准）；README 记录
V2.3c 结果与对照基线；CONTEXT.md 判断是否新增术语（预期不加并记录理由）；
resolve 本 feature 全部 ticket，并给出 V2.4 reranker 的衔接判断。

**Blocked by:** 02

**Status:** resolved

- [ ] ADR-0012 与实现一致（L−1 dense + 1 sparse-only、退化路径、trace）
- [ ] README V2.3c 段：A/B 结果、标准判定、answer-013 链路、结论
- [ ] CONTEXT.md 决策记录（加或明确不加 + 理由）
- [ ] 全部 ticket resolved；写明是否进入 V2.4

## Comments

## Answer

V2.3c 收口：

- ADR-0012 增加 2026-09-11 更新段：A==baseline；B 的 MRR@5/NDCG@5/R@5 与
  hard/easy 不变、Recall@10 −0.0333（保留槽顶掉 dense rank9/10 gold）；
  criterion (iv) PASS（answer-013 source 0→1，p3 经保留槽进入 Agent top-4）；
  失败转移到 answer synthesis（模型未引用已拿到的七日退货证据）；
  同时暴露"top-5 指标看不到最后槽位干预"的测量缺口 → 下一步先补
  agent-context 指标再做 V2.4 决策。
- README V2.3c 段与 `experiment-v2.3c-analysis.md` 已记录指标、诊断链、
  reserved-slot 使用统计（49/50、1 fallback、1 gold hit）与结论。
- CONTEXT.md 无需新增术语：reserved slot / agent-context metric 属评测与
  检索实现概念，不是产品领域词；结论记录在 ADR/README。
- 受控产物：`experiment-v2.3c-A-baseline.json`、
  `experiment-v2.3c-reserved-slot.json`、`experiment-v2.3c-analysis.md`；
  评分草案 `reviews/answer_review_v2.3c.draft.json`（12/13、10/13、11/13，
  待用户确认）；raw 输出 gitignore。

V2.3c 全部 ticket resolved（01/02/03）。下一步由用户决策：V2.3d
agent-context 指标 + answer-synthesis 诊断，或 V2.4 reranker。
