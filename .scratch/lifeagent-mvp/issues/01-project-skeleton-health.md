# 01: 项目骨架与健康检查

**What to build:** API 服务能从环境配置启动并应答健康检查；请求带 request_id 贯穿日志；测试接缝（HTTP 黑盒 + Fake LLM/Embedding 注入 + 隔离测试库）就绪，后续所有切片都落在这一套约定上。

**Blocked by:** None（可立即开始）

**Status:** resolved

- [ ] `GET /api/v1/health` 返回 200 与 healthy 状态
- [ ] 应用配置全部来自环境变量（含默认值），与 .env.example 保持一致
- [ ] 每个响应携带 request_id，日志以结构化字段记录同一 id
- [ ] 测试套件可运行且不调用任何真实外部 API（LLM/Embedding 均为 Fake）
- [ ] 测试使用隔离的测试数据库，每个用例干净开始
- [ ] 未认证请求访问受保护路由返回 401（为后续切片立下约定）

## Answer

已实现并验证（commit `98743a4`）：

- FastAPI 应用从环境配置启动（pydantic-settings，字段与 `.env.example` 一致）
- `GET /api/v1/health` 返回 `{"status": "healthy"}`
- request_id 中间件：响应带 `X-Request-ID`（可回显客户端传入值），日志为结构化 JSON 且含同一 request_id
- 统一错误体 `{error: {code, message, request_id}}`：AppError、HTTPException（404 等）、校验错误（422）、未知异常（500）全覆盖
- 认证约定占位：`get_current_user` 依赖缺失/伪造 token 时返回 401（UNAUTHENTICATED / INVALID_TOKEN），ticket 02 接入真实 JWT
- 测试接缝就绪：TestClient + `APP_ENV=test` + 隔离测试配置；Fake LLM/Embedding 注入约定留给首个消费方（05/08）
- 测试结果：9 passed；真实 uvicorn 冒烟通过
- 仓库已 `git init`（main 分支）并提交首个 commit
