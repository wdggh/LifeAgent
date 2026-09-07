# 04: 打磨与最终验收

**What to build:** V1 becomes deliverable: empty, loading, and error states are polished; the full chain is accepted through a human walkthrough against the real backend; and known limitations plus follow-up candidates are recorded.

**Blocked by:** 02（我的文档）、03（会话 + Chat）

**Status:** ready-for-agent

- [ ] Empty, loading, and error states are clear for no Documents, no Conversations, draft input, and first-use
- [ ] Full-chain walkthrough passes: register → login → upload → completed → ask a question → Answer with Sources → refresh and resume → log out → log back in
- [ ] Error paths are verified: expired session, service unavailable (chat and upload), network loss, oversized/unsupported files
- [ ] UI copy matches the glossary (对话 / 文档 / 消息 / 来源 / 保修凭证) everywhere visible
- [ ] The project builds (`npm run build`) and a fresh environment can start the frontend with the documented run steps
- [ ] Known limitations and follow-up candidates are recorded (automated tests, Markdown rendering, document pagination beyond 100, deployment CORS/Nginx decision, backend-side chat idempotency)
