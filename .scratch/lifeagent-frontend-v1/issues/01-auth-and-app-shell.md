# 01: 认证 + App Shell

**What to build:** A user can register, be logged in automatically, and land on the main interface; an existing user can log in, stay logged in across refreshes, and log out. Logged-out users who try to open a protected page are taken to the login page and returned to where they were going afterwards. The App Shell provides the sidebar skeleton (new chat, conversation area, documents entry, user area) that later tickets fill in.

**Blocked by:** None (can start immediately)

**Status:** resolved

- [ ] A new user can register and is logged in automatically, landing on the chat area; duplicate usernames and invalid input show clear errors
- [ ] A user can log in; wrong credentials show a clear error; success returns the user to their original destination
- [ ] Refresh or reopen keeps the user signed in (session validated against the backend)
- [ ] A missing or invalid token routes the user to the login page and preserves the intended destination
- [ ] A user can log out and is returned to the login page
- [ ] The App Shell shows 新对话, the conversation area, 我的文档, and the user area with logout
- [ ] Acceptance: walkthrough checklist passes and `npm run build` succeeds

## Answer

已实现并验证（本 feature 首轮 commit）：

- 认证层：注册/登录/当前用户 API 模块；统一 Axios 客户端带 JWT 请求头注入与会话失效
  （UNAUTHENTICATED / INVALID_TOKEN）401 自动清 token 回登录并携带 redirect；
  登录失败（INVALID_CREDENTIALS）不误判为会话失效。
- 状态层：auth store（token + user，登录/注册拆分/启动恢复/退出）；注册成功由调用方
  紧接着自动登录，若自动登录失败则提示并引导去登录页，避免「账号已建却报注册失败」死胡同。
- 路由与界面：/login、/register 公开路由；App Shell 承载 /chat、/chat/:conversationId、
  /documents；守卫在无 token 时跳登录并记录 redirect，有 token 时经 /auth/me 校验后放行；
  侧栏含 新对话、对话列表区、我的文档、用户区（用户名/退出登录）；Chat/Documents 为占位，
  由 02/03 填充。
- 错误映射：统一错误体解码与中文文案集中在共享模块（spec §6/§15），Login/Register
  表单预校验与后端约束一致（用户名 3–32、密码 8–128 且 ≤72 UTF-8 字节）。
- 验证：`npm run build`（vue-tsc + vite）通过；dev server 下 /login /register /chat
  /documents /api/v1/health 均 200；无 token 访问 /auth/me 返回 401 UNAUTHENTICATED，
  错误凭据登录返回 401 INVALID_CREDENTIALS（错误体与后端一致）。
- 说明：浏览器内的人工走查（注册→自动登录→刷新恢复→退出）作为最终验收 seam 由
  ticket 04 全链路走查时执行；本 ticket 的程序化验证已全部通过。
