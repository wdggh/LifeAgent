# 10: 生产化收口：一键启动与端到端验收

**What to build:** 一条命令启动完整环境（数据库、Redis、向量库、API、worker、迁移）；错误契约与依赖健康检查收口；README 与新用户快速开始流程齐全；端到端冒烟覆盖 MVP 主闭环；全量测试绿。

**Blocked by:** 06（任务执行与失败语义）、07（删除级联：向量、文件、记录）、09（Chat v2：get_document 深挖与页级来源）

**Status:** ready-for-agent

- [ ] `docker compose up` 一次完成：postgres healthy → migrate 完成 → api/worker 启动，redis 与独立向量库可用，上传目录为 api/worker 共享卷
- [ ] 端到端冒烟：注册 → 上传 → 文档 completed → 提问 → 得到带来源的回答
- [ ] 依赖不可用时健康检查或相关接口返回 503 类明确错误，而不是笼统崩溃
- [ ] 统一错误体在所有端点生效（code/message/request_id）
- [ ] README 含快速开始、环境变量说明与本地开发指引
- [ ] 全量自动化测试通过，含跨用户隔离矩阵
