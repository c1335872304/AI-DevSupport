# API 助手文档

API 助手用于 API 文档问答、鉴权与限流诊断、只读账单核实及人工交接。聊天使用 FastAPI / WebSocket 与 LangGraph，管理界面使用 Vue。DeepSeek、Qwen、GPT 官方快照用于通用知识，账号事实由授权业务工具核实。

## 日常阅读

| 文档 | 用途 |
| --- | --- |
| [本页](README.md) | 项目能力、当前交付与阅读入口 |
| [开发](DEVELOPMENT.md) | 环境、配置、启动、Git 与提交 |
| [架构](ARCHITECTURE.md) | 数据流、模块职责、状态与授权契约 |
| [运维](OPERATIONS.md) | Docker、知识库、诊断恢复、追踪和排障 |
| [测试](TESTING.md) | 本地检查、演示、CI 与评测产物 |
| [发布](RELEASING.md) | 候选验证、迁移、回滚、放量及审批配置 |
| [维护](MAINTENANCE.md) | 六项剩余技术债务及后续功能范围 |

## 当前交付

四阶段核心、持久化上下文、会话显式绑定、生成心跳回收与结算保护、管理员审批恢复均已有对应验证。源码基线 `99e7485` 的范围与成绩见[候选验收](archive/reports/RELEASE_CANDIDATE_ACCEPTANCE_2026-11-19.md)。后续文档整理沿用该代码基线。项目交付在 [PR #1](https://github.com/c1335872304/AI-DevSupport/pull/1)，运行镜像与目标环境状态按[发布手册](RELEASING.md)核对。

当前退款执行使用合成支付沙箱，关闭工单操作更新原业务记录。PDF/DOCX 使用独立 Docling 环境，扫描 OCR、截图输入和真实支付接入由维护台账跟踪。

## 归档

- [历史索引](archive/README.md)按设计、报告、进度和早期记录查阅，保留原版本、失败和复测条件。
- [产物索引](artifacts/README.md)收录逐题回答和截图，并说明生成脚本与原始运行数据位置。
- 详细实现和运维资料分别合并为[实现快照](archive/reference/IMPLEMENTATION_2026-11-19.md)与[运维快照](archive/reference/OPERATIONS_2026-11-19.md)，用于追溯原契约和操作背景。

`docs/` 根目录维护这七份日常手册。新结果写入归档或产物目录，日常手册同步有效操作和当前边界。脚本的专门参数见[脚本说明](../backend/scripts/README.md)。
