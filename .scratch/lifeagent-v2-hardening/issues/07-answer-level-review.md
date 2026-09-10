# 07: Answer-level 12 条人工审查

**What to build:** 使用 V2.0-08 的 review 工具补完 12 条 answer_cases 人工
三轴 0/1 审查（source_correctness/completeness/no_hallucination，含 2 条
not_in_kb），状态 READY 或 PARTIAL 写入 v2.0.1 报告；不影响 retrieval baseline
发布。审查基于真实 Agent 对话（qwen/deepseek + 真实语料）逐条填模板。

**Blocked by:** None（可与 01–06 并行）

**Status:** claimed

- [ ] 12 条全部或部分完成人工评分（0/1），模板文件通过 check
- [ ] not_in_kb 两条按"明确说未找到、不得编造"判定
- [ ] 汇总 READY/PARTIAL 写入报告/README

## Comments
