# Wolfboard

[中文](./README.md) | [English](./README.en.md)

狼人杀赛事记录与管理平台。

当前仓库已经覆盖：

- `Milestone 1`：认证、多角色权限、项目骨架
- `Milestone 2`：赛季、比赛日、报名、签到
- `Milestone 3`：版型预置、对局管理、主持人分配
- `Milestone 4`：赛果录入、草稿保存、提交
- `Milestone 5`：管理员确认、修订、正式积分流水、排行榜、玩家资料、审计日志
- 中英文界面切换：默认中文，可切换英文

## 项目概览

Wolfboard 的目标不是做一个展示型官网，而是做一套可长期维护、可追溯、可扩展的狼人杀赛事运营系统。

当前版本已经形成完整的结果层闭环：

1. 用户登录并按角色进入系统
2. 管理员创建赛季与比赛日
3. 玩家报名，管理员签到
4. 管理员创建对局并分配主持人
5. 主持人录入并提交赛果
6. 管理员确认或修订结果
7. 系统生成正式积分流水并更新排行榜

## 当前能力

| 模块 | 当前状态 | 说明 |
| --- | --- | --- |
| 认证与权限 | 已完成 | `users + roles + user_roles` 多角色模型 |
| 赛季与比赛日 | 已完成 | 支持创建、编辑、查看 |
| 报名与签到 | 已完成 | 玩家报名，管理员签到与状态管理 |
| 版型与角色构成 | 已完成 | 系统预置版型 + 角色列表 |
| 对局管理 | 已完成 | 创建对局、绑定版型、分配主持人 |
| 赛果录入 | 已完成 | judge 可保存草稿、提交赛果 |
| 结果确认与修订 | 已完成 | admin 可确认、驳回、修订 |
| 正式积分流水 | 已完成 | 基于 `score_logs` 生效，不直接拼 `game_players` |
| 排行榜与玩家页 | 已完成 | 赛季排行榜、玩家历史积分 |
| 审计与追溯 | 已完成 | `audit_logs` + `game_status_history` |
| 事件流 | 未开始 | 留作后续 Milestone |

## 技术栈

| 层级 | 技术 |
| --- | --- |
| Frontend | Next.js App Router, TypeScript, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy 2.0, Pydantic, Alembic |
| Database | PostgreSQL |
| Python 环境 | uv |
| 本地开发 | Docker Compose |

## 仓库结构

```text
repo-root/
├─ frontend/
│  ├─ app/
│  ├─ components/
│  ├─ lib/
│  ├─ Dockerfile
│  └─ package.json
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ models/
│  │  ├─ schemas/
│  │  ├─ scripts/
│  │  └─ services/
│  ├─ migrations/
│  ├─ tests/
│  ├─ Dockerfile
│  ├─ alembic.ini
│  └─ pyproject.toml
├─ docker-compose.yml
├─ .env.example
├─ README.md
└─ README.en.md
```

## 快速开始

### 方式一：直接用 Docker 跑全栈

```bash
docker compose up --build
```

启动后可访问：

| 服务 | 地址 |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Swagger Docs | `http://localhost:8000/docs` |
| PostgreSQL | `localhost:5432` |

后端容器启动时会自动执行：

1. Alembic migration
2. seed 默认样例数据
3. 启动 FastAPI 服务

### 方式二：分别本地运行前后端

#### Backend

