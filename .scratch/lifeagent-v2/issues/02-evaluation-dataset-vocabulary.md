# 02: 评测数据集与受控词表

**What to build:** `tests/evaluation/dataset/queries.jsonl`（30 条 retrieval query，
含 `reg-001/reg-002`）、README（8 类受控词表中英文说明 + 隐私红线），以及 schema
校验器（fast 模式）：唯一 id、词表合法、question 边界、document 存在于 manifest、
pages 在合法范围且有 anchor、禁止 chunk/id 级字段（`additionalProperties: false`）。
分布：simple_fact 6、semantic_rewrite 5、exact_term 5、numeric_date 4、clause 5、
cross_paragraph 3、clause_specific 2。全部单文档 gold（document + pages[]）。

**Blocked by:** 01（合成语料与 manifest）

**Status:** claimed

- [ ] queries.jsonl 共 30 条，类别分布符合 spec
- [ ] reg-001/reg-002：`reg-` 前缀 + clause_specific，分别指向 rental_contract_01
      p8（第四条）与 p9（第五条）；query 文本不泄露"第四条/第五条"
- [ ] 单文档 gold：`gold.document` + `gold.pages[]`；dataset 内无 chunk_id/document_id
- [ ] schema 校验器（fast）全绿：结构、词表、slug、页界、唯一性
- [ ] README：8 类词表中英文说明；not_in_kb 不参与 retrieval 指标；隐私红线说明
- [ ] answer_elements 仅作辅助标注，指标实现不读取它

## Comments
