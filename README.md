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

- `game.result_status IN (confirmed, revised)`
- `game.play_status = ended`
- `game.game_type = official`
- `score_logs.effective_status = effective`

也就是说：

- 不直接根据 `game_players` 动态拼排行榜
- 修订时旧流水会 `voided`
- 新流水会重新写入

### 对局与赛果双状态机

- 新对局固定为 `play_status=scheduled`、`result_status=empty`，create/PATCH 均不接受状态或生命周期时间字段。
- 对局状态为 `scheduled -> in_progress -> ended`，`scheduled/in_progress` 可由管理员取消；未进入审核的 ended 对局也可取消。`POST /games/{id}/start|end|cancel` 是对应的专用操作。
- 赛果状态为 `empty -> draft -> submitted -> confirmed`，驳回走 `submitted -> rejected -> draft`，管理员可将 submitted/confirmed/revised 修订为 revised。
- 首次保存草稿会兼容性自动执行 `scheduled -> in_progress`；提交 in-progress 草稿会在同一事务中自动结束对局。未来事件录入 UI 将显式 start。
- 开始后冻结局号、版型与对局类型；取消后通用 PATCH 只读。已提交或生效赛果不能通过当前取消操作 void，需后续专用账本流程。
- 所有状态操作使用 PostgreSQL `SELECT ... FOR UPDATE`，锁后重新校验双状态；冲突返回 `409`，失败请求不留下历史、审计或积分流水。
- `GameStatusHistory` 使用 `status_scope=play|result` 与 `transition_key` 记录每个真实值变化；重复 revised 修订不重复写同值历史，但每次修订仍写 ResultConfirmation 和 AuditLog。
- start、end、cancel、首次/驳回后保存、submit、reject、confirm 和 revise 均写 AuditLog。详见 `docs/architecture/game-state-machines.md`。

### ScoreLog 账本语义

- 已确认或修订的 official、fun 和 practice 对局都可以保留 `ScoreLog.delta`。
- `effective_status=effective` 表示当前有效的流水版本；同一 `game_id + user_id + source_type` 最多只有一条 effective 流水，由 PostgreSQL partial unique index 保护。
- `balance_after` 表示该玩家当时的正式积分余额，与排行榜口径一致。只有 official 对局改变余额；fun 和 practice 流水保留 delta，但不增减正式余额。
- 修订会将该局旧 effective 流水改为 `voided`，为新赛果写入 effective 流水，并对旧新玩家并集重算该赛季后续余额。

### 稳定局内参与者

- `GameParticipant` 是一局内的稳定身份，保存可变的 `user_id`、座位号和比赛时显示名称快照；未来事件 actor/target 将以它作为引用对象。
- `GamePlayer` 只保存角色、阵营、最终状态、胜负、积分、备注和调整项，不再重复保存 user 或 seat。
- 赛果 API 仍扁平返回 `user_id` 与 `seat_number`，并新增 `participant_id`。后续 PUT/revise 应原样回传该 ID。
- 草稿保存采用 participant reconcile：保留行原地更新，新增行创建，移除行单独删除；完全相同的重复保存会保持 participant 与 result ID 不变。
- 显示名称在绑定用户时写入 snapshot，用户之后改名不会重写历史显示名。当前尚无游客创建 UI。
- 架构边界详见 `docs/architecture/game-participants.md`。

### 不可变对局版型快照

- `GameFormat` / `FormatRole` 是 scheduled 阶段使用的可变模板；对局开始后，`GameFormatSnapshot` / `GameFormatRoleSnapshot` 是历史解释的唯一权威。
- 显式 start 与首次草稿 auto-start 会在同一 Game 行锁事务中校验并复制版型、全部角色与独立 JSON metadata；失败不会留下快照、状态、历史或审计记录。
- 赛果读取、保存、提交、审核和修订在已有快照时只按快照验证。源版型之后改名、停用或被 seed 重建角色，不会改变历史对局。
- `GET /api/v1/games/{game_id}/format-context` 明确返回 live 或 frozen context；普通列表只返回 `has_format_snapshot` 与 `format_snapshot_id`。
- migration `20260722_0009` 为有进行或赛果证据的旧对局回填 `legacy_backfill`。它只能证明迁移时可找到的配置，不保证等于比赛发生时的原始配置。
- 快照没有修改或删除 API；除物理删除 Game 的级联外，业务和 seed 均不替换快照。详见 `docs/architecture/game-format-snapshots.md`。

### 结构化对局事件账本

