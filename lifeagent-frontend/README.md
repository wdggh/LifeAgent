# LifeAgent Frontend V1

Vue 3 前端 V1。API 全部以实际后端为准，V1 阶段不修改已经验收的后端。
当前（ticket 01）已实现认证与 App Shell：注册并自动登录、登录、刷新恢复
登录态、401 自动回登录页、退出登录；对话与文档页面仍是占位，由后续 ticket
填充。

## 技术栈

- Vue 3 + TypeScript
- Vite（开发/构建）
- Vue Router（页面路由）
- Pinia（全局状态）
- Axios（HTTP 请求）
- Element Plus（UI 组件）

## 快速开始

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
│   ├── components/   # 可复用 UI 组件（AppShell/AppSidebar 已落地；气泡/来源列表后续补充）
│   ├── views/        # 页面级组件（Login/Register 已实现；Chat/Documents 为占位）
│   ├── stores/       # Pinia 全局状态（auth 已实现；conversation/document 后续补充）
│   ├── router/       # Vue Router 配置
│   ├── types/        # 与后端 API 对齐的 TypeScript 类型（auth 已落地，其余后续补充）
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

## 已知事项（对接下一阶段前需确认）

1. 后端实际「发消息」接口是 `POST /api/v1/chat`
   （请求 `{conversation_id, query}`，响应 `{answer, sources, metadata}`），
   计划文档中写的 `POST /api/v1/conversations/{id}/messages` 在后端不存在。
2. V1 开发环境已定走 Vite Proxy（浏览器只访问 5173），因此不需要给后端加
   CORS，后端保持冻结状态。
