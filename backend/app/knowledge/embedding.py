from __future__ import annotations

import hashlib
import math
import re

import httpx
import numpy as np

from app.core.config import get_settings
from app.accounting.embedding_usage import record_embedding_usage


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
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            payload = response.json()
            record_embedding_usage(payload.get("usage"))
            items = sorted(payload["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in items]

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
