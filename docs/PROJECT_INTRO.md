# API 助手

API 助手面向 API 开发者，协助查阅文档、排查鉴权与限流问题、核实账单，并在需要时交接人工。

## 当前能力

- FastAPI + WebSocket 提供聊天、知识库、用量与工单接口；Vue 管理台提供对应页面。
- LangGraph 按确定性路由选择 API 诊断、Knowledge、Billing Agent；共享工具调度汇总事实后生成答复，质量门检查无依据主张、引用和安全边界。
- Knowledge 检索 DeepSeek、Qwen、GPT 官方快照。千问编码子块，父块补充上下文，支持过滤、权限复核和版本引用。
- RAG 构建具备任务原子领取、文档租约、不可变修订、条件发布、失败恢复、墓碑删除和定向清理。
- PDF/DOCX 通过独立 Docling 进程解析结构与来源；扫描 OCR 尚未纳入。
- API 诊断走本地受控业务工具；Billing 通过只读 MCP。模拟业务数据必须标注为模拟，不能当作用户真实生产状态。

## 一个问题如何处理

```text
“Qwen 的接口一直 429，怎么办？”
  → 识别产品、错误码和缺失的请求信息
  → 检索对应产品的限流文档
  → 有 request_id 等业务信息时查询当前身份的请求工具
  → 区分通用文档建议和本次请求的已核实事实
  → 生成带来源的答复，经质量门后返回
```

文档能够说明限流规则；确定用户本次失败原因还需要业务证据。多轮诊断已有独立持久状态、证据来源与时间范围，聊天页可以查看进度。已接入请求时观测、候选原因、修正后新请求复查、有限重试与结构化恢复，诊断细分规则限定独立 Demo API。

## 如何理解项目状态

四阶段核心迭代已完成本地与隔离验收，包括固定机制任务、轨迹评分与可复现演示。当前成绩与适用条件统一见[最终验收](04-testing/FINAL_PROJECT_ACCEPTANCE.md)、[第三阶段验收](04-testing/DIAGNOSIS_LOOP_ACCEPTANCE.md)、[第二阶段验收](04-testing/DIAGNOSIS_STATE_ACCEPTANCE.md) 和 [RAG 验收](04-testing/RAG_PHASE_ONE_ACCEPTANCE.md)，不混用旧虚构语料或历史编码的指标。Docker Demo 已原地更新，保留其独立知识库和配置，见[部署验收](04-testing/DOCKER_DEMO_UPGRADE_2026-10-20.md)。

[架构与代码地图](02-architecture/README.md) · [启动指南](01-getting-started/GETTING_STARTED.md) · [四阶段计划](FOUR_PHASE_ITERATION_PLAN.md)
