# Text AIGC Reducer

中文文本降 AIGC 率智能体应用（FastAPI + LangChain/LangGraph + Vue3）。

## 项目简介

系统围绕「改写 -> 检测 -> 决策」闭环运行，目标是在保证语义不变的前提下，降低文本 AIGC 检测分数。

默认策略为：
- `deai_external`（外部规则增强）

策略、任务默认值与 LLM 非敏感运行参数现已支持在管理中心在线修改。

## 技术栈

后端：
- FastAPI
- SQLAlchemy + Alembic
- LangChain + LangGraph
- JWT 鉴权 + RBAC

前端：
- Vue 3 + Vite + TypeScript
- Pinia + Vue Router
- Element Plus

## 目录结构

```text
.
├─ backend/
│  ├─ app/                  # API、鉴权、RBAC、任务闭环
│  ├─ alembic/              # 迁移脚本
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/                  # 登录、工作台、任务、历史、管理中心
│  ├─ package.json
│  └─ .env.example
├─ prompts/zh-CN/           # Prompt YAML（统一管理，禁止硬编码）
├─ .external/               # 外部规则仓库（可选）
└─ run.bat                  # 一键安装/迁移/启动
```

## 核心能力

- 异步任务状态机：`queued/running/success/not_met/failed`
- 闭环节点：`load_prompt -> rewrite_with_llm -> detect_score -> decide_next -> persist_iteration`
- 达标规则：任一轮 `score <= target_score` 立即成功
- 未达标规则：达到最大轮次返回最低分版本并标记 `not_met`
- 检测适配器：`MockDetector`（默认）/ `HttpDetector`（可替换第三方）
- Prompt YAML 在线管理（管理员可在系统内查看/编辑/保存/热重载）
- 系统设置在线管理（管理员可在系统内修改默认目标分数、轮次、策略和 LLM 非敏感参数）

## 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+

### 1) 准备环境变量

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env
```

`backend/.env` 现在主要放两类配置：
- 密钥与部署级敏感配置，例如 `OPENAI_API_KEY`、`SECRET_KEY`
- 不适合由业务用户在线修改的基础设施参数，例如数据库连接、鉴权过期时间、检测器地址

以下运行参数不再建议放在 `.env` 中维护，而是在 Web 管理中心直接修改：
- 默认目标分数
- 默认最大轮次
- 默认策略
- `use_mock_llm`
- `openai_base_url`
- `openai_model`
- `openai_timeout_seconds`
- `openai_max_retries`

默认管理员（可在 `backend/.env` 修改）：
- 用户名：`admin`
- 密码：`Admin@123456`

### 2) 一键启动（推荐）

```powershell
.\run.bat
```

可选参数：

```powershell
.\run.bat --install
.\run.bat --no-start
.\run.bat --skip-migrate
```

启动后访问：
- 前端：`http://localhost:5173`
- 后端：`http://localhost:8000`
- OpenAPI：`http://localhost:8000/docs`

### 3) 首次登录后配置运行参数

使用管理员账号登录后，进入“管理中心 -> 系统设置”配置以下内容：
- 默认任务参数：目标 AIGC 率、最大轮次、默认策略
- LLM 运行参数：模式、Base URL、模型、超时、重试次数

注意：
- `OPENAI_API_KEY` 仍然只从 `backend/.env` 读取
- 当 `use_mock_llm=auto` 且未配置 `OPENAI_API_KEY` 时，系统会自动退回 Mock 模式

### 4) 升级已有数据库

本次版本新增了 `system_settings` 表。如果你是在已有数据基础上升级，需要执行：

```powershell
cd backend
alembic upgrade head
```

## 主要接口

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/tasks`
- `GET /api/v1/tasks/{task_id}/export`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PATCH /api/v1/users/{id}/role`
- `GET /api/v1/prompts/metadata`
- `GET /api/v1/prompts/{group}/{name}`
- `PUT /api/v1/prompts/{group}/{name}`
- `POST /api/v1/prompts/reload`
- `GET /api/v1/system-settings/runtime`
- `PUT /api/v1/system-settings/runtime`

## 测试

```powershell
cd backend
python -m pytest
```

## 常见问题

- 登录后无管理权限：检查 `admin` 是否仍绑定 `admin` 角色。
- 改写效果弱：先检查管理中心中的系统设置，确认 `use_mock_llm`、`openai_model`、`openai_base_url` 和超时配置是否正确，再确认 `backend/.env` 中已配置 `OPENAI_API_KEY`。
- 数据库连接失败：核对 `DATABASE_URL`/`SYNC_DATABASE_URL` 用户名密码及权限。
