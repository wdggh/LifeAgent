# 03: 会话 + Chat（核心闭环）

**What to build:** A user can see, open, create, and delete Conversations from the sidebar; starting 新对话 is a draft that creates the Conversation with the first message; sending a question produces an Answer with its Sources, history survives refresh and deep links, and only one question is in flight at a time without messages landing in the wrong Conversation.

**Blocked by:** 01（认证 + App Shell）

**Status:** ready-for-agent

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
