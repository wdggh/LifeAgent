# 08: Answer-level 评测数据集

**What to build:** `tests/evaluation/dataset/answer_cases.jsonl`（12 条：从 30 条
retrieval query 派生 10 条 + 2 条 `not_in_kb`），字段含 question/category/
expected_sources/answer_requirements；人工三轴 0/1 判定表（source_correctness /
completeness / no_hallucination）；说明不参与 retrieval 指标、不上 LLM-as-Judge，
answer 状态 READY/PARTIAL 不阻塞 retrieval baseline 发布。

**Blocked by:** 02（dataset 与词表）

**Status:** claimed

- [ ] answer_cases.jsonl 12 条：10 条与 retrieval query 对应 + 2 条 not_in_kb
- [ ] not_in_kb 用例要求"明确说资料中没有找到"，不得给日期/金额
- [ ] 三轴 0/1 判定说明与人工审查清单（report 模板字段）
- [ ] schema 校验：category 合法、expected_sources 引用 manifest、answer_requirements 非空
- [ ] README 说明 answer-level 独立于 retrieval 指标

## Comments
