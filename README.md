# AI-DevSupport：面向 API 开放平台的多智能体技术支持系统

AI-DevSupport 是一个面向 API 开放平台技术支持场景的研究型原型系统。项目关注的问题是：当开发者遇到鉴权失败、接口限流、签名错误、账单异常等问题时，如何让大语言模型不仅回答文档问题，还能够结合调用日志、账户状态和业务规则完成可解释的诊断，并在风险较高或证据不足时安全地转交人工处理。

本项目采用多智能体协作与检索增强生成（RAG）相结合的方法，将意图识别、文档检索、API 故障诊断、账单分析、工单处理和敏感信息审查组织为一条完整工作流。系统定位为课程设计或科研实践原型，重点验证多智能体编排在技术支持任务中的可行性，而非直接用于生产环境。

## 研究目标

项目主要围绕以下问题展开：

1. 如何根据用户问题动态选择文档问答、故障诊断和账单分析等不同能力；
2. 如何联合结构化业务数据与非结构化文档，提高回答的依据完整性；
3. 如何记录智能体执行过程，使诊断结果可以追踪和复核；
4. 如何在模型输出前执行统一的敏感信息检测与人工兜底策略；
5. 如何通过评估集、链路耗时和 Token 用量对系统效果进行初步分析。

## 系统功能

| 功能 | 说明 |
| --- | --- |
| 文档问答 | 对 API 接入、签名、回调、计费等知识进行混合检索、重排和引用式回答 |
| API 故障诊断 | 结合 request_id、调用日志、错误码和 API Key 状态生成诊断结论与修复建议 |
| 账单分析 | 对比不同月份的调用量和费用构成，解释费用变化 |
| 多智能体编排 | 根据问题意图调度一个或多个专业 Agent，并对结果进行汇总 |
| 工单流转 | 在证据不足、操作风险较高或模型无法处理时创建人工工单 |
| 安全审查 | 对 API Key、Secret、Token、手机号、邮箱、身份证号和银行卡号等信息进行检测与脱敏 |
| 链路观测 | 展示节点耗时、模型调用、命中文档和 Token 用量 |

可以使用以下问题观察系统在不同任务下的处理过程：

```text
我调用实名认证接口一直返回 401。
今天下午出现很多 429，是不是服务故障？
接口签名应该如何生成？
为什么这个月的费用比上个月高？
```

## 方法与架构

系统的主要处理流程为：

```text
用户请求
   ↓
身份认证与租户隔离
   ↓
意图识别与任务路由
   ↓
文档问答 / API 诊断 / 账单分析（按需执行）
   ↓
结果汇总与工单判断
   ↓
敏感信息审查
   ↓
流式返回与链路记录
```

整体实现分为三层：

- 交互层：使用 FastAPI 提供 REST 与 SSE 接口，React 实现用户端和内部工作台；
- 智能体层：使用 LangGraph 组织意图路由、专业 Agent、结果汇总与安全审查；
- 数据与工具层：使用 MySQL 保存业务数据，Milvus 保存知识向量，Redis 管理缓存和会话，并通过工具接口向 Agent 提供结构化证据。

安全审查位于输出流程末端，避免不同专业 Agent 绕过统一脱敏规则。对套餐变更、退款和密钥重置等高风险操作，当前原型仅进行工单转交，不允许模型直接执行。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 | Python 3.11+、FastAPI、LangGraph、SQLAlchemy |
| 模型服务 | DashScope OpenAI 兼容接口、Qwen、text-embedding-v3、gte-rerank-v2 |
| 数据存储 | MySQL 8、Redis 7、Milvus 2.4、MinIO |
| 前端 | React 18、TypeScript、Vite、Ant Design、React Flow |
| 工程与评估 | Docker Compose、pytest、评估集、并发压测脚本 |

## 项目结构

```text
AI-DevSupport/
├── backend/
│   ├── app/          # API、Agent、RAG、工具、安全与可观测模块
│   ├── scripts/      # 建表、种子数据和知识库入库脚本
│   ├── eval/         # 功能与安全评估集
│   └── benchmark/    # 并发压测脚本
├── frontend/         # React 前端
├── data/knowledge/   # RAG 使用的领域文档
├── docker-compose.yml
└── Makefile
```

## 运行环境

运行项目前需要准备：

- Docker 与 Docker Compose v2；
- Python 3.11 或更高版本，推荐 Python 3.11；
- Node.js 18 或更高版本，推荐 Node.js 20 LTS；
- 可用的 DashScope API Key。

