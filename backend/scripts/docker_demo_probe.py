"""Credential-safe knowledge/config fingerprint; usable before and after migration."""

import asyncio
import hashlib
import json


async def main():
    from sqlalchemy import text
    from app.db.session import engine
    from app.core.config import get_settings
    settings = get_settings()
    async with engine.connect() as db:
        schema = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        groups = {}
        for table, columns, order in (
            ("file_upload", "id,file_md5,user_id,file_name,active_vector_version", "id"),
            ("document_vectors", "vector_id,file_md5,user_id,chunk_id,vector_version,text_content,vector_json", "vector_id"),
            ("document_parent_chunks", "id,file_md5,user_id,vector_version,text_content", "id"),
        ):
            rows = [list(row) for row in (await db.execute(text(f"SELECT {columns} FROM {table} ORDER BY {order}"))).all()]
            groups[table] = {"count": len(rows), "sha256": hashlib.sha256(json.dumps(rows, ensure_ascii=False, default=str).encode()).hexdigest()}
        models = [list(row) for row in (await db.execute(text("SELECT model_version,COUNT(*) FROM document_vectors GROUP BY model_version"))).all()]
    report = {"schema": schema, "knowledge": groups, "vectorModels": models,
        "configuration": {"searchBackend": settings.search_backend, "storageBackend": settings.storage_backend,
            "taskMode": settings.task_mode, "embeddingModel": settings.embedding_model,
            "embeddingDimension": settings.embedding_dimension, "llmModel": settings.llm_model},
        "providerCalls": 0}
    print(json.dumps(report, ensure_ascii=False))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
