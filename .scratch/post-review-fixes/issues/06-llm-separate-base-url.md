# 06: LLM 独立 base URL（Standards 1）

**What to build:** LLM 调用不再复用 embedding_base_url；配置语义分开。

**Blocked by:** None

**Status:** resolved

- [ ] 新增 LLM_BASE_URL 配置并写入 .env.example/compose
- [ ] DashScopeLLMClient 使用 llm_base_url
- [ ] 真实 qwen-max 冒烟仍通过

## Answer

已修复：新增 LLM_BASE_URL 配置（默认 DashScope 兼容端点），DashScopeLLMClient 不再复用 embedding_base_url；真实 qwen-max 冒烟通过。详见 report.md。
