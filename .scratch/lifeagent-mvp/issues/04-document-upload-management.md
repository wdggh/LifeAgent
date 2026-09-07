# 04: 文档上传与管理

**What to build:** 用户能上传 PDF/TXT/Markdown 并指定 document_type；上传立即返回而不等待处理；可查看列表/详情并删除自己的 Document；非法上传被清晰拒绝；原始文件安全落盘且无法被他人访问。

**Blocked by:** 02（认证：注册 / 登录 / 当前用户）

**Status:** resolved

- [ ] 合法文件上传立即返回文档记录（状态 uploaded），响应含 filename、file_type、document_type
- [ ] 上传时不接受任何 user_id 参数，归属只来自当前用户
- [ ] 不支持的扩展名返回 415；超过大小上限返回 413；扩展名与文件内容不符（magic bytes 校验）返回明确错误
- [ ] 文件以安全生成的名字存储；用户看到的仍是原始文件名
- [ ] 文档列表分页并按时间倒序；详情返回 filename、file_type、document_type、status、processing_stage、error_message
- [ ] 删除自己的文档同时移除记录与磁盘文件；删除他人文档返回 404；重复删除返回 404
- [ ] 未认证请求返回 401

## Answer

已实现并验证（commit 见下方）：文档上传/校验/列表/详情/删除。

- `POST /documents`（multipart，201）：扩展名白名单（pdf/txt/markdown）→ magic bytes/UTF-8 内容校验（415）→ 大小上限（413）；成功返回文档信息且不含 file_path
- `GET /documents`（分页、时间倒序）、`GET /documents/{id}`（详情）、`DELETE /documents/{id}`（204，记录+磁盘文件一并删除）
- LocalFileStorage：uuid 存储名 + 动态 upload_dir（测试可重定向临时目录）、幂等删除、路径穿越防御
- documents 模型 + Alembic 0003 迁移（user_id FK CASCADE）；归属隔离：跨用户一律 404；未认证 401
- 测试：10 个文档用例 + 全套 38 passed；真实服务冒烟（上传/列表/详情/删除）通过
