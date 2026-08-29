from __future__ import annotations

import asyncio
import hashlib
import io
import tempfile
from pathlib import Path

try:
    from minio import Minio
except ImportError:  # optional production dependency
    Minio = None  # type: ignore

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = self.settings.storage_backend.lower()
        self.settings.storage_path.mkdir(parents=True, exist_ok=True)
        self._minio: Minio | None = None
        if self.backend == "minio":
            if Minio is None:
                raise RuntimeError("STORAGE_BACKEND=minio requires the 'minio' package")
            self._minio = Minio(
                self.settings.minio_endpoint,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_secure,
            )

    async def ensure_ready(self) -> None:
        if not self._minio:
            return
        exists = await asyncio.to_thread(self._minio.bucket_exists, self.settings.minio_bucket)
        if not exists:
            await asyncio.to_thread(self._minio.make_bucket, self.settings.minio_bucket)

    async def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        if self._minio:
            await self.ensure_ready()
            stream = io.BytesIO(data)
            await asyncio.to_thread(
                self._minio.put_object,
                self.settings.minio_bucket,
                key,
                stream,
                len(data),
                content_type,
            )
            return key
        path = self.settings.storage_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def get_bytes(self, key: str) -> bytes:
        if self._minio:
            response = await asyncio.to_thread(self._minio.get_object, self.settings.minio_bucket, key)
            try:
                return await asyncio.to_thread(response.read)
            finally:
                response.close()
                response.release_conn()
        path = self.settings.storage_path / key
        return await asyncio.to_thread(path.read_bytes)

    async def merge_parts(self, destination_key: str, source_keys: list[str]) -> tuple[int, str]:
        """Merge upload parts without materialising the whole file in RAM.

        Returns ``(byte_count, md5_hex)`` for validation by the upload service.
        Local storage writes directly to the destination. MinIO uses a spooled temporary
        file, keeping small uploads in memory and spilling large uploads to disk.
        """
        if self._minio:
            await self.ensure_ready()
            return await asyncio.to_thread(self._merge_minio_parts, destination_key, source_keys)
        return await asyncio.to_thread(self._merge_local_parts, destination_key, source_keys)

    def _merge_local_parts(self, destination_key: str, source_keys: list[str]) -> tuple[int, str]:
        destination = self.settings.storage_path / destination_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.md5()
        total = 0
        with destination.open("wb") as output:
            for key in source_keys:
                source = self.settings.storage_path / key
                with source.open("rb") as input_file:
                    while True:
                        block = input_file.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
                        digest.update(block)
                        total += len(block)
        return total, digest.hexdigest()

    def _merge_minio_parts(self, destination_key: str, source_keys: list[str]) -> tuple[int, str]:
        assert self._minio is not None
        digest = hashlib.md5()
        total = 0
        with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as merged:
            for key in source_keys:
                response = self._minio.get_object(self.settings.minio_bucket, key)
                try:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        merged.write(block)
                        digest.update(block)
                        total += len(block)
                finally:
                    response.close()
                    response.release_conn()
            merged.seek(0)
            self._minio.put_object(
                self.settings.minio_bucket,
                destination_key,
                merged,
                total,
                "application/octet-stream",
            )
        return total, digest.hexdigest()

    async def iter_bytes(self, key: str, chunk_size: int = 1024 * 1024):
        """Stream an object in bounded chunks for downloads/previews."""
        chunk_size = max(64 * 1024, int(chunk_size))
        if self._minio:
            response = await asyncio.to_thread(self._minio.get_object, self.settings.minio_bucket, key)
            try:
                while True:
                    block = await asyncio.to_thread(response.read, chunk_size)
                    if not block:
                        break
                    yield block
            finally:
                response.close()
                response.release_conn()
            return
        path = self.settings.storage_path / key
        handle = await asyncio.to_thread(path.open, "rb")
        try:
            while True:
                block = await asyncio.to_thread(handle.read, chunk_size)
                if not block:
                    break
                yield block
        finally:
            await asyncio.to_thread(handle.close)

    async def delete(self, key: str) -> None:
        if self._minio:
            await asyncio.to_thread(self._minio.remove_object, self.settings.minio_bucket, key)
            return
        path = self.settings.storage_path / key
        if path.exists():
            await asyncio.to_thread(path.unlink)


storage_service = StorageService()
