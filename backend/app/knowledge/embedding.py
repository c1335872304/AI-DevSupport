from __future__ import annotations

import hashlib
import logging
import re
import time

import httpx
import numpy as np

from app.accounting.embedding_usage import record_embedding_usage
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _console(message: str) -> None:
    print(message, flush=True)


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self.settings.embedding_api_key:
            return await self._remote(texts)
        return [self._local_hash_embedding(text) for text in texts]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]

    async def _remote(self, texts: list[str]) -> list[list[float]]:
        url = self.settings.embedding_base_url.rstrip("/") + "/embeddings"
        headers = {"Authorization": f"Bearer {self.settings.embedding_api_key}"}
        payload = {"model": self.settings.embedding_model, "input": texts}
        # Qwen/DashScope's OpenAI-compatible endpoint supports requesting a
        # smaller output dimension. Keep it aligned with the Elasticsearch
        # dense_vector mapping (256 by default) instead of silently receiving
        # the model default of 1024 dimensions.
        model_name = self.settings.embedding_model.lower()
        if model_name.startswith(("text-embedding-v3", "text-embedding-v4")) or "qwen" in model_name:
            payload["dimensions"] = self.settings.embedding_dimension
            payload["encoding_format"] = "float"
        # DashScope is directly reachable in the local setup. Do not inherit a
        # broken system HTTPS proxy, which otherwise causes ConnectError before
        # the provider can return a useful authentication/model error.
        started = time.monotonic()
        logger.info("[EMBED] request model=%s batch=%d", self.settings.embedding_model, len(texts))
        _console(f"[EMBED] request model={self.settings.embedding_model} batch={len(texts)}")
        try:
            client_kwargs = {"timeout": 90, "trust_env": False}
            if self.settings.embedding_http_proxy:
                client_kwargs["proxy"] = self.settings.embedding_http_proxy
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                payload = response.json()
                record_embedding_usage(payload.get("usage"))
                items = sorted(payload["data"], key=lambda item: item["index"])
                vectors = [item["embedding"] for item in items]
            expected_dimension = self.settings.embedding_dimension
            actual_dimensions = {len(vector) for vector in vectors}
            if actual_dimensions and actual_dimensions != {expected_dimension}:
                raise RuntimeError(
                    "Embedding provider returned dimension(s) "
                    f"{sorted(actual_dimensions)}, expected {expected_dimension}. "
                    "Set EMBEDDING_DIMENSION to the provider dimension and reindex the knowledge base."
                )
            logger.info("[EMBED] success vectors=%d dimension=%d duration_ms=%d", len(vectors), len(vectors[0]) if vectors else 0, int((time.monotonic() - started) * 1000))
            _console(f"[EMBED] success vectors={len(vectors)} dimension={len(vectors[0]) if vectors else 0} duration_ms={int((time.monotonic() - started) * 1000)}")
            return vectors
        except Exception as exc:
            logger.exception("[EMBED] failed duration_ms=%d", int((time.monotonic() - started) * 1000))
            _console(f"[EMBED] failed duration_ms={int((time.monotonic() - started) * 1000)} error={exc}")
            raise

    def _local_hash_embedding(self, text: str) -> list[float]:
        dim = self.settings.embedding_dimension
        vec = np.zeros(dim, dtype=np.float32)
        # Chinese-friendly character ngrams plus ASCII words. Deterministic and dependency-free.
        compact = re.sub(r"\s+", " ", text.lower())
        tokens = re.findall(r"[a-z0-9_]+", compact)
        tokens += [compact[i : i + 2] for i in range(max(0, len(compact) - 1)) if compact[i : i + 2].strip()]
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            n = int.from_bytes(digest, "little")
            idx = n % dim
            sign = -1.0 if (n >> 8) & 1 else 1.0
            vec[idx] += sign
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        if not a or not b:
            return 0.0
        av = np.asarray(a, dtype=np.float32)
        bv = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
        return float(np.dot(av, bv) / denom) if denom else 0.0


embedding_service = EmbeddingService()
