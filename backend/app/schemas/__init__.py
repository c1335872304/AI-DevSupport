"""schemas 包初始化文件。

本包集中定义 AI-DevSupport 系统中所有 API 的请求和响应数据结构（DTO），
使用 Pydantic BaseModel 提供自动的数据验证、序列化和 OpenAPI 文档生成能力。
包含以下两个子模块：
  - auth：认证相关 DTO，包含 LoginRequest、UserInfo、TokenResponse。
  - chat：对话和工单相关 DTO，包含 ChatRequest、FeedbackRequest、TicketUpdateRequest。

各 schema 类可在路由层通过 `from app.schemas.auth import LoginRequest` 等方式直接导入。
本 __init__.py 仅作包标识，不做额外导出。
"""
