from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.mysql import DATETIME as MysqlDateTime

from app.core.time import utcnow


class Base(DeclarativeBase):
    pass


class IndexBuild(Base):
    __tablename__ = "index_builds"
    build_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, index=True)
    owner: Mapped[str] = mapped_column(String(64))
    epoch: Mapped[int] = mapped_column(Integer)
    input_revision: Mapped[int] = mapped_column(Integer)
    revision_id: Mapped[str] = mapped_column(String(64))
    profile_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="BUILDING", index=True)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}")
    completed_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DocumentRevision(Base):
    __tablename__ = "document_revisions"
    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(1000))
    metadata_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class IndexOutbox(Base):
    __tablename__ = "index_outbox"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class EmbeddingAttempt(Base):
    __tablename__ = "embedding_attempts"
    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    build_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_start: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="STARTED")
    provider_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    provider_request_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    settled_tokens: Mapped[int] = mapped_column(BigInteger, default=0)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


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
    source_md5: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_source_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    active_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    write_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    input_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    desired_metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Customer-service knowledge metadata. These fields live on the document and are
    # denormalized into Elasticsearch chunks at index time for pre-retrieval filtering.
    knowledge_category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_product: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_region: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_channel: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    knowledge_effective_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    knowledge_effective_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    knowledge_superseded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
    location_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    location_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class ConversationContextState(Base):
    __tablename__ = "conversation_context_states"
    conversation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("conversation_sessions.conversation_id", ondelete="CASCADE"), primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    last_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)


class DiagnosisSession(Base, TimestampMixin):
    __tablename__ = "diagnosis_sessions"
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow, onupdate=utcnow)
    diagnosis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    app_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="COLLECTING")
    symptom: Mapped[str] = mapped_column(Text)
    entities_json: Mapped[str] = mapped_column(Text, default="{}")
    entity_sources_json: Mapped[str] = mapped_column(Text, default="{}")
    candidates_json: Mapped[str] = mapped_column(Text, default="[]")
    missing_fields_json: Mapped[str] = mapped_column(Text, default="[]")
    next_action: Mapped[str] = mapped_column(String(500), default="补充脱敏请求信息")
    end_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_generation_id: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    workflow_json: Mapped[str] = mapped_column(Text, default="{}", server_default=text("('{}')"))


class DiagnosisExecution(Base):
    __tablename__ = "diagnosis_executions"
    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), nullable=True)
    epoch: Mapped[int] = mapped_column(Integer, default=0)
    attempts_used: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow, onupdate=utcnow)


class DiagnosisStep(Base):
    __tablename__ = "diagnosis_steps"
    step_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), index=True)
    generation_id: Mapped[str] = mapped_column(String(64), index=True)
    tool_name: Mapped[str] = mapped_column(String(64))
    arguments_json: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow, onupdate=utcnow)


class DiagnosisTurn(Base):
    __tablename__ = "diagnosis_turns"
    generation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), index=True)
    finished: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)


class DiagnosisEvidence(Base):
    __tablename__ = "diagnosis_evidence"
    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), index=True)
    generation_id: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)


class DiagnosisTransition(Base):
    __tablename__ = "diagnosis_transitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[str] = mapped_column(String(64), index=True)
    generation_id: Mapped[str] = mapped_column(String(64))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(255))
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow)


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
    diagnosis_id: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime().with_variant(MysqlDateTime(fsp=6), "mysql"), default=utcnow, index=True)


class SupportRequestObservation(Base):
    """Sanitized at-call instrumentation for the separate Demo API service."""
    __tablename__ = "support_request_observations"
    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    service_id: Mapped[str] = mapped_column(String(64), default="demo-api")
    rule_version: Mapped[str] = mapped_column(String(64), default="2026-10-v1")
    observations_json: Mapped[str] = mapped_column(Text, default="{}")


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


class RefundApprovalPreview(Base, TimestampMixin):
    __tablename__ = "refund_approval_previews"
    __table_args__ = (UniqueConstraint("user_id", "request_key", name="uq_refund_preview_user_key"),)

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    handoff_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    closure_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    request_key: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(500))
    decision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RefundSandboxIntent(Base):
    __tablename__ = "refund_sandbox_intents"

    request_id: Mapped[str] = mapped_column(
        ForeignKey("refund_approval_previews.request_id", ondelete="CASCADE"), primary_key=True,
    )
    payment_id: Mapped[str] = mapped_column(String(64))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    refund_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (Index("uq_processing_request_key", "request_key", unique=True),)
    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, index=True)
    input_revision: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    request_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApprovalCheckpoint(Base):
    __tablename__ = "approval_checkpoints"
    thread_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    value_json: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text)


class ApprovalWrite(Base):
    __tablename__ = "approval_writes"
    thread_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_ns: Mapped[str] = mapped_column(String(128), primary_key=True)
    checkpoint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    idx: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String(128))
    value_json: Mapped[str] = mapped_column(Text)


class ApprovalExecution(Base, TimestampMixin):
    __tablename__ = "approval_executions"
    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: utcnow() - timedelta(seconds=1))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class SupportHandoffAudit(Base):
    __tablename__ = "support_handoff_audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    handoff_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32))
    before_json: Mapped[str] = mapped_column(Text)
    after_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ProviderAttempt(Base, TimestampMixin):
    __tablename__ = "provider_attempts"
    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    generation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="IN_FLIGHT", index=True)
    prompt_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reconciled_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProviderReconciliation(Base):
    __tablename__ = "provider_reconciliations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(String(64), unique=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    evidence_ref: Mapped[str] = mapped_column(String(500))
    statement_hash: Mapped[str] = mapped_column(String(64), unique=True)
    receipt_key: Mapped[str] = mapped_column(String(64), unique=True)
    before_json: Mapped[str] = mapped_column(Text)
    after_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UserRoleAudit(Base):
    __tablename__ = "user_role_audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(64))
    previous_role: Mapped[str] = mapped_column(String(20))
    new_role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