- `GameEvent` 记录局内动作与结算事实，不重复 Game 生命周期、赛果审核、积分或状态历史；普通追加不重复写 AuditLog，纠正和作废会写审计。
- `GET /api/v1/games/{game_id}/derived-state` 将当前 effective timeline 确定性投影为显式阶段、出局记录、警长、票型、已记录动作次数和一致性提示。它是只读记录状态，不是自动裁判或规则引擎结论。
- 可选 `through_logical_sequence` 只读取“当前有效时间线”的逻辑前缀；它不能恢复纠正或作废发生前的历史 as-of 视角。
- 纯投影器不访问数据库、不读取当前时间、不写事件或 Game，并以 `projection_version = 1` 固定当前语义。架构边界详见 `docs/architecture/game-state-projection.md`。
- 主持人事件工作台提供“推导状态”视图，展示显式阶段、参与者出局记录、警长记录、票型、已记录动作次数、轮次摘要和投影提示；前端只负责排序、分组和本地化，不在浏览器中重新实现 reducer。
- 有效时间线中的事件可打开“截止此逻辑位置”的当前有效前缀。该视图在事件纠正、作废或追加后保持所选逻辑位置并重新请求，且不会伪装为过去某一账本时刻的历史快照。详见 `docs/architecture/derived-state-panel.md`。
- `sequence_no` 是不可变账本顺序，`logical_sequence_no` 是有效时间线位置。纠正会追加新版本并继承逻辑位置，原版本保留为 `superseded`；作废保留原文并标记 `voided`。
- Game 行锁与 `next_event_sequence` 串行分配序号；`client_event_id` 提供局内幂等，数据库 partial unique index 保证每个逻辑位置最多一个 active 版本。
- 事件 actor/target 使用稳定 `GameParticipant`，并依赖冻结版型快照。participant 一旦被任意事件引用，当前草稿流程不再允许删除或修改其 user/seat。
- M6.1 仅允许管理员和本局主持人读取或写入；赛果 submitted 后锁定，reject 后重新开放。当前不执行技能、阶段、死亡因果或胜负规则。
- 完整 V1 taxonomy、payload、可见性和并发语义见 `docs/architecture/game-event-ledger.md`。

## 常用本地验证流程

### 1. 登录验证

1. 打开 `http://localhost:3000/login`
2. 使用 `admin_user / password123` 登录
3. 确认首页和导航显示正常
4. 尝试切换中文 / English

### 2. 主持人赛果录入验证

1. 登录 `judge_user`
2. 打开 `/judge/games`
3. 进入一个赛果状态为 `empty`、`draft` 或 `rejected` 且未取消的对局
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
- `GET /api/v1/games/{game_id}/format-context`
- `PATCH /api/v1/games/{game_id}`
- `POST /api/v1/games/{game_id}/start`
- `POST /api/v1/games/{game_id}/end`
- `POST /api/v1/games/{game_id}/cancel`
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

### 对局事件

- `GET /api/v1/game-events/definitions`
- `GET /api/v1/games/{game_id}/derived-state`
- `GET /api/v1/games/{game_id}/events`
- `GET /api/v1/games/{game_id}/events/{event_id}`
- `POST /api/v1/games/{game_id}/events`
- `POST /api/v1/games/{game_id}/events/{event_id}/correct`
- `POST /api/v1/games/{game_id}/events/{event_id}/void`

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

前端使用已提交的 `package-lock.json` 安装依赖，并执行与 CI 相同的质量检查：

```bash
cd frontend
npm ci
npm run lint
npx tsc --noEmit
npm run test
npm run build
```

后端使用 `uv.lock` 的锁定依赖：

```bash
cd backend
uv sync --frozen --dev
uv run pytest -q
uv run alembic heads
```

`pytest` 同时运行纯单元测试和真实 PostgreSQL 集成测试。集成测试不使用 SQLite，也不运行 seed：

- 未设置 `TEST_DATABASE_ADMIN_URL` 时，测试夹具会通过 `docker-compose.test.yml` 启动本地 PostgreSQL。
- 每次 pytest session 创建随机命名的 `wolfboard_test_*` 数据库，自动执行 `alembic upgrade head`。
- 每个测试前会清空应用表，保留 Alembic revision；测试结束或失败后会删除随机数据库和由夹具启动的容器。
- CI 可以通过 `TEST_DATABASE_ADMIN_URL` 指向 CI 专用 PostgreSQL service；不应指向开发或生产数据库。

也可手动预启动本地测试 PostgreSQL：

```bash
docker compose --project-name wolfboard-tests -f docker-compose.test.yml up --detach --wait
cd backend
uv run pytest -q
```

若未设置外部测试 URL，pytest 会在本次运行后回收该 Compose 服务。

### CI 质量门

`.github/workflows/quality.yml` 在 push 和 pull request 上并行运行：

- Frontend：`npm ci`、ESLint、TypeScript 检查、Vitest、production build。
- Backend：`uv sync --frozen --dev`、CI PostgreSQL service、`alembic upgrade head`、`pytest -q`。
- CI 不运行 seed，也不需要真实 secrets。

### 已知缺陷基线

M6.0C 已将最后一条 strict xfail（重复保存草稿导致 `GamePlayer.id` 变化）转为普通通过测试。当前测试套件为 `0 xfailed`。

## 当前未实现内容

当前已提供 `/judge/games/{game_id}/events` 主持人事件工作台。工作台从服务器 definitions 注册表读取权威事件约束，支持 22 种 V1 事件、有效时间线、完整账本、纠正、作废，以及基于 `client_event_id` 的安全重试。本地未提交表单仅保存在版本化的 `localStorage` 记录中，不包含令牌或完整 Game 数据。

当前工作台已接入后端确定性只读状态投影，可查看最新有效状态或有效时间线的逻辑前缀，并从推导结果定位原始事件。仍未实现：

- 面向普通玩家或公众的可见性 projection 与复盘页面
- 自动裁判 / 自动胜负推导
- 历史账本 as-of 回放
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
