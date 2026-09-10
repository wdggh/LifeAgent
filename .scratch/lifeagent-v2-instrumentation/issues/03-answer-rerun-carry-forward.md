# 03: Answer-level 重跑与评分沿用

**What to build:** 在修订后的 corpus 上重跑 12 条 answer transcripts；与现有
评分逐条对比：输出未变则沿用 11/10/11 并把 review 文件与
baseline-v2.0.2.answer_level 指向 v2.0.2；有变化的部分提交用户确认后再定分。

**Blocked by:** 02

**Status:** claimed

- [ ] 12 条 transcripts 重跑（raw 输出 gitignore）
- [ ] 逐条对比，未变则 carry-forward；变化处列出差异待用户确认
- [ ] review/基线报告的 answer_level 指向 v2.0.2

## Comments
