# LLM access behind an LLMClient interface, DeepSeek via OpenAI-compatible API

Status: accepted

The Agent depends on an `LLMClient` interface, implemented by `DeepSeekClient` over DeepSeek's OpenAI-compatible chat API with tool calling. The agent loop is not wrapped in a framework, so providers can be swapped (DeepSeek → OpenAI → other compatible APIs) without touching Agent code.

Consequences: configuration lives in environment variables (`DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`); future providers implement the same interface.
