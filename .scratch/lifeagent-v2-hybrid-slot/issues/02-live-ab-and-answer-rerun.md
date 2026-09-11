# 02: Live A/B + 13 条 answer 重跑 + 归因分析

**What to build:** A=dense-only（应等于 baseline-v2.0.2）；B=reserved_slot
（dense top(L−1) + 1 个 sparse-only 槽位，expansion/rewrite 关闭），产出
`experiment-v2.3c-reserved-slot.json`。按预注册标准判定 (i)–(iv)，并输出
诊断：reserved slot 使用次数/命中 gold 次数、answer-013 的 purchase p3 从
sparse rank → fused rank → Agent top-4 的完整链路。重跑 13 条 answer
（answer-013 为达标项，answer-010 仅跟踪），如评分变化需用户确认。

**Blocked by:** 01

**Status:** resolved

- [ ] A 与 baseline 逐项一致；B 产出受控报告（raw gitignore）
- [ ] 标准 (i)–(iv) 逐条判定；easy-40 回退 >0.01 必须判失败
- [ ] answer-013 诊断链完整记录（p3 是否进入 top-4、最终 source 是否购买记录）
- [ ] 13 条 answer 重跑（如评分变化提交用户确认；未变则沿用 v2.2 review）
- [ ] 结论与未达标项写入 README/分析报告；失败时先归因而非改参数

## Comments

- 2026-09-11 (post-hoc provenance fix, user review): the review artifacts had
  two defects that would have published a wrong provenance record. (1) A
  duplicated `transcripts` key in `answer_review_v2.1.json`,
  `answer_review_v2.2.json` and `answer_review_v2.3c.draft.json` — `json.load`
  kept the last value, so all three declared the v2.0.2 transcripts. (2) The
  `carry_forward` text was stale v2.0.2 wording ("only answer-005 changed and
  was confirmed at completeness=0") and contradicted the file's own
  `answer-005` score of 1. Fixed by renaming to `current_transcripts` /
  `baseline_transcripts` everywhere and rewriting `carry_forward` to the real
  chain (v2.0.2 review = 0 → v2.1 / v2.2 / v2.3c = 1). The checker now rejects
  duplicate JSON keys and requires `current_transcripts` on a scored review,
  with a regression test over the committed review files. Scores unchanged.

## Answer

实验完成，结论：**目标 criterion (iv) 通过，总体指标不通过**。

- A（dense-only）与 baseline-v2.0.2 逐项完全一致。
- B（reserved_slot = dense top(L−1) + 真 sparse-only 保留槽）：
  MRR@5 / NDCG@5 / Recall@5 / hard-10 / easy-40 MRR 全部与 baseline 相同；
  **Recall@10 0.9100 → 0.8767（−0.0333）**，因为保留槽顶掉了 dense 第
  9/10 位的 gold（这是该策略的位移成本，如实记录）。
- 标准判定：(i) FAIL（无 +0.03；且 R@10 回退）；(ii) PASS（预注册 easy MRR
  无回退）；(iii) gate PASS；**(iv) PASS：answer-013 source 0→1**。
- reserved slot 诊断：49/50 使用、1 次 fallback（编号跳过）、1 次命中 gold；
  真实 trace（answer-013）：sparse p3 rank3 → 保留槽 → Agent top-4 =
  [p1, bike_warranty, bike_warranty, p3]，最终答案引用 purchase_record_01
  并给出 24 个月保修。
- 失败已从检索层转移到 **answer synthesis**：模型拿到了 p3（七日退货）却
  仍称"未直接提及"并改用通用话术 → completeness/no_hallucination 仍 0。
- 测量发现：top-5 指标结构性看不到"最后一个消费槽位"的干预；需要预注册
  `agent_context_recall@4`（gold 是否进入 Agent 消费的 top-4）这样的
  agent 层指标，再做 V2.4 决策。
- answer 草案：`reviews/answer_review_v2.3c.draft.json`（source 12/13、
  completeness 10/13、no_hallucination 11/13），待用户确认。
- 产物：`experiment-v2.3c-A-baseline.json`、`experiment-v2.3c-reserved-slot.json`、
  `experiment-v2.3c-analysis.md`；raw 输出 gitignore；README 增加 V2.3c 段。
- 下一步建议（待用户决策）：先补 agent-context 指标 + answer-synthesis
  诊断（V2.3d），再决定 V2.4 reranker。
