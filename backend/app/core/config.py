from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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

    storage_backend: str = "local"
    local_storage_dir: str = "./data/storage"

    task_mode: str = "background"  # background | kafka
    search_backend: str = "database"  # database | elasticsearch

    jwt_secret: str = "change-me-in-production-with-at-least-32-bytes"
    jwt_access_minutes: int = 120
    jwt_refresh_days: int = 14

    bootstrap_admin_enabled: bool = True
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin123"

    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = False

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
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_stream_include_usage: bool = True

    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: int = 256
    embedding_batch_size: int = 10
    elasticsearch_bulk_size: int = 100

    chat_checkpoint_seconds: float = 1.0
    chat_checkpoint_chars: int = 512
    websocket_auth_timeout_seconds: float = 10.0
    conversation_history_messages: int = 8
    conversation_history_chars: int = 6000

    # Agent runtime. A model turn may emit multiple independent tool calls; the
    # runtime executes them concurrently and feeds all results back in one batch.
    agent_enabled: bool = True
    agent_max_steps: int = 6
    agent_max_parallel_tools: int = 6
    agent_tool_timeout_seconds: float = 20.0
    agent_tool_result_max_chars: int = 20000

    # Skill layer. Only selected SKILL.md instructions are injected; detailed
    # references/scripts are loaded on demand through controlled tools.
    skills_enabled: bool = True
    skills_dir: str = str(Path(__file__).resolve().parents[2] / "skills")
    skills_max_active: int = 2
    skills_max_instruction_chars: int = 12000
    skills_reference_max_chars: int = 12000
    skills_script_input_max_chars: int = 20000
    skills_script_output_max_chars: int = 20000

    # MCP server/client. Streamable HTTP should use bearer auth; stdio keeps an
    # explicit service user because pipes do not carry HTTP Authorization headers.
    mcp_auth_enabled: bool = True
    mcp_auth_issuer_url: str = "http://127.0.0.1:8000"
    mcp_resource_server_url: str = "http://127.0.0.1:8011/mcp"
    mcp_required_scope: str = "tools:read"
    mcp_remote_servers_json: str = "{}"

    # Business Tool backend. "local" uses PaiSmart demo/domain tables. "mcp" keeps
    # the same stable Tool names while delegating execution to a configured remote MCP
    # business service, so Agent/Skill/LangGraph code does not change.
    business_tool_backend: str = "local"  # local | mcp
    business_mcp_server: str = ""
    business_mcp_tool_map_json: str = "{}"
    business_mcp_default_user_argument: str = "customer_id"

    # Standalone MCP wrapper for the same internal tools. The service user is
    # intentionally explicit; never default an external MCP client to admin.
    mcp_service_username: str = ""

    # Production runtime / accounting / observability.
    agent_trace_persist_enabled: bool = True
    llm_minimum_balance_tokens: int = 1
    rate_limit_register_max: int = 20
    rate_limit_register_window_seconds: int = 600
    rate_limit_login_max: int = 30
    rate_limit_login_window_seconds: int = 60
    metrics_enabled: bool = True
    otel_enabled: bool = False
    otel_service_name: str = "paismart-backend"
    otel_exporter_otlp_endpoint: str = ""

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

    @field_validator("business_tool_backend")
    @classmethod
    def validate_business_tool_backend(cls, value: str) -> str:
        normalized = str(value or "local").strip().lower()
        if normalized not in {"local", "mcp"}:
            raise ValueError("BUSINESS_TOOL_BACKEND must be local or mcp")
        return normalized

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
        if self.business_tool_backend == "mcp" and not self.business_mcp_server.strip():
            raise RuntimeError("Production BUSINESS_TOOL_BACKEND=mcp requires BUSINESS_MCP_SERVER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