```bash
cd backend
uv sync --dev
uv run alembic upgrade head
uv run python -m app.scripts.seed
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

默认前端会请求：

```text
http://localhost:8000/api/v1
```

## 环境变量

如果你需要自定义本地配置，可以先复制：

```powershell
Copy-Item .env.example .env
```

若单独运行后端，可在 `backend/.env` 中设置：

```env
DATABASE_URL=postgresql+psycopg://wolfboard:wolfboard@localhost:5432/wolfboard
JWT_SECRET_KEY=change-this-secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
BACKEND_CORS_ORIGINS=http://localhost:3000
```

## 默认测试账号

所有样例账号密码统一为：

```text
password123
```

| 用户名 | 角色 |
| --- | --- |
| `admin_user` | `admin + judge + player` |
| `judge_user` | `judge + player` |
| `player_user` | `player` |

## 默认样例数据

### 赛季与比赛日

- `S1 试验赛季`
- `2026-04-05 正赛日`
- `2026-03-29 社群比赛日`

### 预置版型

当前默认 seed 至少包含以下 10 个版型：

- `预女猎白混`
- `狼王守卫`
- `狼美骑士`
- `机械狼通灵师`
- `梦魇摄梦人`
- `孤注一掷`
- `盗宝大师`
- `假面舞会`
- `唯邻是从`
- `魔幻对决`

并且每个版型都带有基础角色构成。

### 示例对局

默认会生成：

- 正式局 3 局
- 娱乐局 1 局
- 至少一局分配给 `judge_user`
- 至少一局分配给 `admin_user`

## 语言支持

当前前端支持中英文双语：

- 默认语言：简体中文
- 可切换语言：中文 / English
- 切换入口：登录页、登录后站点壳子
- 存储方式：浏览器 `localStorage`
- 存储 key：`wolfboard-language`

说明：

- 系统预置文案与预置版型说明支持双语
- 用户自己录入的自由文本不会被自动翻译

## 核心业务规则

### 多角色权限

系统不使用单一 `users.role_id`。

而是使用：

- `users`
- `roles`
- `user_roles`

一个用户可以同时拥有多个系统角色，例如：

- `player + judge`
- `player + admin`
- `player + judge + admin`

### 积分规则

当前基础积分规则为：

- 好人胜利：`+1`
- 狼人胜利：`+1.5`
- 失败：`-1`

调整项通过 `score_adjustments` 单独记录，最终正式积分通过 `score_logs` 生效。

### 排行榜规则

排行榜只统计：

- `game.status IN (confirmed, revised)`
- `game.game_type = official`
- `score_logs.effective_status = effective`

也就是说：

- 不直接根据 `game_players` 动态拼排行榜
- 修订时旧流水会 `voided`
- 新流水会重新写入

## 常用本地验证流程

### 1. 登录验证

1. 打开 `http://localhost:3000/login`
2. 使用 `admin_user / password123` 登录
3. 确认首页和导航显示正常
4. 尝试切换中文 / English

### 2. 主持人赛果录入验证

1. 登录 `judge_user`
2. 打开 `/judge/games`
3. 进入一个 `draft` 或 `in_progress` 的对局
4. 保存草稿
5. 提交赛果
6. 确认页面变为只读

### 3. 管理员审核验证

1. 登录 `admin_user`
2. 打开 `/admin/games/review`
3. 进入一个 `submitted` 对局
4. 点击确认
5. 打开 `/leaderboard`
6. 检查排行榜更新

### 4. 管理员修订验证

1. 在审核页进入修订页
2. 修改玩家结果或加扣分
3. 填写修订原因
4. 提交修订
5. 检查旧 `score_logs` 是否 `voided`
6. 检查新 `score_logs` 是否重新生成

## 常用 API

这里只列当前较核心的一部分接口：

### 认证

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

### 赛事组织

- `GET /api/v1/seasons`
- `POST /api/v1/seasons`
- `GET /api/v1/seasons/{season_id}`
- `PATCH /api/v1/seasons/{season_id}`
- `GET /api/v1/event-days/{event_day_id}`
- `POST /api/v1/event-days`
- `PATCH /api/v1/event-days/{event_day_id}`
- `POST /api/v1/event-days/{event_day_id}/registrations`
- `GET /api/v1/event-days/{event_day_id}/registrations`

### 版型与对局

- `GET /api/v1/formats`
- `GET /api/v1/formats/{format_id}`
- `GET /api/v1/event-days/{event_day_id}/games`
- `POST /api/v1/games`
- `GET /api/v1/games/{game_id}`
- `PATCH /api/v1/games/{game_id}`
- `GET /api/v1/judges/me/games`

### 赛果与积分

- `GET /api/v1/games/{game_id}/result-draft`
- `PUT /api/v1/games/{game_id}/result-draft`
- `POST /api/v1/games/{game_id}/submit-result`
- `GET /api/v1/admin/games/review`
- `POST /api/v1/games/{game_id}/confirm-result`
- `POST /api/v1/games/{game_id}/reject-result`
- `POST /api/v1/games/{game_id}/revise-result`
- `GET /api/v1/seasons/{season_id}/leaderboard`
- `GET /api/v1/players/{player_id}/profile`
- `GET /api/v1/audit-logs`

## 数据库迁移

执行迁移：

```bash
cd backend
uv run alembic upgrade head
```

生成新 migration：

```bash
cd backend
uv run alembic revision --autogenerate -m "describe your change"
```

## 测试

后端测试：

```bash
cd backend
uv run pytest
```

## 当前未实现内容

当前仍未实现：

- 事件流录入
- 自动裁判 / 自动胜负推导
- 复盘回放系统
- 复杂规则引擎

这些能力会在后续 Milestone 中继续推进。

## 开发约定

- 不直接在 `main` 上开发
- 默认从最新 `dev` 检出功能分支
- 使用 Conventional Commits
- 重要改动通过 PR 合并
- 代码注释和 docstring 统一使用英语

## 许可证

当前仓库未单独声明开源许可证。如需公开分发，请后续补充正式 License。
