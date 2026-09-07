# 03: 会话管理

**What to build:** 用户能创建、查看、列出和删除自己的 Conversation；会话归属由后端强制校验。

**Blocked by:** 02（认证：注册 / 登录 / 当前用户）

**Status:** resolved

- [ ] 创建 Conversation（title 可选）成功
- [ ] 列表只返回当前用户自己的会话，新的在前
- [ ] 会话详情返回其 Message（此阶段为空列表）
- [ ] 删除会话会连同其 Message 一起删除
- [ ] 访问或删除其他用户的会话返回 404（不泄露存在性）
- [ ] 未认证请求返回 401

## Answer

已实现并验证（commit 见下方）：会话管理四端点 + 消息模型 + 归属隔离。

- `POST /conversations`（201，title 可选）、`GET /conversations`（本人列表，新在前）、`GET /conversations/{id}`（详情含 messages）、`DELETE /conversations/{id}`（204，DB 级联删消息）
- conversations/messages 模型 + Alembic 0002 迁移（messages.role 仅 user/assistant CHECK；agent_run_id 为占位列，FK 待 ticket 08）
- 归属：所有查询 `WHERE user_id=当前用户`；跨用户访问/删除返回 404 CONVERSATION_NOT_FOUND；未认证 401
- 测试：7 个会话用例 + 全套 28 passed；真实服务冒烟通过
