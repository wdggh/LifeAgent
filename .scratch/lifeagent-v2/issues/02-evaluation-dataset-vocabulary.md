# 02: 评测数据集与受控词表

**What to build:** `tests/evaluation/dataset/queries.jsonl`（30 条 retrieval query，
含 `reg-001/reg-002`）、README（8 类受控词表中英文说明 + 隐私红线），以及 schema
校验器（fast 模式）：唯一 id、词表合法、question 边界、document 存在于 manifest、
pages 在合法范围且有 anchor、禁止 chunk/id 级字段（`additionalProperties: false`）。
分布：simple_fact 6、semantic_rewrite 5、exact_term 5、numeric_date 4、clause 5、
cross_paragraph 3、clause_specific 2。全部单文档 gold（document + pages[]）。

**Blocked by:** 01（合成语料与 manifest）

**Status:** resolved

- [ ] queries.jsonl 共 30 条，类别分布符合 spec
- [ ] reg-001/reg-002：`reg-` 前缀 + clause_specific，分别指向 rental_contract_01
      p8（第四条）与 p9（第五条）；query 文本不泄露"第四条/第五条"
- [ ] 单文档 gold：`gold.document` + `gold.pages[]`；dataset 内无 chunk_id/document_id
- [ ] schema 校验器（fast）全绿：结构、词表、slug、页界、唯一性
- [ ] README：8 类词表中英文说明；not_in_kb 不参与 retrieval 指标；隐私红线说明
- [ ] answer_elements 仅作辅助标注，指标实现不读取它

## Comments

## Answer

已实现并验证：

- `tests/evaluation/dataset/queries.jsonl`：30 条 retrieval query，类别分布与 spec
  一致（simple_fact 6 / semantic_rewrite 5 / exact_term 5 / numeric_date 4 /
  clause 5 / cross_paragraph 3 / clause_specific 2）；全部单文档 gold
  （document + pages[]），不存 chunk_id。
- reg-001/reg-002 按修订设计落地：分别指向 rental_contract_01 p8（第四条）与
  p9（第五条），query 文本不泄露条款号，使 MRR/Recall 能观察语义匹配条款是否
  排在近似干扰项之前（校验器对 clause_specific 做"不得出现第 N 条"断言）。
- `tests/evaluation/dataset/answer_cases.jsonl`：12 条 answer-level 用例
  （10 条派生自 retrieval query + 2 条 not_in_kb，不参与 retrieval 指标）。
- `tests/evaluation/README.md`：8 类受控词表中英文对照、隐私红线、schema 语义、
  fast/live 说明与 answer-level 三轴 0/1 判定。
- `tests/evaluation/dataset/validate_dataset.py`（fast schema 校验器）全绿：
  结构/词表/slug/页界/分布/回归放置/条款号泄露检查，输出
  "30 retrieval queries, 12 answer cases, all checks passed"。

验收清单全部满足。下一步 V2.0-08（answer-level 人工审查清单/报告模板）与
V2.0-03（gold mapping + StoredChunk + Repository 接口）。