模型、Embedding 和 Rerank 请求会调用外部服务，可能产生费用。请勿将真实 API Key 提交到代码仓库。

## 快速复现

### 1. 安装后端依赖

Linux 或 macOS：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

编辑 `backend/.env`，填写模型服务密钥：

```env
DASHSCOPE_API_KEY=your_api_key
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 启动基础设施

根目录中的 Docker Compose 负责启动 MySQL、Redis、Milvus、etcd 和 MinIO，不包含前后端应用容器。

```bash
docker compose up -d
docker compose ps
```

首次启动 Milvus 通常需要一段时间。请等待相关容器显示为 `healthy` 后再初始化数据。

### 4. 初始化实验数据

激活后端虚拟环境，并在项目根目录执行：

```bash
cd backend
python -m scripts.init_db --recreate
python -m scripts.seed_data
python -m scripts.ingest_knowledge
```

其中知识库入库步骤会调用 Embedding 服务。

### 5. 启动后端与前端

后端终端：

```bash
cd backend
uvicorn app.main:app --reload
```

前端终端：

```bash
cd frontend
npm run dev
```

启动完成后可访问：

| 服务 | 地址 |
| --- | --- |
| Web 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| OpenAPI 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/api/health |
| MinIO 控制台 | http://localhost:9003 |

## 演示账户

种子数据中的账户密码统一为 `password123`，仅用于本地实验：

| 账户 | 角色 | 可观察功能 |
| --- | --- | --- |
| `dev_acme` | 客户开发者 | 智能问答、会话与工单 |
| `admin_acme` | 客户管理员 | 客户侧管理功能 |
| `support1` | 技术支持人员 | 工单工作台与诊断链路 |
| `admin` | 系统管理员 | 运营指标与评估入口 |

## 评估与实验

项目提供两类实验脚本：

```bash
make eval
make bench
```

- `make eval`：运行意图识别、文档引用和敏感信息处理等评估；
- `make bench`：执行并发请求并统计阶段耗时，用于观察缓存和编排开销。

在没有 GNU Make 的 Windows 环境中，可以直接运行对应 Python 模块：

```powershell
cd backend
python -m eval.run_eval
python -m benchmark.loadtest
```

评估结果受模型版本、知识库内容、网络状态和随机性影响，因此当前结果更适合作为原型对比依据，不应被视为稳定的生产指标。

## 常见问题

### Milvus 连接失败

执行 `docker compose ps`，确认 Milvus、etcd 和 MinIO 已正常启动。Milvus 首次启动较慢，未就绪时执行知识入库会失败。

### 后端无法连接 MySQL 或 Redis

确认 Docker 服务已经启动，并检查 `.env` 与 `docker-compose.yml` 中的端口是否一致：MySQL 为 `3307`，Redis 为 `6380`，Milvus 为 `19531`。

### 模型调用失败

检查 `DASHSCOPE_API_KEY` 是否已填写、账户是否具有可用额度，以及当前网络能否访问模型服务。

### Python 导入 `jose` 时出现语法错误

项目依赖的是 `python-jose`，不是旧版的 `jose` 包。建议在独立虚拟环境中重新安装项目依赖，并通过下面的命令启动后端：

```bash
uvicorn app.main:app --reload
```

不要直接运行 `backend/app/main.py`。

## 当前局限

- 知识库和业务数据均为面向实验的模拟数据，覆盖范围有限；
- 效果依赖外部大模型，尚未完成跨模型和多随机种子的系统性比较；
- 工具调用主要围绕预设业务场景，泛化到其他 API 平台仍需补充适配层；
- 当前只实现文本交互，尚未覆盖图片、语音等多模态输入；
- Docker Compose 仅编排基础设施，前后端仍需在本机单独运行；
- 高风险业务操作只生成工单，没有接入真实生产系统。

## 后续工作

后续可从以下方向继续完善：

1. 扩充真实但经过匿名化处理的故障案例与知识文档；
2. 引入基线方法，对比单 Agent、固定流程和动态多 Agent 的效果与成本；
3. 增加答案正确性、证据一致性、任务完成率和人工接管率等指标；
4. 研究更细粒度的权限控制、提示注入防护和工具调用审计；
5. 补充前后端容器与自动化测试，使实验环境更容易复现。

## 数据与安全说明

仓库中的租户、用户、日志、账单、API Key、邮箱和手机号均为演示或安全测试数据。运行实际数据前应完成匿名化处理，并使用环境变量或密钥管理服务保存凭证。生产部署还需要替换默认数据库密码与 JWT Secret，并补充 HTTPS、访问控制、审计和备份机制。
