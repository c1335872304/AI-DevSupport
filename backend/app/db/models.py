from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.time import utcnow


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="USER")
    org_tags: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    primary_org: Mapped[str | None] = mapped_column(String(255), nullable=True)
    llm_token_balance: Mapped[int] = mapped_column(BigInteger, default=10000)
    embedding_token_balance: Mapped[int] = mapped_column(BigInteger, default=10000)
    token_version: Mapped[int] = mapped_column(Integer, default=0)


class OrganizationTag(Base, TimestampMixin):
    __tablename__ = "organization_tags"
    tag_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_max_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer)


class FileUpload(Base):
    __tablename__ = "file_upload"
    __table_args__ = (UniqueConstraint("file_md5", "user_id", name="uk_file_upload_md5_user"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_md5: Mapped[str] = mapped_column(String(32), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    total_size: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[int] = mapped_column(Integer, default=0)  # 0 uploading, 1 completed, 2 merging
    process_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    process_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    org_tag: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    estimated_embedding_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    estimated_chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_embedding_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    actual_chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active_vector_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Customer-service knowledge metadata. These fields live on the document and are
    # denormalized into Elasticsearch chunks at index time for pre-retrieval filtering.
    knowledge_category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_product: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_region: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_channel: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    knowledge_version: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_error_code: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_plan: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)


class ChunkInfo(Base):
    __tablename__ = "chunk_info"
    __table_args__ = (UniqueConstraint("file_md5", "user_id", "chunk_index", name="uk_file_md5_user_chunk_index"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_md5: Mapped[str] = mapped_column(String(32), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_md5: Mapped[str] = mapped_column(String(32))
    storage_path: Mapped[str] = mapped_column(String(1000))
    user_id: Mapped[str] = mapped_column(String(64), default="")


class DocumentParentChunk(Base):
    __tablename__ = "document_parent_chunks"
    __table_args__ = (
        UniqueConstraint("file_md5", "user_id", "vector_version", "parent_chunk_id", name="uk_parent_chunk_file_user_ver_id"),
        Index("ix_parent_chunk_file_user_range", "file_md5", "user_id", "start_chunk_id", "end_chunk_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_md5: Mapped[str] = mapped_column(String(32), index=True)
    parent_chunk_id: Mapped[int] = mapped_column(Integer)
    vector_version: Mapped[str] = mapped_column(String(64), default="legacy", index=True)
    text_content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_chunk_id: Mapped[int] = mapped_column(Integer)
    end_chunk_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    org_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)


class DocumentVector(Base):
    __tablename__ = "document_vectors"
    vector_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_md5: Mapped[str] = mapped_column(String(32), index=True)
    chunk_id: Mapped[int] = mapped_column(Integer)
    vector_version: Mapped[str] = mapped_column(String(64), default="legacy", index=True)
    text_content: Mapped[str] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchor_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    org_tag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    vector_json: Mapped[str] = mapped_column(Text)


class ConversationSession(Base, TimestampMixin):
    __tablename__ = "conversation_sessions"
    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Structured entities remembered across turns, e.g. request_id/app_id/error_code.
    # This preserves the legacy supervisor's entity memory without requiring Redis.
    collected_entities_json: Mapped[str] = mapped_column(Text, default="{}")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reference_mappings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class GenerationState(Base):
    __tablename__ = "generation_states"
    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    reference_mappings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class LLMTokenReservation(Base):
    __tablename__ = "llm_token_reservations"
    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    reserved_tokens: Mapped[int] = mapped_column(BigInteger)
    settled_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="RESERVED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class InviteCode(Base, TimestampMixin):
    __tablename__ = "invite_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RechargePackage(Base, TimestampMixin):
    __tablename__ = "recharge_packages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    package_name: Mapped[str] = mapped_column(String(128))
    package_price: Mapped[int] = mapped_column(BigInteger)
    package_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_token: Mapped[int] = mapped_column(BigInteger, default=0)
    embedding_token: Mapped[int] = mapped_column(BigInteger, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)


class RechargeOrder(Base, TimestampMixin):
    __tablename__ = "recharge_orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_no: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    package_id: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[int] = mapped_column(BigInteger)
    llm_token: Mapped[int] = mapped_column(BigInteger, default=0)
    embedding_token: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(20), default="NOT_PAY")
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class UserTokenRecord(Base):
    __tablename__ = "user_token_record"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    record_date: Mapped[date] = mapped_column(Date, default=date.today)
    token_type: Mapped[str] = mapped_column(String(20))
    change_type: Mapped[str] = mapped_column(String(20))
    request_count: Mapped[int] = mapped_column(BigInteger, default=0)
    amount: Mapped[int] = mapped_column(BigInteger)
    balance_before: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    balance_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    generation_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    rating: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    generation_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    active_skills_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ToolExecution(Base):
    __tablename__ = "tool_executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    generation_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_call_id: Mapped[str] = mapped_column(String(128), index=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True)
    step: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arguments_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RateLimitPolicy(Base, TimestampMixin):
    __tablename__ = "rate_limit_policies"
    scope: Mapped[str] = mapped_column(String(64), primary_key=True)
    max_requests: Mapped[int] = mapped_column(Integer)
    window_seconds: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class MCPAccessToken(Base, TimestampMixin):
    __tablename__ = "mcp_access_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    scopes: Mapped[str] = mapped_column(String(1000), default="tools:read")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SupportHandoff(Base):
    __tablename__ = "support_handoffs"
    handoff_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    category: Mapped[str] = mapped_column(String(64), default="GENERAL", index=True)
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", index=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    reason: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(20), default="AI")
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SupportApplication(Base):
    __tablename__ = "support_applications"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(128))
    product: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SupportApiKey(Base):
    __tablename__ = "support_api_keys"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    app_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    key_masked: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SupportApiCallLog(Base):
    __tablename__ = "support_api_call_logs"
    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    app_id: Mapped[str] = mapped_column(String(64), index=True)
    api_key_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(255), index=True)
    http_status: Mapped[int] = mapped_column(Integer, index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class SupportErrorCode(Base):
    __tablename__ = "support_error_codes"
    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    http_status: Mapped[int] = mapped_column(Integer)
    cause: Mapped[str] = mapped_column(Text)
    fix_steps: Mapped[str] = mapped_column(Text)


class SupportPlan(Base):
    __tablename__ = "support_plans"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    qps_limit: Mapped[int] = mapped_column(Integer)
    monthly_quota: Mapped[int] = mapped_column(Integer)
    base_price: Mapped[float] = mapped_column(Float, default=0.0)
    overage_price_per_call: Mapped[float] = mapped_column(Float, default=0.0)


class SupportSubscription(Base):
    __tablename__ = "support_subscriptions"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class SupportUsageRecord(Base):
    __tablename__ = "support_usage_records"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uk_support_usage_user_month"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    overage_count: Mapped[int] = mapped_column(Integer, default=0)


class SupportInvoice(Base):
    __tablename__ = "support_invoices"
    __table_args__ = (UniqueConstraint("user_id", "month", name="uk_support_invoice_user_month"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    items_json: Mapped[str] = mapped_column(Text, default="{}")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="ISSUED")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
