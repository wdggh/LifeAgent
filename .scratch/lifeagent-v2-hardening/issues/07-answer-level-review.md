# 07: Answer-level 12 条人工审查

**What to build:** 使用 V2.0-08 的 review 工具补完 12 条 answer_cases 人工
三轴 0/1 审查（source_correctness/completeness/no_hallucination，含 2 条
not_in_kb），状态 READY 或 PARTIAL 写入 v2.0.1 报告；不影响 retrieval baseline
发布。审查基于真实 Agent 对话（qwen/deepseek + 真实语料）逐条填模板。

**Blocked by:** None（可与 01–06 并行）

**Status:** resolved

- [ ] 12 条全部或部分完成人工评分（0/1），模板文件通过 check
- [ ] not_in_kb 两条按"明确说未找到、不得编造"判定
- [ ] 汇总 READY/PARTIAL 写入报告/README

## Comments

## Answer

已完成（人工确认版）：

- 12 条 answer_cases 适配到 synthetic-personal-kb-v2（`dataset/answer_cases.jsonl`），
  v2 validator 校验通过（12 条含 2 条 not_in_kb）。
- 用真实 Agent（qwen-max + v2 语料）跑完 12 条对话：
  `python -m tests.evaluation.reviews.run_answer_transcripts --dataset
  synthetic-personal-kb-v2`；原始 transcript
  `reports/answer-transcripts-v2.raw.json`（gitignore）。
- 人工三轴 0/1 评分（用户确认，照草案通过，不调整为全 1）：
  - source_correctness 11/12；completeness 10/12；
    no_hallucination 11/12；
  - 正式文件 `tests/evaluation/reviews/answer_review_v2.json`
    （review_status=READY，reviewer=user 2026-09-10）；
  - 已知失败样本（保留为 V2.x 回归锚点）：
    - `answer-007`：检索正确（rental p4），但回答漏掉违约后果 →
      completeness=0；
    - `answer-010`：应命中自行车购买记录 p2/p3，实际检索到净化器保修凭证，
      未给出 24 个月/七日无理由，并用通用话术补造退货规则 →
      source 0 / completeness 0 / no_hallucination 0。
- `baseline-v2.0.1.json` 的 answer_level 更新为 READY（含 12 条汇总与失败清单）；
  README v2.0.1 段同步。
- 原则确认：评测用于暴露问题而不是凑满分；007/010 是 V2.1+ 优化最直接的
  端到端回归样本。

至此 V2.0.1（Benchmark Hardening）01–07 全部 resolved。
