# 02: Live A/B（双路最小版）与 13 条 answer 重跑

**What to build:** 在 v2.0.2 基线上跑两次实验：A=扩展关闭（应与基线一致）；
B=原查询 + 1 条改写、等权 RRF + original 同分优先。按预先固定标准判定：hard-10
chunk MRR/NDCG 提升 ≥0.03；easy-40 回退 ≤0.01；reg-001/002 gate 不回归；
answer-013（自行车单轮用例）source_correctness=1。`answer-010` 作为歧义/多轮
用例单独跟踪，不作为通过标准。13 条 answer 对话重跑并对比既有 review。
多变体与权重消融（1.0 vs 1.5）明确留到 V2.2b/V2.3，不在本实验内。

**Blocked by:** 01

**Status:** resolved

- [ ] A 与 baseline-v2.0.2 逐项一致（工具路径、扩展关闭）
- [ ] B 产出 `experiment-v2.2-query-expansion.json`（raw gitignore）
- [ ] 成功标准 (i)–(iv) 逐条判定；融合规则为预注册的等权 RRF + original 同分优先，不事后调参
- [ ] 13 条 answer transcripts 重跑；answer-013 与 answer-010 分别记录
- [ ] 结论（通过/未通过/部分通过 + 未达标项）写入 README/报告

## Comments

## Answer

实验完成，结论：**4 条预注册标准中 3 条通过、1 条失败，且 (i) 是边界性通过**：

- A（扩展关闭，工具路径，--reset）与 baseline-v2.0.2 逐项完全一致；
- B（原查询 + 1 改写，等权 RRF + original 同分优先）：
  overall chunk MRR 0.8373→0.8433、NDCG 0.8061→0.8097；hard-10 MRR
  0.5867→0.6167（**+0.0300，正好达标**）、NDCG 0.4974→0.5124；
  easy-40 无回退；reg-001/002 gate PASS；`answer-013` source=1 **FAIL**（0/0/0）。
- 按约定的失败分类（hard-10）：7 条 `no_new_recall`、2 条
  `original_sufficient`、1 条 `rank_only_gain`（cd-003）；0 条
  `new_recall_but_fusion_missed`、0 条 `expansion_error`。**整个 +0.03 来自
  cd-003 一个 rank-only 重排**，expansion 在 hard 子集没有带来任何新召回，
  因此这次"通过"是脆弱的，不能证明 expansion 的预期机制成立。
- answer-level：13 条草案 `reviews/answer_review_v2.2.draft.json`
  （11/13 source、10/13 completeness、11/13 no_hallucination）；answer-013
  检索到保修凭证而非购买记录、未答七日无理由 → 0/0/0；answer-010 保持冻结
  歧义用例单独跟踪。
- 产物：`experiment-v2.2-A-baseline.json`、`experiment-v2.2-query-expansion.json`
  （controlled）、`experiment-v2.2-analysis.md`（逐 case 分类）；raw 输出
  gitignore；README 增加实验段。
- 纪律执行：**没有因为 B 结果而修改 expansion prompt**。下一步二选一（待用户
  决策）：V2.2b 互补型变体（分解/文档词表/精确术语锚点）或 V2.3 引入
  sparse/BM25 通道进入同一融合；两者都必须先预注册再跑。
