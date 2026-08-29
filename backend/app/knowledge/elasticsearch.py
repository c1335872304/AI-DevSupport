from __future__ import annotations

from collections import defaultdict

try:
    from elasticsearch import AsyncElasticsearch, NotFoundError
except ImportError:  # optional production dependency
    AsyncElasticsearch = None  # type: ignore

    class NotFoundError(Exception):
        pass

from app.core.config import get_settings
from app.core.access import user_orgs
from app.db.models import User
from app.knowledge.metadata import ES_FIELD_MAP, normalize_metadata


class ElasticsearchService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client: AsyncElasticsearch | None = None
        if self.settings.search_backend.lower() == "elasticsearch":
            if AsyncElasticsearch is None:
                raise RuntimeError("SEARCH_BACKEND=elasticsearch requires the 'elasticsearch' package")
            kwargs = {}
            if self.settings.elasticsearch_username:
                kwargs["basic_auth"] = (
                    self.settings.elasticsearch_username,
                    self.settings.elasticsearch_password,
                )
            self.client = AsyncElasticsearch(self.settings.elasticsearch_url, **kwargs)

    async def ensure_index(self) -> None:
        if not self.client:
            return
        index = self.settings.elasticsearch_index
        if await self.client.indices.exists(index=index):
            mapping = await self.client.indices.get_mapping(index=index)
            index_mapping = mapping.get(index, {}).get("mappings", {}).get("properties", {})
            required = {
                "indexVersion": {"type": "keyword"},
                "category": {"type": "keyword"},
                "product": {"type": "keyword"},
                "region": {"type": "keyword"},
                "channel": {"type": "keyword"},
                "effectiveDate": {"type": "date", "format": "strict_date_optional_time||yyyy-MM-dd"},
                "knowledgeVersion": {"type": "keyword"},
                "errorCode": {"type": "keyword"},
                "plan": {"type": "keyword"},
            }
            missing = {name: mapping for name, mapping in required.items() if name not in index_mapping}
            version_mapping = index_mapping.get("indexVersion")
            if version_mapping is not None and version_mapping.get("type") != "keyword":
                raise RuntimeError(
                    "Elasticsearch field indexVersion must be keyword. Recreate/reindex the knowledge index before enabling versioned retrieval."
                )
            if missing:
                await self.client.indices.put_mapping(index=index, properties=missing)
            return
        await self.client.indices.create(
            index=index,
            mappings={
                "properties": {
                    "fileMd5": {"type": "keyword"},
                    "fileName": {"type": "keyword"},
                    "chunkId": {"type": "integer"},
                    "parentChunkId": {"type": "integer"},
                    "indexVersion": {"type": "keyword"},
                    "textContent": {"type": "text"},
                    "pageNumber": {"type": "integer"},
                    "anchorText": {"type": "text"},
                    "userId": {"type": "keyword"},
                    "orgTag": {"type": "keyword"},
                    "isPublic": {"type": "boolean"},
                    "category": {"type": "keyword"},
                    "product": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "channel": {"type": "keyword"},
                    "effectiveDate": {"type": "date", "format": "strict_date_optional_time||yyyy-MM-dd"},
                    "knowledgeVersion": {"type": "keyword"},
                    "errorCode": {"type": "keyword"},
                    "plan": {"type": "keyword"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": self.settings.embedding_dimension,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        )

    @staticmethod
    def _document_id(document: dict) -> str:
        return f"{document['userId']}:{document['fileMd5']}:{document.get('indexVersion', 'legacy')}:{document['chunkId']}"

    async def index_chunk(self, document: dict) -> None:
        # Backward-compatible single-document API. New ingestion code should use bulk_index().
        await self.bulk_index([document])

    async def bulk_index(self, documents: list[dict], *, refresh: bool = False) -> None:
        if not self.client or not documents:
            return
        await self.ensure_index()
        operations: list[dict] = []
        for document in documents:
            operations.append(
                {
                    "index": {
                        "_index": self.settings.elasticsearch_index,
                        "_id": self._document_id(document),
                    }
                }
            )
            operations.append(document)

        response = await self.client.bulk(operations=operations, refresh=refresh)
        if not response.get("errors"):
            return

        failures = []
        for item in response.get("items", []):
            action = item.get("index") or item.get("create") or item.get("update") or {}
            error = action.get("error")
            if error:
                failures.append(f"{action.get('_id', '?')}: {error}")
            if len(failures) >= 5:
                break
        details = "; ".join(failures) if failures else "unknown bulk indexing error"
        raise RuntimeError(f"Elasticsearch bulk indexing failed: {details}")

    async def verify_version(self, file_md5: str, user_id: str, version: str, expected_count: int) -> None:
        if not self.client:
            return
        await self.ensure_index()
        # Bulk indexing deliberately avoids refresh on every batch. Refresh exactly once
        # before verification so near-real-time visibility cannot produce a false rollback.
        await self.client.indices.refresh(index=self.settings.elasticsearch_index)
        response = await self.client.count(
            index=self.settings.elasticsearch_index,
            query={"bool": {"filter": [
                {"term": {"fileMd5": file_md5}},
                {"term": {"userId": user_id}},
                {"term": {"indexVersion": version}},
            ]}},
        )
        actual = int(response.get("count") or 0)
        if actual != expected_count:
            raise RuntimeError(f"Elasticsearch version verification failed: expected {expected_count}, got {actual}")

    async def delete_version(self, file_md5: str, user_id: str, version: str) -> None:
        if not self.client:
            return
        try:
            await self.client.delete_by_query(
                index=self.settings.elasticsearch_index,
                query={"bool": {"filter": [
                    {"term": {"fileMd5": file_md5}},
                    {"term": {"userId": user_id}},
                    {"term": {"indexVersion": version}},
                ]}},
                conflicts="proceed", refresh=False,
            )
        except NotFoundError:
            return

    async def delete_other_versions(self, file_md5: str, user_id: str, active_version: str) -> None:
        if not self.client:
            return
        try:
            await self.client.delete_by_query(
                index=self.settings.elasticsearch_index,
                query={"bool": {"filter": [
                    {"term": {"fileMd5": file_md5}},
                    {"term": {"userId": user_id}},
                    {"bool": {"must_not": [{"term": {"indexVersion": active_version}}]}},
                ]}},
                conflicts="proceed", refresh=False,
            )
        except NotFoundError:
            return

    async def delete_stale_chunks(self, file_md5: str, user_id: str, chunk_count: int) -> None:
        """Delete chunks left behind when a reprocessed file now has fewer chunks.

        New chunks are indexed first, so the previous searchable copy remains available if
        bulk indexing fails. Cleanup runs only after the new set has been successfully sent.
        """
        if not self.client:
            return
        try:
            await self.client.delete_by_query(
                index=self.settings.elasticsearch_index,
                query={
                    "bool": {
                        "filter": [
                            {"term": {"fileMd5": file_md5}},
                            {"term": {"userId": user_id}},
                            {"range": {"chunkId": {"gte": chunk_count}}},
                        ]
                    }
                },
                conflicts="proceed",
                refresh=False,
            )
        except NotFoundError:
            return

    async def delete_file(self, file_md5: str, user_id: str | None = None) -> None:
        if not self.client:
            return
        try:
            filters = [{"term": {"fileMd5": file_md5}}]
            if user_id is not None:
                filters.append({"term": {"userId": user_id}})
            await self.client.delete_by_query(
                index=self.settings.elasticsearch_index,
                query={"bool": {"filter": filters}},
                conflicts="proceed",
                refresh=True,
            )
        except NotFoundError:
            return

    def _permission_filter(self, user: User) -> dict:
        should = [
            {"term": {"userId": str(user.id)}},
            {"term": {"isPublic": True}},
        ]
        orgs = sorted(user_orgs(user))
        if orgs:
            should.append({"terms": {"orgTag": orgs}})
        if user.role == "ADMIN":
            return {"match_all": {}}
        return {"bool": {"should": should, "minimum_should_match": 1}}

    @staticmethod
    def _metadata_filter(raw: dict | None) -> list[dict]:
        metadata = normalize_metadata(raw)
        filters: list[dict] = []
        for public_name, es_name in ES_FIELD_MAP.items():
            value = metadata.get(public_name)
            if value is None:
                continue
            if isinstance(value, list):
                filters.append({"terms": {es_name: value}})
            else:
                filters.append({"term": {es_name: value}})
        effective_at = metadata.get("effective_at")
        if effective_at:
            filters.append({"range": {"effectiveDate": {"lte": effective_at.isoformat()}}})
        return filters

    async def search(self, user: User, query: str, query_vector: list[float], top_k: int, metadata_filters: dict | None = None) -> list[dict]:
        if not self.client:
            return []
        await self.ensure_index()
        index = self.settings.elasticsearch_index
        permission = self._permission_filter(user)
        metadata_filter = self._metadata_filter(metadata_filters)
        combined_filter = {"bool": {"filter": [permission, *metadata_filter]}} if metadata_filter else permission
        recall = max(top_k * 3, 30)

        semantic = await self.client.search(
            index=index,
            size=recall,
            knn={
                "field": "vector",
                "query_vector": query_vector,
                "k": recall,
                "num_candidates": max(recall * 4, 100),
                "filter": combined_filter,
            },
            source=[
                "fileMd5",
                "fileName",
                "chunkId",
                "parentChunkId",
                "indexVersion",
                "textContent",
                "pageNumber",
                "anchorText",
                "orgTag",
                "isPublic",
                "userId",
                "category",
                "product",
                "region",
                "channel",
                "effectiveDate",
                "knowledgeVersion",
                "errorCode",
                "plan",
            ],
        )
        lexical = await self.client.search(
            index=index,
            size=recall,
            query={
                "bool": {
                    "must": [{"match": {"textContent": {"query": query}}}],
                    "filter": [permission, *metadata_filter],
                }
            },
            source=[
                "fileMd5",
                "fileName",
                "chunkId",
                "parentChunkId",
                "indexVersion",
                "textContent",
                "pageNumber",
                "anchorText",
                "orgTag",
                "isPublic",
                "userId",
                "category",
                "product",
                "region",
                "channel",
                "effectiveDate",
                "knowledgeVersion",
                "errorCode",
                "plan",
            ],
        )

        # Reciprocal Rank Fusion: semantic and lexical recall remain independent. Keep the
        # channel ranks/scores as internal features for the post-retrieval reranker.
        fused: dict[str, float] = defaultdict(float)
        docs: dict[str, dict] = {}
        signals: dict[str, dict] = defaultdict(dict)
        for channel, weight, result in (("semantic", 1.0, semantic), ("lexical", 0.8, lexical)):
            for rank, hit in enumerate(result["hits"]["hits"], start=1):
                doc_id = hit["_id"]
                fused[doc_id] += weight / (60 + rank)
                docs[doc_id] = hit["_source"]
                signals[doc_id][f"{channel}Rank"] = rank
                signals[doc_id][f"{channel}Score"] = float(hit.get("_score") or 0.0)
        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]
        output: list[dict] = []
        for doc_id, score in ranked:
            source = dict(docs[doc_id])
            source["ownerUserId"] = source.pop("userId", None)
            output.append({"score": score, **signals[doc_id], **source})
        return output

    async def close(self) -> None:
        if self.client:
            await self.client.close()


elasticsearch_service = ElasticsearchService()
