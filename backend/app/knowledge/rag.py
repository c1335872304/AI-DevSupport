from __future__ import annotations

import heapq
import json
import math
import re
from collections import Counter, defaultdict

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import user_orgs
from app.core.config import get_settings
from app.db.models import DocumentParentChunk, DocumentVector, FileUpload, User
from app.knowledge.embedding import embedding_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.metadata import SCALAR_FIELDS, normalize_metadata, file_metadata
from app.knowledge.reranker import reranker_service


class RagService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def search(self, db: AsyncSession, user: User, query: str, top_k: int | None = None, metadata_filters: dict | None = None) -> list[dict]:
        top_k = top_k or self.settings.top_k
        candidate_k = max(top_k, top_k * max(1, self.settings.rag_candidate_multiplier))
        if self.settings.search_backend.lower() == "elasticsearch":
            qvec = await embedding_service.embed_one(query)
            raw_candidates = await elasticsearch_service.search(user, query, qvec, max(candidate_k * 2, candidate_k), metadata_filters=metadata_filters)
            candidates = await self._filter_active_versions(db, raw_candidates, candidate_k)
        else:
            candidates = await self._search_database(db, user, query, candidate_k, metadata_filters=metadata_filters)

        reranked = reranker_service.rerank(query, candidates, candidate_k)
        return await self._expand_parent_context(db, reranked, top_k)


    async def _filter_active_versions(self, db: AsyncSession, candidates: list[dict], limit: int) -> list[dict]:
        """Use the DB active-version pointer as the cross-store source of truth.

        Elasticsearch may temporarily contain old and newly-built versions at the same
        time. Filtering candidates against FileUpload.active_vector_version makes the
        logical switch atomic even though DB and ES cannot share one transaction.
        """
        if not candidates:
            return []
        pairs = {(str(item.get("fileMd5") or ""), str(item.get("ownerUserId") or "")) for item in candidates}
        pairs.discard(("", ""))
        if not pairs:
            return candidates[:limit]
        clauses = [and_(FileUpload.file_md5 == md5, FileUpload.user_id == owner) for md5, owner in pairs]
        rows = list((await db.scalars(select(FileUpload).where(or_(*clauses)))).all())
        active = {(row.file_md5, row.user_id): (row.active_vector_version or "legacy") for row in rows}
        output = []
        for item in candidates:
            key = (str(item.get("fileMd5") or ""), str(item.get("ownerUserId") or ""))
            if str(item.get("indexVersion") or "legacy") != active.get(key, "legacy"):
                continue
            output.append(item)
            if len(output) >= limit:
                break
        return output

    async def _search_database(self, db: AsyncSession, user: User, query: str, top_k: int, metadata_filters: dict | None = None) -> list[dict]:
        """Exact fallback search for small installations.

        Permissions are applied in SQL; rows are streamed; only a bounded candidate heap is
        retained. Large installations should use Elasticsearch ANN retrieval.
        """
        permission = self._database_permission_filter(user)
        metadata = normalize_metadata(metadata_filters)
        metadata_clauses = []
        for public_name, column_name in SCALAR_FIELDS.items():
            value = metadata.get(public_name)
            if value is None:
                continue
            column = getattr(FileUpload, column_name)
            metadata_clauses.append(column.in_(value) if isinstance(value, list) else column == value)
        if metadata.get("effective_at"):
            metadata_clauses.append(FileUpload.knowledge_effective_date <= metadata["effective_at"])
        stmt = (
            select(DocumentVector, FileUpload)
            .join(
                FileUpload,
                and_(
                    FileUpload.file_md5 == DocumentVector.file_md5,
                    FileUpload.user_id == DocumentVector.user_id,
                ),
            )
            .where(
                permission,
                *metadata_clauses,
                or_(
                    FileUpload.active_vector_version == DocumentVector.vector_version,
                    and_(FileUpload.active_vector_version.is_(None), DocumentVector.vector_version == "legacy"),
                ),
            )
            .execution_options(yield_per=256)
        )

        qvec = await embedding_service.embed_one(query)
        query_terms = self._terms(query)
        heap: list[tuple[float, int, DocumentVector, str]] = []

        result = await db.stream(stmt)
        async for row, file_row in result:
            try:
                vec = json.loads(row.vector_json)
            except (TypeError, ValueError, json.JSONDecodeError):
                vec = []
            semantic = embedding_service.cosine(qvec, vec)
            lexical = self._lexical_score(query_terms, self._terms(row.text_content))
            score = semantic * 0.75 + lexical * 0.25
            item = (float(score), row.vector_id, row, file_row)
            if len(heap) < top_k:
                heapq.heappush(heap, item)
            elif item[:2] > heap[0][:2]:
                heapq.heapreplace(heap, item)

        ranked = sorted(heap, key=lambda item: (item[0], item[1]), reverse=True)
        return [
            {
                "score": round(score, 6),
                "fileMd5": row.file_md5,
                "fileName": file_row.file_name,
                "chunkId": row.chunk_id,
                "indexVersion": row.vector_version,
                "textContent": row.text_content,
                "pageNumber": row.page_number,
                "anchorText": row.anchor_text,
                "orgTag": row.org_tag,
                "isPublic": row.is_public,
                "ownerUserId": row.user_id,
                **{
                    "category": file_metadata(file_row).get("category"),
                    "product": file_metadata(file_row).get("product"),
                    "region": file_metadata(file_row).get("region"),
                    "channel": file_metadata(file_row).get("channel"),
                    "effectiveDate": file_metadata(file_row).get("effective_date"),
                    "knowledgeVersion": file_metadata(file_row).get("version"),
                    "errorCode": file_metadata(file_row).get("error_code"),
                    "plan": file_metadata(file_row).get("plan"),
                },
            }
            for score, _, row, file_row in ranked
        ]

    async def _expand_parent_context(self, db: AsyncSession, candidates: list[dict], top_k: int) -> list[dict]:
        """Replace matched child text with its parent context while preserving child citation.

        Multiple child hits from the same parent collapse to one context. Old indexed data
        without parent metadata gracefully falls back to the child text.
        """
        if not candidates:
            return []

        parent_lookup: dict[tuple[str, str, int], DocumentParentChunk] = {}
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for item in candidates:
            file_md5 = str(item.get("fileMd5") or "")
            owner = str(item.get("ownerUserId") or "")
            if file_md5 and owner:
                groups[(file_md5, owner)].append(item)

        for (file_md5, owner), items in groups.items():
            explicit_parent_ids = {
                int(item["parentChunkId"])
                for item in items
                if item.get("parentChunkId") is not None
            }
            child_ids = {
                int(item["chunkId"])
                for item in items
                if item.get("chunkId") is not None and item.get("parentChunkId") is None
            }
            matchers = []
            if explicit_parent_ids:
                matchers.append(DocumentParentChunk.parent_chunk_id.in_(explicit_parent_ids))
            for child_id in child_ids:
                matchers.append(
                    and_(
                        DocumentParentChunk.start_chunk_id <= child_id,
                        DocumentParentChunk.end_chunk_id >= child_id,
                    )
                )
            if not matchers:
                continue
            rows = list(
                (
                    await db.scalars(
                        select(DocumentParentChunk).where(
                            DocumentParentChunk.file_md5 == file_md5,
                            DocumentParentChunk.user_id == owner,
                            DocumentParentChunk.vector_version == str(items[0].get("indexVersion") or "legacy"),
                            or_(*matchers),
                        )
                    )
                ).all()
            )
            for row in rows:
                parent_lookup[(file_md5, owner, row.parent_chunk_id)] = row

        selected: list[dict] = []
        seen_contexts: set[tuple] = set()
        char_budget = max(1000, self.settings.rag_context_char_budget)
        parent_max_chars = max(500, self.settings.rag_parent_context_max_chars)
        used_chars = 0

        for item in candidates:
            file_md5 = str(item.get("fileMd5") or "")
            owner = str(item.get("ownerUserId") or "")
            chunk_id = int(item.get("chunkId") or 0)
            parent_id = item.get("parentChunkId")
            parent: DocumentParentChunk | None = None
            if parent_id is not None:
                parent = parent_lookup.get((file_md5, owner, int(parent_id)))
            if parent is None and file_md5 and owner:
                # Resolve parent by the persisted child-id range for DB results / old ES docs.
                for (fmd5, fowner, _), candidate_parent in parent_lookup.items():
                    if fmd5 == file_md5 and fowner == owner and candidate_parent.start_chunk_id <= chunk_id <= candidate_parent.end_chunk_id:
                        parent = candidate_parent
                        break

            context_key = (
                owner,
                file_md5,
                "parent" if parent else "child",
                parent.parent_chunk_id if parent else chunk_id,
            )
            if context_key in seen_contexts:
                continue

            enriched = dict(item)
            matched_child = str(item.get("textContent") or "")
            enriched["matchedChunkText"] = matched_child
            if parent:
                context_text = parent.text_content[:parent_max_chars]
                enriched["textContent"] = context_text
                enriched["parentChunkId"] = parent.parent_chunk_id
                enriched["contextType"] = "PARENT"
                if not enriched.get("pageNumber"):
                    enriched["pageNumber"] = parent.page_number
            else:
                context_text = matched_child
                enriched["contextType"] = "CHILD"

            remaining = char_budget - used_chars
            if remaining <= 0:
                break
            if len(context_text) > remaining:
                if selected:
                    break
                context_text = context_text[:remaining]
                enriched["textContent"] = context_text
            used_chars += len(context_text)
            seen_contexts.add(context_key)

            # ownerUserId and raw channel ranks are internal retrieval details, not API fields.
            enriched.pop("ownerUserId", None)
            enriched.pop("semanticRank", None)
            enriched.pop("semanticScore", None)
            enriched.pop("lexicalRank", None)
            enriched.pop("lexicalScore", None)
            selected.append(enriched)
            if len(selected) >= top_k:
                break
        return selected

    @staticmethod
    def _database_permission_filter(user: User):
        if user.role == "ADMIN":
            return True
        clauses = [
            FileUpload.user_id == str(user.id),
            FileUpload.is_public.is_(True),
        ]
        orgs = sorted(user_orgs(user))
        if orgs:
            clauses.append(FileUpload.org_tag.in_(orgs))
        return or_(*clauses)

    @staticmethod
    def _terms(text: str) -> Counter[str]:
        normalized = re.sub(r"\s+", "", text.lower())
        chinese_bigrams = [normalized[i : i + 2] for i in range(max(0, len(normalized) - 1))]
        ascii_terms = re.findall(r"[a-z0-9_]+", text.lower())
        return Counter(chinese_bigrams + ascii_terms)

    @staticmethod
    def _lexical_score(q: Counter[str], d: Counter[str]) -> float:
        if not q or not d:
            return 0.0
        overlap = sum(min(q[k], d[k]) for k in q.keys() & d.keys())
        denom = math.sqrt(sum(q.values()) * sum(d.values()))
        return overlap / denom if denom else 0.0


rag_service = RagService()
