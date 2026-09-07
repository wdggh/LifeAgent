# LifeAgent Frontend V1

Vue 3 前端 V1。API 全部以实际后端为准，V1 阶段不修改已经验收的后端。
已实现：认证与 App Shell（注册自动登录/登录/刷新恢复/401 回登录/退出）、
我的文档（多文件上传、处理状态轮询、失败重试、删除、行展开详情）、对话与
Chat（新对话草稿、首问建对话、消息历史、答案与来源展示、单 in-flight、
失败语义）。后端契约与实现边界见仓库 `.scratch/lifeagent-frontend-v1/`。

## 技术栈

- Vue 3 + TypeScript
- Vite（开发/构建）
- Vue Router（页面路由）
- Pinia（全局状态）
- Axios（HTTP 请求）
- Element Plus（UI 组件）

## 快速开始

前提：后端已通过 `docker compose up -d --build` 启动并监听宿主机 8080；
chat 与文档处理需要 LLM/Embedding provider key（在仓库根 `.env` 配置
`DEEPSEEK_API_KEY`/`DASHSCOPE_API_KEY`，在 compose 启动前生效）。

```bash
npm install
cp .env.example .env   # 按需修改 VITE_API_BASE_URL
npm run dev            # http://localhost:5173
```

开发期请求链路（无跨域）：

```text
浏览器 → http://localhost:5173 → Vite Proxy → http://localhost:8080 → FastAPI
```

构建与类型检查：

```bash
npm run build
```

## 目录结构

```text
lifeagent-frontend/
├── src/
│   ├── api/          # API 层：client.ts 是统一 Axios 实例，errors.ts 统一解码后端错误体
│   ├── components/   # 可复用 UI 组件（AppShell/AppSidebar/ChatMessage/SourceList/上传对话框）
│   ├── views/        # 页面级组件（Login/Register/Chat/Documents）
│   ├── stores/       # Pinia 全局状态（auth/conversation/document）
│   ├── router/       # Vue Router 配置
│   ├── types/        # 与后端 API 对齐的 TypeScript 类型
│   ├── App.vue       # 根组件
│   └── main.ts       # 入口：装配 Pinia / Router / Element Plus
├── .env.example      # 环境变量模板
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 分层约定

页面不直接调用 Axios，请求链路固定为：

```text
views / components → stores → api/xxx.ts → api/client.ts → FastAPI
```

这样 JWT、`Authorization`、`request_id`、401 自动处理、统一错误提示将来都只改
`api/client.ts` 一处。

## 环境变量

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `VITE_API_BASE_URL` | API 根路径（开发期走 Vite 代理） | `/api/v1` |

> 注意：`/api/v1` 由 `vite.config.ts` 代理到宿主机 8080（容器内 8000），
> 原样转发、不做路径重写。该代理只在 `npm run dev` 时生效；部署架构
> （Nginx 同源转发或直连 API + CORS）等正式部署时再定。

## API 对接事实

1. 后端实际「发消息」接口是 `POST /api/v1/chat`
   （请求 `{conversation_id, query}`，响应 `{answer, sources, metadata}`），
   计划文档中写的 `POST /api/v1/conversations/{id}/messages` 在后端不存在。
2. V1 开发环境已定走 Vite Proxy（浏览器只访问 5173），因此不需要给后端加
   CORS，后端保持冻结状态。

## 人工验收走查（V1 验收 seam）

1. 注册 → 自动登录进入对话页
2. 我的文档 → 上传一个 PDF/TXT/Markdown → 等待状态到「已完成」（或「处理失败」后重试）
3. 回到对话 → 点「新对话」输入问题 → 得到答案与来源卡片
4. 刷新页面 → 对话与历史仍在 → 可继续提问
5. 退出登录 → 重新登录 → 数据仍在
6. 异常路径抽查：过期 token 回登录页、后端停止时给出可读错误、上传超限/不支持类型被拦截

## V1 已知限制与后续候选

- 自动化前端测试（Vitest/Playwright）、答案 Markdown 渲染、文档超过 100 条的分页
- 部署期 CORS/Nginx 方案（当前 Vite Proxy 仅开发期生效）
- chat 幂等重发、历史 assistant 消息的来源/检索信息持久化（后端 Message 无来源字段）
- 注册账号会真实写入开发库且无删除用户接口，测试账号需手动清理或重置 volume
