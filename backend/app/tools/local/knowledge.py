from __future__ import annotations

from sqlalchemy import and_, or_, select

from app.core.access import user_orgs
from app.db.models import DocumentParentChunk, DocumentVector, FileUpload
from app.knowledge.rag import rag_service
from app.knowledge.metadata import metadata_filter_schema, file_metadata
from app.tools.base import BaseTool, ToolExecutionContext


def _access_filter(user, *, include_evaluation_fixtures: bool = False):
    if user.role == "ADMIN":
        permission = True
    else:
        clauses = [
            FileUpload.user_id == str(user.id),
            FileUpload.is_public.is_(True),
        ]
        orgs = sorted(user_orgs(user))
        if orgs:
            clauses.append(FileUpload.org_tag.in_(orgs))
        permission = or_(*clauses)
    # `fixture-*` is a reserved evaluation namespace. No customer-facing Tool
    # may enumerate or read it, even for an administrator using the Demo UI.
    if include_evaluation_fixtures:
        return permission
    return and_(permission, FileUpload.file_name.not_like("fixture-%"))


class SearchKnowledgeTool(BaseTool):
    required_scopes = frozenset({"tools:read"})
    name = "search_knowledge"
    description = (
        "Search the knowledge base that the current user is allowed to access. "
        "Use this when the answer may depend on uploaded documents. Multiple independent searches may be called in parallel."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Self-contained search query."},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 12, "default": 6},
            "filters": metadata_filter_schema(),
        },
        "required": ["query"],
        "additionalProperties": False,
    }
    resource_group = "knowledge-read"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        from app.db.session import SessionLocal

        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        top_k = int(arguments.get("top_k") or 6)
        top_k = max(1, min(12, top_k))
        # Each parallel tool call gets its own AsyncSession. SQLAlchemy AsyncSession
        # is not safe for concurrent use by multiple tasks.
        async with SessionLocal() as db:
            results = await rag_service.search(db, context.user, query, top_k, metadata_filters=arguments.get("filters"))
        return {"query": query, "filters": arguments.get("filters") or {}, "count": len(results), "results": results}


class ListDocumentsTool(BaseTool):
    required_scopes = frozenset({"tools:read"})
    name = "list_documents"
    description = (
        "List documents visible to the current user. Use this to discover file names or fileMd5 values before requesting a document."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "Optional file-name keyword."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        },
        "additionalProperties": False,
    }
    resource_group = "knowledge-read"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        from app.db.session import SessionLocal

        keyword = str(arguments.get("keyword") or "").strip()
        limit = max(1, min(50, int(arguments.get("limit") or 20)))
        stmt = select(FileUpload).where(_access_filter(context.user)).order_by(FileUpload.created_at.desc()).limit(limit)
        if keyword:
            stmt = stmt.where(FileUpload.file_name.ilike(f"%{keyword}%"))
        async with SessionLocal() as db:
            rows = list((await db.scalars(stmt)).all())
        return {
            "count": len(rows),
            "documents": [
                {
                    "fileMd5": item.file_md5,
                    "fileName": item.file_name,
                    "status": item.process_status,
                    "orgTag": item.org_tag,
                    "isPublic": item.is_public,
                    "createdAt": item.created_at.isoformat(),
                    "knowledgeMetadata": file_metadata(item),
                }
                for item in rows
            ],
        }


class GetDocumentTool(BaseTool):
    required_scopes = frozenset({"tools:read"})
    name = "get_document"
    description = (
        "Read text from one accessible knowledge-base document by fileMd5. "
        "Optionally provide chunk_id to focus on the parent context around a known citation."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_md5": {"type": "string", "minLength": 32, "maxLength": 32},
            "chunk_id": {"type": "integer", "minimum": 0},
            "max_chars": {"type": "integer", "minimum": 500, "maximum": 12000, "default": 5000},
        },
        "required": ["file_md5"],
        "additionalProperties": False,
    }
    resource_group = "knowledge-read"

    async def execute(self, context: ToolExecutionContext, arguments: dict):
        from app.db.session import SessionLocal

        file_md5 = str(arguments.get("file_md5") or "").strip().lower()
        if len(file_md5) != 32:
            raise ValueError("file_md5 must be a 32-character MD5")
        max_chars = max(500, min(12000, int(arguments.get("max_chars") or 5000)))
        chunk_id_raw = arguments.get("chunk_id")
        chunk_id = int(chunk_id_raw) if chunk_id_raw is not None else None

        async with SessionLocal() as db:
            file = await db.scalar(
                select(FileUpload)
                .where(FileUpload.file_md5 == file_md5, _access_filter(context.user))
                .order_by(FileUpload.id.desc())
            )
            if not file:
                raise PermissionError("document not found or not accessible")

            if chunk_id is not None:
                child = await db.scalar(
                    select(DocumentVector).where(
                        DocumentVector.file_md5 == file.file_md5,
                        DocumentVector.user_id == file.user_id,
                        DocumentVector.chunk_id == chunk_id,
                        DocumentVector.vector_version == (file.active_vector_version or "legacy"),
                    )
                )
                if not child:
                    raise ValueError("chunk_id not found")
                parent = await db.scalar(
                    select(DocumentParentChunk).where(
                        DocumentParentChunk.file_md5 == file.file_md5,
                        DocumentParentChunk.user_id == file.user_id,
                        DocumentParentChunk.start_chunk_id <= chunk_id,
                        DocumentParentChunk.end_chunk_id >= chunk_id,
                        DocumentParentChunk.vector_version == (file.active_vector_version or "legacy"),
                    )
                )
                text = (parent.text_content if parent else child.text_content)[:max_chars]
                return {
                    "fileMd5": file.file_md5,
                    "fileName": file.file_name,
                    "chunkId": chunk_id,
                    "pageNumber": child.page_number or (parent.page_number if parent else None),
                    "text": text,
                    "knowledgeMetadata": file_metadata(file),
                }

            parents = list(
                (
                    await db.scalars(
                        select(DocumentParentChunk)
                        .where(
                            DocumentParentChunk.file_md5 == file.file_md5,
                            DocumentParentChunk.user_id == file.user_id,
                            DocumentParentChunk.vector_version == (file.active_vector_version or "legacy"),
                        )
                        .order_by(DocumentParentChunk.parent_chunk_id.asc())
                    )
                ).all()
            )
            if parents:
                text = "\n\n".join(item.text_content for item in parents)[:max_chars]
            else:
                children = list(
                    (
                        await db.scalars(
                            select(DocumentVector)
                            .where(DocumentVector.file_md5 == file.file_md5, DocumentVector.user_id == file.user_id, DocumentVector.vector_version == (file.active_vector_version or "legacy"))
                            .order_by(DocumentVector.chunk_id.asc())
                        )
                    ).all()
                )
                text = "\n\n".join(item.text_content for item in children)[:max_chars]
            return {"fileMd5": file.file_md5, "fileName": file.file_name, "text": text, "knowledgeMetadata": file_metadata(file)}
