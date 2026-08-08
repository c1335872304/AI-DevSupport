# observability 包初始化文件
# 本包负责 AI-DevSupport 项目的可观测性功能，包含：
#   - cost.py：Token 用量统计，按会话与租户记录每次 LLM 调用的 token 消耗，
#              供成本看板汇总查询使用。
#   - trace.py：Agent 编排链路追踪，逐节点记录耗时/token/命中文档/状态，
#              落库后可还原完整调用链，便于排查问题与性能分析。
# 使用方：直接从子模块导入，如 `from app.observability.cost import record`。
