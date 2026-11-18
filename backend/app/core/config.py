from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PaiSmart Python"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:9527", "http://127.0.0.1:9527"]

    database_url: str = "sqlite+aiosqlite:///./data/paismart.db"
    database_auto_create_dev: bool = True
    # Run Alembic once from backend/run.py before starting Uvicorn. Keep this
    # opt-in because direct multi-worker Uvicorn launches must migrate in CI/CD.
    database_auto_migrate: bool = False
    refund_preview_enabled: bool = False
    # Legacy environment compatibility only; approval checkpoints now use SQL.
    refund_checkpoint_path: Path = Path("data/refund-checkpoints.sqlite")
    refund_sandbox_url: str = ""

    storage_backend: str = "local"
    local_storage_dir: str = "./data/storage"

    task_mode: str = "background"  # background | kafka
    index_lease_seconds: int = 120
    index_max_attempts: int = 3
    index_gc_retention_seconds: int = 3600
    index_max_active_per_user: int = 2
    docling_python: str = ""
    docling_artifacts_path: str = ""
    document_parse_timeout_seconds: int = 180
    document_parse_max_bytes: int = 25 * 1024 * 1024
    document_parse_max_pages: int = 200
    document_parse_max_memory_mb: int = 2048
    search_backend: str = "database"  # database | elasticsearch

    jwt_secret: str = "change-me-in-production-with-at-least-32-bytes"
    jwt_access_minutes: int = 120
    jwt_refresh_days: int = 14

    bootstrap_admin_enabled: bool = True
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin123"

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False
    memory_history_max: int = 20
    memory_entity_ttl_seconds: int = 21600
    route_cache_ttl_seconds: int = 86400

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "file-processing-topic1"
    kafka_group_id: str = "paismart-python-file-worker"
    kafka_dlq_topic: str = "file-processing-dlq"
    kafka_retry_attempts: int = 3
    kafka_retry_backoff_seconds: float = 2.0

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "uploads"
    minio_secure: bool = False

    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_username: str = ""
    elasticsearch_password: str = ""
    elasticsearch_index: str = "paismart_knowledge"

    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_thinking_enabled: bool | None = None
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_stream_include_usage: bool = True
    llm_request_timeout_seconds: float = 120.0
    llm_max_retries: int = 2
    llm_retry_backoff_seconds: float = 0.5
    llm_circuit_breaker_failures: int = 3
    llm_circuit_breaker_cooldown_seconds: float = 30.0

    # Retrieval query rewriting is deliberately narrower than answer generation:
    # it is only used for entity-backed follow-up questions and never retries.
    rag_query_rewrite_enabled: bool = True
    rag_query_rewrite_max_tokens: int = 160
    rag_query_rewrite_timeout_seconds: float = 8.0
    rag_query_rewrite_cache_seconds: int = 300

    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: int = 256
    embedding_batch_size: int = 10
    # Optional explicit proxy for containers. Leave empty for direct access.
    embedding_http_proxy: str = ""
    elasticsearch_bulk_size: int = 100

    chat_checkpoint_seconds: float = 1.0
    chat_checkpoint_chars: int = 512
    websocket_auth_timeout_seconds: float = 10.0
    conversation_history_messages: int = 20
    conversation_history_chars: int = 12000
    context_system_enabled: bool = True
    context_progress_enabled: bool = False
    context_shadow_enabled: bool = False

    # Agent runtime. A model turn may emit multiple independent tool calls; the
    # runtime executes them concurrently and feeds all results back in one batch.
    agent_max_steps: int = 6
    agent_max_parallel_tools: int = 6
    agent_tool_timeout_seconds: float = 20.0
    agent_tool_result_max_chars: int = 20000
    agent_generation_timeout_seconds: float = 180.0

    # The deterministic three-Agent workflow is the only supported customer
    # service architecture. These limits apply to its shared scheduler.
    agent_max_concurrency: int = 3
    agent_tool_global_concurrency: int = 6
    # A generation has one shared read-Tool budget across all specialists and
    # replanning rounds. This is a hard stop against accidental tool loops.
    agent_max_tool_calls: int = 8
    diagnosis_lease_seconds: int = 240
    diagnosis_step_attempts: int = 2
    diagnosis_turn_attempt_budget: int = 12
    diagnosis_case_attempt_budget: int = 36
    diagnosis_recovery_enabled: bool = True

    # Billing is the only external MCP integration. Its three stable read Tool
    # contracts are query_plan/query_usage/query_bill.
    billing_mcp_enabled: bool = False
    billing_mcp_url: str = ""
    billing_mcp_bearer_token_env: str = "BILLING_MCP_TOKEN"
    billing_mcp_timeout_seconds: float = 30.0

    # Skill layer. Only selected SKILL.md instructions are injected; detailed
    # references/scripts are loaded on demand through controlled tools.
    skills_enabled: bool = True
    skills_semantic_routing_enabled: bool = True
    skills_routing_timeout_seconds: float = 20.0
    skills_dir: str = str(Path(__file__).resolve().parents[2] / "skills")
    skills_max_active: int = 3
    skills_max_instruction_chars: int = 12000
    skills_reference_max_chars: int = 12000
    skills_script_input_max_chars: int = 20000
    skills_script_output_max_chars: int = 20000
    skills_script_timeout_seconds: float = 10.0

    # MCP server/client. Streamable HTTP should use bearer auth; stdio keeps an
    # explicit service user because pipes do not carry HTTP Authorization headers.
    mcp_auth_enabled: bool = True
    mcp_auth_issuer_url: str = "http://127.0.0.1:8000"
    mcp_resource_server_url: str = "http://127.0.0.1:8011/mcp"
    mcp_required_scope: str = "tools:read"

    # Standalone MCP wrapper for the same internal tools. The service user is
    # intentionally explicit; never default an external MCP client to admin.
    mcp_service_username: str = ""

    # Production runtime / accounting / observability.
    llm_minimum_balance_tokens: int = 1
    rate_limit_register_max: int = 20
    rate_limit_register_window_seconds: int = 600
    rate_limit_login_max: int = 30
    rate_limit_login_window_seconds: int = 60
    rate_limit_chat_max: int = 20
    rate_limit_chat_window_seconds: int = 60
    chat_max_input_chars: int = 8000
    chat_max_connections_per_user: int = 3
    chat_connection_ttl_seconds: int = 7200
    privacy_history_retention_days: int = 180
    privacy_trace_retention_days: int = 90
    privacy_auto_maintenance_enabled: bool = True
    privacy_maintenance_interval_seconds: int = 86400
    langfuse_enabled: bool = True
    langfuse_base_url: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: SecretStr = SecretStr("")

    # Parent-child RAG: child chunks are embedded/searched; parent chunks are used as answer context.
    parent_chunk_size: int = 1800
    chunk_size: int = 600
    chunk_overlap: int = 100
    min_chunk_size: int = 120
    top_k: int = 6
    rag_candidate_multiplier: int = 6
    rag_context_char_budget: int = 12000
    rag_parent_context_max_chars: int = 2600
    rag_max_results_per_file: int = 4

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def storage_path(self) -> Path:
        return Path(self.local_storage_dir).expanduser().resolve()

    @property
    def skills_path(self) -> Path:
        return Path(self.skills_dir).expanduser().resolve()

    def validate_runtime_safety(self) -> None:
        if self.app_env.lower() not in {"prod", "production"}:
            return
        if self.jwt_secret.startswith("change-me-in-production") or len(self.jwt_secret) < 32:
            raise RuntimeError("Production requires a non-default JWT_SECRET of at least 32 characters")
        if self.bootstrap_admin_enabled and self.bootstrap_admin_password == "admin123":
            raise RuntimeError("Production must change BOOTSTRAP_ADMIN_PASSWORD or disable BOOTSTRAP_ADMIN_ENABLED")
        if not self.redis_enabled:
            raise RuntimeError("Production requires REDIS_ENABLED=true for distributed rate limits and WebSocket limits")
        if self.billing_mcp_enabled and not self.billing_mcp_url.strip():
            raise RuntimeError("Production BILLING_MCP_ENABLED=true requires BILLING_MCP_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
