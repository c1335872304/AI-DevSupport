# memory 包初始化文件
# 本包负责 AI-DevSupport 项目的会话记忆功能，包含：
#   - session.py：基于 Redis 的历史消息窗口管理与实体记忆存取
# 其他模块可通过 `from app.memory.session import ...` 直接导入所需函数。
# 此处留空是有意为之，不做统一 re-export，避免引入不必要的依赖。
