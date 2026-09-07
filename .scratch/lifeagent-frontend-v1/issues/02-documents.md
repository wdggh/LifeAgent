# 02: 我的文档（上传 / 列表 / 状态 / 删除 / 重试）

**What to build:** A user can open 我的文档 and see their Documents with processing status; upload several files at once under one chosen Document type; watch each file move from upload to processing to completed or failed; see why a failed Document failed and retry it; and delete Documents they no longer need.

**Blocked by:** 01（认证 + App Shell）

**Status:** ready-for-agent

- [ ] Opening 我的文档 shows the Document list (newest first) or a clear empty state
- [ ] The upload dialog lets the user pick a Document type first (Chinese labels, default other) and select multiple files
- [ ] Client-side checks reject unsupported types and oversized files with clear messages before upload
- [ ] Uploaded files appear immediately, each with its own state line, and reach 已完成 / 处理失败 with error visibility
- [ ] Processing Documents refresh automatically and stop refreshing once they reach a terminal state
- [ ] A row can be expanded to show processing stage, file type, size, Document type, and timestamps
- [ ] A failed Document can be retried; deletion asks for confirmation and disappears on success, with a retryable message if deletion fails
- [ ] Status, type, and error copy follows the locked Chinese copy table
- [ ] Acceptance: walkthrough checklist passes and `npm run build` succeeds
