# 03: 每轮最多注入 4 chunks（Spec 1）

**What to build:** 检索结果每轮/每次工具返回硬上限 4 条，代码强制，不依赖 prompt。

**Blocked by:** None

**Status:** resolved

- [ ] search_knowledge 请求 top_k>4 时实际返回 ≤4
- [ ] 工具结果文本条数与 result_count ≤4
- [ ] 单元测试覆盖 top_k=10 被截断

## Answer

已修复：search_knowledge 硬性截断每次返回 ≤4 chunks（MAX_CHUNKS_PER_ROUND），不依赖 prompt。详见 report.md。
