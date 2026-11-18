from __future__ import annotations

import heapq
import json
import logging
import math
import re
import time
from collections import Counter, defaultdict

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import user_orgs
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import DocumentParentChunk, DocumentVector, FileUpload, User
from app.knowledge.embedding import embedding_service
from app.knowledge.elasticsearch import elasticsearch_service
from app.knowledge.metadata import SCALAR_FIELDS, TEXT_FALLBACK_FIELDS, file_metadata, metadata_matches, normalize_metadata
from app.knowledge.reranker import reranker_service
from app.knowledge.product_scope import ProductScopeConflict, scoped_filters

logger = logging.getLogger(__name__)


def _console(message: str) -> None:
    print(message, flush=True)


class RagService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def search_evidence(self, db, user, query, top_k=None, metadata_filters=None):
        """Structured contract for agents; low-level search keeps list compatibility."""
        try:
            metadata_filters = scoped_filters(query,metadata_filters)
            results = await self.search(db, user, query, top_k, metadata_filters)
        except ProductScopeConflict:
            return {"status":"NEEDS_CLARIFICATION","results":[],"count":0,
                    "missingFields":["product"],"conflicts":[],"warnings":["product_scope_conflict"]}
        except Exception as exc:
            logger.warning("RAG backend unavailable: %s", type(exc).__name__)
            return {"status": "BACKEND_UNAVAILABLE", "results": [], "count": 0,
                    "missingFields": [], "conflicts": [], "warnings": [type(exc).__name__]}
        products = {r.get("product") for r in results if r.get("product")}
        versions = defaultdict(set)
        for result in results:
            if result.get("knowledgeVersion"):
                versions[result.get("product")].add(result["knowledgeVersion"])
        missing, conflicts = [], []
        status = "OK" if results else "NO_EVIDENCE"
        if len(products) > 1 and not (metadata_filters or {}).get("product") and not re.search(
            r"deepseek|qwen|千问|gpt|openai|比较|对比|分别|区别", query, re.I):
            status, missing = "NEEDS_CLARIFICATION", ["product"]
        if any(len(v) > 1 for v in versions.values()) and not (metadata_filters or {}).get("version"):
            status = "NEEDS_CLARIFICATION"
            missing.append("version")
            conflicts = [{"product": p, "versions": sorted(v), "reason": "multiple applicable versions"}
                         for p, v in versions.items() if len(v) > 1]
        # Optional, explicit source annotations support reproducible rule
        # disagreement checks without inventing semantic certainty from prose.
        # They are untrusted claims, never executable instructions or facts.
        claims = defaultdict(lambda: defaultdict(list))
        for result in results:
            scope = (result.get("product"), result.get("knowledgeVersion"), result.get("region"))
            text = str(result.get("matchedChunkText") or result.get("textContent") or "")
            for key, value in re.findall(r"(?:^|\n)rag-claim:\s*([\w.:-]{1,128})\s*=\s*([^\n]{1,256})", text):
                claims[(*scope, key)][value.strip()].append(result.get("citationId") or result.get("fileName"))
        for scope, values in claims.items():
            if len(values) > 1:
                status = "CONFLICT"
                conflicts.append({"product": scope[0], "version": scope[1], "region": scope[2],
                    "claim": scope[3], "reason": "declared_claim_disagreement",
                    "alternatives": [{"value": v, "sources": ids} for v, ids in values.items()]})
        filters = normalize_metadata(metadata_filters)
        warnings = [
            f"{field}_matched_in_text"
            for field, result_key in (("error_code", "errorCode"), ("plan", "plan"))
            if field in filters and any(not result.get(result_key) for result in results)
        ]
        return {"status": status, "results": results, "count": len(results),
                "missingFields": missing, "conflicts": conflicts, "warnings": warnings}

    async def search(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        top_k: int | None = None,
        metadata_filters: dict | None = None,
        *,
        include_evaluation_fixtures: bool = False,
    ) -> list[dict]:
        started = time.monotonic()
        try:
            metadata_filters = scoped_filters(query,metadata_filters)
        except ProductScopeConflict:
            return []
        top_k = top_k or self.settings.top_k
        candidate_k = max(top_k, top_k * max(1, self.settings.rag_candidate_multiplier))
        if self.settings.search_backend.lower() == "elasticsearch":
            qvec = await embedding_service.embed_one(query)
            raw_candidates = await elasticsearch_service.search(
                user,
                query,
                qvec,
                max(candidate_k * 2, candidate_k),
                metadata_filters=metadata_filters,
                include_evaluation_fixtures=include_evaluation_fixtures,
            )
            candidates = await self._filter_active_versions(db, raw_candidates, candidate_k, user, metadata_filters)
            # Bounded refill when stale versions consumed the initial ES window.
            if len(candidates) < top_k:
                raw_candidates = await elasticsearch_service.search(user, query, qvec,
                    candidate_k * 6, metadata_filters=metadata_filters,
                    include_evaluation_fixtures=include_evaluation_fixtures)
                candidates = await self._filter_active_versions(db, raw_candidates, candidate_k, user, metadata_filters)
        else:
            candidates = await self._search_database(
                db,
                user,
                query,
                candidate_k,
                metadata_filters=metadata_filters,
                include_evaluation_fixtures=include_evaluation_fixtures,
            )

        candidates = await self._filter_active_versions(db, candidates, candidate_k, user, metadata_filters)
        reranked = reranker_service.rerank(query, candidates, candidate_k)
        reranked = await self._filter_active_versions(db, reranked, candidate_k, user, metadata_filters)
        output = await self._expand_parent_context(db, reranked, top_k)
        output = await self._filter_active_versions(db, output, top_k, user, metadata_filters)
        for item in output:
            item.pop("ownerUserId", None)
        logger.info("[RAG] search user=%s backend=%s candidates=%d results=%d duration_ms=%d", user.id, self.settings.search_backend, len(candidates), len(output), int((time.monotonic() - started) * 1000))
        _console(f"[RAG] search backend={self.settings.search_backend} candidates={len(candidates)} results={len(output)} duration_ms={int((time.monotonic() - started) * 1000)}")
        return output


    async def _filter_active_versions(self, db: AsyncSession, candidates: list[dict], limit: int,
                                      user: User, metadata_filters=None) -> list[dict]:
        from app.documents.coordination import session_factory
        # A fresh short transaction avoids reusing an earlier MySQL REPEATABLE
        # READ snapshot after a concurrent ACL or active-version change.
        async with session_factory(db)() as authorization_db:
            return await self._validate_active_versions(authorization_db, candidates, limit, user, metadata_filters)

    async def _validate_active_versions(self, db, candidates, limit, user, metadata_filters=None):
        """Use the DB active-version pointer as the cross-store source of truth.

        Elasticsearch may temporarily contain old and newly-built versions at the same
        time. Filtering candidates against FileUpload.active_vector_version makes the
        logical switch atomic even though DB and ES cannot share one transaction.
        """
        if not candidates:
            return []
        current_identity = await db.scalar(select(User).where(User.id == user.id).execution_options(populate_existing=True))
        if current_identity is None:
            return []
        user = current_identity
        pairs = {(str(item.get("fileMd5") or ""), str(item.get("ownerUserId") or "")) for item in candidates}
        pairs.discard(("", ""))
        if not pairs:
            return []
        clauses = [and_(FileUpload.file_md5 == md5, FileUpload.user_id == owner) for md5, owner in pairs]
        rows = list((await db.scalars(select(FileUpload).where(or_(*clauses),
            FileUpload.deleted_at.is_(None), self._database_permission_filter(user))
            .execution_options(populate_existing=True))).all())
        active = {(row.file_md5, row.user_id): (row.active_vector_version or "legacy") for row in rows}
        files = {(row.file_md5, row.user_id): row for row in rows}
        filters = normalize_metadata(metadata_filters)
        effective_at = filters.get("effective_at") or (None if filters.get("version") else utcnow().date())
        output = []
        for item in candidates:
            key = (str(item.get("fileMd5") or ""), str(item.get("ownerUserId") or ""))
            if key not in active or str(item.get("indexVersion") or "legacy") != active[key]:
                continue
            metadata = file_metadata(files[key])
            text = str(item.get("matchedChunkText") or item.get("textContent") or "")
            if any(not metadata_matches(metadata.get(k), v, k, text)
                   for k, v in filters.items() if k in SCALAR_FIELDS):
                continue
            if filters.get("effective_at") and (not files[key].knowledge_effective_date or
                    files[key].knowledge_effective_date > filters["effective_at"]):
                continue
            if filters.get("effective_at") and files[key].knowledge_effective_until and files[key].knowledge_effective_until <= filters["effective_at"]:
                continue
            if effective_at and ((files[key].knowledge_effective_date and files[key].knowledge_effective_date > effective_at)
                    or (files[key].knowledge_effective_until and files[key].knowledge_effective_until <= effective_at)):
                continue
            if "error_code" in filters:
                item["errorCode"] = metadata.get("error_code")
            if "plan" in filters:
                item["plan"] = metadata.get("plan")
            output.append(item)
            if len(output) >= limit:
                break
        return output

    async def _search_database(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        top_k: int,
        metadata_filters: dict | None = None,
        *,
        include_evaluation_fixtures: bool = False,
    ) -> list[dict]:
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
            clause = column.in_(value) if isinstance(value, list) else column == value
            if public_name in TEXT_FALLBACK_FIELDS:
                clause = or_(clause, column.is_(None), column == "")
            metadata_clauses.append(clause)
        text_filters = {key: value for key, value in metadata.items() if key in TEXT_FALLBACK_FIELDS}
        if metadata.get("effective_at"):
            metadata_clauses.append(FileUpload.knowledge_effective_date <= metadata["effective_at"])
            metadata_clauses.append(or_(FileUpload.knowledge_effective_until.is_(None),
                                       FileUpload.knowledge_effective_until > metadata["effective_at"]))
        elif not metadata.get("version"):
            today = utcnow().date()
            metadata_clauses.extend([or_(FileUpload.knowledge_effective_date.is_(None), FileUpload.knowledge_effective_date <= today),
                                    or_(FileUpload.knowledge_effective_until.is_(None), FileUpload.knowledge_effective_until > today)])
        if not include_evaluation_fixtures:
            metadata_clauses.append(FileUpload.file_name.not_like("fixture-%"))
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
                FileUpload.deleted_at.is_(None),
                DocumentVector.model_version == self.settings.embedding_model,
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
            if any(not metadata_matches(getattr(file_row, SCALAR_FIELDS[key]), value, key, row.text_content)
                   for key, value in text_filters.items()):
                continue
            try:
                vec = json.loads(row.vector_json)
            except (TypeError, ValueError, json.JSONDecodeError):
                vec = []
            if len(vec) != self.settings.embedding_dimension:
                # Same-sized vectors from different models are already excluded in SQL;
                # obsolete dimensions also require reindexing, never synthetic conversion.
                continue
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
                "fileName": file_row.active_file_name or file_row.file_name,
                "chunkId": row.chunk_id,
                "indexVersion": row.vector_version,
                "textContent": row.text_content,
                "pageNumber": row.page_number,
                "anchorText": row.anchor_text,
                "sourceLocation": json.loads(row.location_json) if row.location_json else None,
                "orgTag": row.org_tag,
                "isPublic": row.is_public,
                "ownerUserId": row.user_id,
                **{
                    "category": file_metadata(file_row).get("category"),
                    "product": file_metadata(file_row).get("product"),
                    "region": file_metadata(file_row).get("region"),
                    "channel": file_metadata(file_row).get("channel"),
                    "effectiveDate": file_metadata(file_row).get("effective_date"),
                    "effectiveUntil": file_metadata(file_row).get("effective_until"),
                    "supersededBy": file_metadata(file_row).get("superseded_by"),
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
            enriched["evidenceType"] = "DOCUMENT_RULE"
            # Opaque signed identity binds the citation to its exact build and owner.
            from app.knowledge.citations import issue_citation
            enriched["citationId"] = issue_citation(owner, file_md5, str(item.get("indexVersion") or "legacy"), chunk_id)
            if parent:
                context_text = parent.text_content[:parent_max_chars]
                if parent.location_json and not enriched.get("sourceLocation"):
                    enriched["sourceLocation"] = json.loads(parent.location_json)
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
