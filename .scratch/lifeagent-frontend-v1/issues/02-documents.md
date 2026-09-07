# 02: 我的文档（上传 / 列表 / 状态 / 删除 / 重试）

**What to build:** A user can open 我的文档 and see their Documents with processing status; upload several files at once under one chosen Document type; watch each file move from upload to processing to completed or failed; see why a failed Document failed and retry it; and delete Documents they no longer need.

**Blocked by:** 01（认证 + App Shell）

**Status:** resolved

- [ ] Opening 我的文档 shows the Document list (newest first) or a clear empty state
- [ ] The upload dialog lets the user pick a Document type first (Chinese labels, default other) and select multiple files
- [ ] Client-side checks reject unsupported types and oversized files with clear messages before upload
- [ ] Uploaded files appear immediately, each with its own state line, and reach 已完成 / 处理失败 with error visibility
- [ ] Processing Documents refresh automatically and stop refreshing once they reach a terminal state
- [ ] A row can be expanded to show processing stage, file type, size, Document type, and timestamps
- [ ] A failed Document can be retried; deletion asks for confirmation and disappears on success, with a retryable message if deletion fails
- [ ] Status, type, and error copy follows the locked Chinese copy table
- [ ] Acceptance: walkthrough checklist passes and `npm run build` succeeds

## Answer

已实现并验证（commit 见 03 之后的本批提交）：

- 文档 API 模块（列表 page/page_size、详情、上传、删除、重试）与后端 schema/约束对齐；
  上传按请求覆盖 120s 超时。
- 上传对话框：先选文档类型（六类中文标签，默认 other）、多选文件、客户端预校验
  （扩展名 .pdf/.txt/.md、≤50MB）；逐个上传、每文件独立状态行（预校验/上传中/
  处理中/完成/失败）并显示错误；失败行提示可在列表重试。
- 列表：page_size=100 单页；只轮询 processing 文档（3s），到终态自动停止；
  行展开显示处理阶段/文件类型/大小/文档类型/时间/错误信息；删除需确认并同步列表；
  failed 行提供重试。
- UI 文案使用锁定中文表（合同/购买记录/保修凭证/…、已上传/处理中/已完成/处理失败）。
- 验证：vue-tsc + vite 构建通过；dev server 下 /documents 与列表/上传端点可达；
  真实文件上传→处理→重试的人工走查留到 ticket 04 全链路验收。
