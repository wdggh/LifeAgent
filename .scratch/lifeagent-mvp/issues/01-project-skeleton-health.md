# 01: 项目骨架与健康检查

**What to build:** API 服务能从环境配置启动并应答健康检查；请求带 request_id 贯穿日志；测试接缝（HTTP 黑盒 + Fake LLM/Embedding 注入 + 隔离测试库）就绪，后续所有切片都落在这一套约定上。

**Blocked by:** None（可立即开始）

**Status:** claimed

- [ ] `GET /api/v1/health` 返回 200 与 healthy 状态
- [ ] 应用配置全部来自环境变量（含默认值），与 .env.example 保持一致
- [ ] 每个响应携带 request_id，日志以结构化字段记录同一 id
- [ ] 测试套件可运行且不调用任何真实外部 API（LLM/Embedding 均为 Fake）
- [ ] 测试使用隔离的测试数据库，每个用例干净开始
- [ ] 未认证请求访问受保护路由返回 401（为后续切片立下约定）
