# 03: 会话 + Chat（核心闭环）

**What to build:** A user can see, open, create, and delete Conversations from the sidebar; starting 新对话 is a draft that creates the Conversation with the first message; sending a question produces an Answer with its Sources, history survives refresh and deep links, and only one question is in flight at a time without messages landing in the wrong Conversation.

**Blocked by:** 01（认证 + App Shell）

**Status:** resolved

- [ ] The sidebar lists Conversations newest first; opening one shows its message history as paired user/assistant turns
- [ ] Clicking 新对话 starts a draft state and creates no Conversation until the first message is sent
- [ ] The first message creates the Conversation (title from the first question) and the Answer appears in that Conversation, which then shows in the sidebar
- [ ] While an Answer is loading, sending is disabled with a visible processing state, and the user can still switch to other Conversations
- [ ] If a response finishes after switching away, nothing is inserted into the wrong Conversation; the list refreshes with a light notification
- [ ] Answers render as plain text; Sources appear as Document cards with relevance; metadata shows 检索 N 次 · 用时 X.Xs; no-Source answers show 本次未引用文档
- [ ] A failed chat shows an honest error and refreshes history instead of automatically re-sending the same question
- [ ] Deleting a Conversation asks for confirmation and keeps the sidebar and current view consistent
- [ ] Refreshing or deep-linking to a Conversation restores it
- [ ] Acceptance: walkthrough checklist passes and `npm run build` succeeds

## Answer

已实现并验证（本批提交）：

- 会话/聊天 API 模块（列表/详情/删除、创建、POST /chat），chat 按请求 120s 超时。
- 侧栏会话列表（新的在前）支持打开与删除（二次确认）；标题为空显示「未命名对话」。
- 新对话 = conversationStore draft（无 conversation_id，不产生后端对象，ADR-0008）；
  首条消息才 POST /conversations（title=首问截断 30 字）→ POST /chat → 刷新列表。
- 发送：乐观 user 气泡 + 全局单 in-flight（输入禁用、显示“思考中”）；期间可切会话；
  回答返回时若已切走，只刷新列表并提示，不向当前会话插入内容；返回路径与地址栏
  /chat/:conversationId 保持同步（含深链/刷新恢复）。
- 呈现：user/assistant 气泡、纯文本保留换行；来源卡片（📄 文档名 + 相关性进度）；
  metadata 小字（检索 N 次 · 用时 X.Xs）；无来源回答显示「本次未引用文档」。
- 失败语义：不自动重发；失败后刷新历史把可能已落库的 user Message 如实显示，
  内联提示“再次发送会留下重复提问，请自行决定”；离开会话时以 toast 提示。
- 已知限制（记入 ticket 04 候选）：历史 assistant 消息的来源/检索信息仅会话内内存
  缓存，刷新后不可见（后端 Message 不含来源字段，V1 不做前端持久化）。
- 验证：vue-tsc + vite 构建通过；/chat 与 /chat/:id、/documents 路由及 API 端点可达；
  完整提问→来源展示人工走查留到 ticket 04。
