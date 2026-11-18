# A 阶段生产图离线验收

2026-11-17 · 冻结用例单题通过 **60/60**，成对通过 **30/30**，执行错误 **0**。同一评分器重算改动前结果为 26/60、3/30。两轮均使用同一套工具夹具，模型用量为 0。发布验收见 [生产就绪规划](PRODUCTION_READINESS_PLAN.md)。

## 当前入口

评测脚本使用冻结指纹加载 48 条固定回归和 12 条发布比较用例，运行生产图并保存逐题的最终答复、公开事件、工具调用记录和分层评分。

在 `backend` 目录运行以下离线复测。输出须使用新文件名。

```powershell
python -c "import os, runpy, sys; os.environ.update(LLM_API_KEY='', BILLING_MCP_ENABLED='false', REDIS_ENABLED='false', LANGFUSE_ENABLED='false'); sys.argv=['scripts/run_phase_a_graph.py', 'data/phase-a/offline-rerun.jsonl', '--offline']; runpy.run_path(sys.argv[0], run_name='__main__')"
```

[冻结清单](../../backend/eval/customer_service/phase_a_manifest.json) · [执行脚本](../../backend/scripts/run_phase_a_graph.py) · [最终逐题记录](../../backend/data/phase-a/production-graph-offline-final-v2.jsonl) · [最终日志](../../backend/data/phase-a/production-graph-offline-final-v2.log)

## 隔离 Docker 端到端抽验

从六类冻结用例各取一对。使用独立 Docker 容器和 SQLite 数据库，通过正式 HTTP 登录、会话接口和 `/chat` WebSocket 发起请求。检索、引用读取、套餐查询和工单写入均使用应用实现。固定向量由容器内回环接口提供，答复使用离线生成路径，容器禁用外网。工单失败侧在隔离数据库内注入写入失败，通过工单查询接口核对落库结果。

首轮自动评分通过后，逐条检查发现个人状态答复缺少明确的证据边界，普通工单失败提示误提及退款。修复后用新容器和全新数据库复测，**12/12 条、6/6 对通过**。验收校验了公开流式正文与持久化答复一致、引用出处可读取，以及成功工单与本次生成关联。修复后全量离线回归仍为 **60/60、30/30**。真实模型、线上依赖配置和 Langfuse 追踪由发布验收覆盖。

[Docker 验收脚本](../../backend/scripts/run_phase_a_docker_acceptance.py) · [首轮逐题记录](../../backend/data/phase-a/docker-e2e-first.jsonl) · [Docker 复测记录](../../backend/data/phase-a/docker-e2e-retest.jsonl) · [全量回归日志](../../backend/data/phase-a/production-graph-offline-post-docker.log)

## 历史存档

首版模型夹具评测、Docker 抽验和离线中间对照存放在历史目录。复核前后差异时使用改动前的逐题记录和现行评分器。

[历史基线](history/PHASE_A_QUALITY_BASELINE_2026-11-17.md) · [历史原始记录](../../backend/data/history/phase-a/) · [改动前逐题记录](../../backend/data/history/phase-a/production-graph-offline-retest.jsonl)
