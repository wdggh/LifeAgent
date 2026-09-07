# 02: 认证：注册 / 登录 / 当前用户

**What to build:** 用户能注册、登录并取得访问令牌，之后凭令牌获取自己的用户信息；系统身份永远来自认证信息，客户端无法传入 user_id。

**Blocked by:** 01（项目骨架与健康检查）

**Status:** resolved

- [ ] 注册成功返回用户基本信息；用户名重复返回明确的错误
- [ ] 登录成功返回 access_token；密码错误或用户不存在返回 401
- [ ] 携带有效令牌访问当前用户接口返回本人信息；令牌缺失/无效/过期返回 401
- [ ] 密码只以哈希形式存储（测试断言无法取回明文）
- [ ] 请求体或查询参数中的 user_id 一律被忽略（测试证明服务端身份不被客户端控制）

## Answer

已实现并验证（commit `2d5dab1`）：

- `POST /api/v1/auth/register`（201）、`POST /api/v1/auth/login`（200）、`GET /api/v1/auth/me`（200）
- bcrypt 密码哈希；PyJWT HS256 access token（`sub`=user_id，默认 24h 过期）
- 分层落地：User domain entity → UserRepository 接口 → SQLAlchemy async 实现 → UserService → auth 路由；`get_current_user` 从 bearer token 解析并加载用户
- PostgreSQL 接入：docker-compose（容器端口 5433，规避宿主机原生 Postgres 占用 5432）、SQLAlchemy async + asyncpg、Alembic 迁移 `0001`（users 表）
- 身份边界：请求体/参数中的 user_id 一律拒绝（schema `extra=forbid` → 422）；错误凭据统一 401 INVALID_CREDENTIALS
- 测试：21 passed（含重复用户名 409、弱密码/超长密码 422、过期 token、已删除用户 token、大小写归一化、跨用户隔离语义）
- 真实服务冒烟：register → login → me 全通，无 token 401
