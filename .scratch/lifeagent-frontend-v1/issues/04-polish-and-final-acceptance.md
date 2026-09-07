# 04: 打磨与最终验收

**What to build:** V1 becomes deliverable: empty, loading, and error states are polished; the full chain is accepted through a human walkthrough against the real backend; and known limitations plus follow-up candidates are recorded.

**Blocked by:** 02（我的文档）、03（会话 + Chat）

**Status:** claimed

- [ ] Empty, loading, and error states are clear for no Documents, no Conversations, draft input, and first-use
- [ ] Full-chain walkthrough passes: register → login → upload → completed → ask a question → Answer with Sources → refresh and resume → log out → log back in
- [ ] Error paths are verified: expired session, service unavailable (chat and upload), network loss, oversized/unsupported files
- [ ] UI copy matches the glossary (对话 / 文档 / 消息 / 来源 / 保修凭证) everywhere visible
- [ ] The project builds (`npm run build`) and a fresh environment can start the frontend with the documented run steps
- [ ] Known limitations and follow-up candidates are recorded (automated tests, Markdown rendering, document pagination beyond 100, deployment CORS/Nginx decision, backend-side chat idempotency, persisted Sources/metadata for past assistant messages)

## Notes（进行中）

已完成：

- 空态/加载/错误态：Chat（新对话草稿、空对话、思考中、失败提示、历史恢复）、
  文档（空表、加载、列表错误+重试、上传队列逐行错误与失败提示）、
  侧栏对话列表（加载/空/错误+重试）。
- 术语审计：前端可见文案无「会话」，统一 对话/文档/消息/来源/保修凭证；
  代码注释中的「会话」已改为 对话/登录态。
- 错误路径代码级覆盖：401 回登录带 redirect、503/网络错误友好文案、
  上传超限/类型不符客户端预校验与服务端映射。
- 构建与冒烟：`npm run build` 通过；/login /register /chat /chat/:id /documents
  与 /api/v1/health 均 200；无 token 401 错误体与后端一致。
- README 补充运行前提（后端 compose 与 provider key）、人工验收走查步骤、
  V1 已知限制与后续候选。

剩余（验收 seam，需真实账号与真实文件，无法在不写库的前提下由代理执行）：

- 浏览器全链路走查：注册 → 登录 → 上传（PDF/TXT/MD）→ 处理完成/失败重试 →
  提问 → 答案+来源 → 刷新恢复 → 登出 → 重登。
- 走查通过后本 ticket 置 resolved；期间如发现 UI 问题，直接在此 ticket 追加修复。
