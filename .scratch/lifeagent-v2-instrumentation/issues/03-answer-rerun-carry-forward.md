# 03: Answer-level 重跑与评分沿用

**What to build:** 在修订后的 corpus 上重跑 12 条 answer transcripts；与现有
评分逐条对比：输出未变则沿用 11/10/11 并把 review 文件与
baseline-v2.0.2.answer_level 指向 v2.0.2；有变化的部分提交用户确认后再定分。

**Blocked by:** 02

**Status:** resolved

- [ ] 12 条 transcripts 重跑（raw 输出 gitignore）
- [ ] 逐条对比，未变则 carry-forward；变化处列出差异待用户确认
- [ ] review/基线报告的 answer_level 指向 v2.0.2

## Comments

## Answer

已完成：

- 在修订后 corpus 上用 qwen-max 重跑 12 条 answer transcripts
  （`reports/answer-transcripts-v2.0.2.raw.json`，gitignore）。
- 逐条与 v2.0.1 确认版对比：11 条评分沿用；唯一变化为 `answer-005`
  （新回答未说明线上/邮寄提交方式，全文无"线上/渠道/邮寄/上传/平台"字样），
  经用户确认保留 completeness=0。
- 正式 review：`reviews/answer_review_v2.0.2.json`（READY，
  reviewer=user 2026-09-11）：source 11/12、completeness 9/12、
  no_hallucination 11/12；失败样本 answer-005 / answer-007 / answer-010。
- `baseline-v2.0.2.json` answer_level 更新为 READY（含汇总、失败清单与
  carry-forward 说明）；README v2.0.2 段同步。

至此 V2.0.2（measurement fixture revision）01–03 全部 resolved，
ACTIVE baseline = v2.0.2，可以开始在稳定尺子上做 V2.1 Query Rewrite。
