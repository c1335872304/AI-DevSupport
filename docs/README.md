# PaiSmart 文档导航

PaiSmart 当前定位是 **LangGraph AI 客服 Agent**。这套文档只描述当前客服架构，不保留历史版本演进说明。

| 文档 | 解决什么问题 |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | AI 客服整体架构、目录职责、依赖方向、主请求流 |
| [GETTING_STARTED.md](GETTING_STARTED.md) | 最小模式和完整基础设施模式如何运行 |
| [AGENT_AND_SKILLS.md](AGENT_AND_SKILLS.md) | 客服 Agent、三个 Skill、Tool、并行执行、MCP |
| [KNOWLEDGE_PIPELINE.md](KNOWLEDGE_PIPELINE.md) | 客服知识库、文档入库、版本化索引和 RAG |
| [EVALUATION.md](EVALUATION.md) | 如何评测客服路由、排障、人工升级和最终回答质量 |
| [PRODUCTION.md](PRODUCTION.md) | 数据库迁移、人工工单、MCP Auth、Kafka、监控与生产边界 |

第一次读代码推荐：

```text
README
  -> ARCHITECTURE
  -> AGENT_AND_SKILLS
  -> KNOWLEDGE_PIPELINE
```
