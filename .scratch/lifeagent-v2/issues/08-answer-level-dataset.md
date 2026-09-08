# 08: Answer-level 评测数据集

**What to build:** `tests/evaluation/dataset/answer_cases.jsonl`（12 条：从 30 条
retrieval query 派生 10 条 + 2 条 `not_in_kb`），字段含 question/category/
expected_sources/answer_requirements；人工三轴 0/1 判定表（source_correctness /
completeness / no_hallucination）；说明不参与 retrieval 指标、不上 LLM-as-Judge，
answer 状态 READY/PARTIAL 不阻塞 retrieval baseline 发布。

**Blocked by:** 02（dataset 与词表）

**Status:** resolved

- [ ] answer_cases.jsonl 12 条：10 条与 retrieval query 对应 + 2 条 not_in_kb
- [ ] not_in_kb 用例要求"明确说资料中没有找到"，不得给日期/金额
- [ ] 三轴 0/1 判定说明与人工审查清单（report 模板字段）
- [ ] schema 校验：category 合法、expected_sources 引用 manifest、answer_requirements 非空
- [ ] README 说明 answer-level 独立于 retrieval 指标

## Comments

## Answer

已实现并验证（fast，无外部依赖）：

- `answer_cases.jsonl`（12 条：10 派生 + 2 not_in_kb）此前随 V2.0-02 落地并由
  dataset schema 校验器覆盖；本 ticket 补齐人工审查基础设施：
- `tests/evaluation/reviews/answer_review.py`：三轴 0/1 校验
  （source_correctness / completeness / no_hallucination）、`READY`/`PARTIAL`
  状态判定、per-axis pass/fail/pending 汇总、template/check 两个 CLI 子命令；
  `not_in_kb` 的 source_correctness 语义为"不得引用编造来源且须明确说未找到"。
- `tests/evaluation/reviews/answer_review_template.json`：已生成并校验
  （12 条 pending，PARTIAL 是合法中间态）。
- `tests/evaluation/reviews/test_answer_review.py`：8 个 fast 用例全绿
  （id 齐全/未知/重复、非法分值/字段、allow-pending、READY vs PARTIAL、
  汇总计数、真实 dataset 可解析）。
- `tests/evaluation/README.md`：answer-level 审查流程、轴定义与
  "Retrieval READY + Answer PARTIAL 可发布"说明。

验收清单全部满足；answer-level 不参与 retrieval 指标、不上 LLM-as-Judge。
下一步 V2.0-05 Real ingestion & isolated evaluation harness。
