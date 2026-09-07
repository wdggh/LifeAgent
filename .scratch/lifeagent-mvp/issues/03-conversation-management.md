# 03: 会话管理

**What to build:** 用户能创建、查看、列出和删除自己的 Conversation；会话归属由后端强制校验。

**Blocked by:** 02（认证：注册 / 登录 / 当前用户）

**Status:** ready-for-agent

- [ ] 创建 Conversation（title 可选）成功
- [ ] 列表只返回当前用户自己的会话，新的在前
- [ ] 会话详情返回其 Message（此阶段为空列表）
- [ ] 删除会话会连同其 Message 一起删除
- [ ] 访问或删除其他用户的会话返回 404（不泄露存在性）
- [ ] 未认证请求返回 401
