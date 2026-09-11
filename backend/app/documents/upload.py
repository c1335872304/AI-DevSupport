from __future__ import annotations

import hashlib
import re
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import user_orgs
from app.core.time import utcnow
from app.db.models import ChunkInfo, FileUpload, OrganizationTag, User
from app.documents.storage import storage_service
from app.knowledge.metadata import apply_metadata_to_file

_MD5_RE = re.compile(r"^[0-9a-fA-F]{32}$")


class UploadService:
    @staticmethod
    def _normalize_md5(value: str, label: str = "MD5") -> str:
        value = (value or "").strip()
        if not _MD5_RE.fullmatch(value):
            raise ValueError(f"Invalid {label}")
        return value.lower()

    @staticmethod
    def _safe_file_name(file_name: str) -> str:
        # Browsers normally send only the basename, but never trust it for filesystem keys.
        normalized = (file_name or "").replace("\\", "/").split("/")[-1].strip()
        if not normalized or normalized in {".", ".."}:
            raise ValueError("Invalid file name")
        if len(normalized) > 255:
            raise ValueError("File name is too long")
        return normalized

    async def save_chunk(
        self,
        db: AsyncSession,
        user: User,
        file_md5: str,
        file_name: str,
        chunk_index: int,
        total_chunks: int,
        total_size: int,
        chunk_bytes: bytes,
        chunk_md5: str | None,
        org_tag: str | None,
        is_public: bool,
        knowledge_metadata: dict | None = None,
    ) -> dict:
        file_md5 = self._normalize_md5(file_md5, "file MD5")
        file_name = self._safe_file_name(file_name)
        if chunk_index < 0 or total_chunks <= 0 or chunk_index >= total_chunks:
            raise ValueError("Invalid chunk index")
        if total_size < 0:
            raise ValueError("Invalid total file size")

        resolved_org_tag = org_tag or user.primary_org
        if user.role != "ADMIN" and resolved_org_tag and resolved_org_tag not in user_orgs(user):
            raise PermissionError("No permission for this organization")

        if resolved_org_tag:
            org = await db.get(OrganizationTag, resolved_org_tag)
            if org and org.upload_max_size_bytes and total_size > org.upload_max_size_bytes:
                raise ValueError(
                    f"File exceeds organization upload limit ({org.upload_max_size_bytes} bytes)"
                )

        actual_md5 = hashlib.md5(chunk_bytes).hexdigest()
        if chunk_md5 and self._normalize_md5(chunk_md5, "chunk MD5") != actual_md5:
            raise ValueError("Chunk MD5 mismatch")

        upload = await db.scalar(
            select(FileUpload).where(FileUpload.file_md5 == file_md5, FileUpload.user_id == str(user.id))
        )
        if not upload:
            upload = FileUpload(
                file_md5=file_md5,
                file_name=file_name,
                total_size=total_size,
                status=0,
                user_id=str(user.id),
                org_tag=resolved_org_tag,
                is_public=is_public,
            )
            apply_metadata_to_file(upload, knowledge_metadata)
            db.add(upload)
            await db.flush()
        else:
            upload.file_name = file_name or upload.file_name
            upload.total_size = total_size or upload.total_size
            if org_tag is not None:
                upload.org_tag = resolved_org_tag
            upload.is_public = is_public
            if knowledge_metadata:
                apply_metadata_to_file(upload, knowledge_metadata)

        key = f"chunks/{user.id}/{file_md5}/{chunk_index:08d}.part"
        await storage_service.put_bytes(key, chunk_bytes)
        existing = await db.scalar(
            select(ChunkInfo).where(
                ChunkInfo.file_md5 == file_md5,
                ChunkInfo.user_id == str(user.id),
                ChunkInfo.chunk_index == chunk_index,
            )
        )
        if existing:
            existing.chunk_md5 = actual_md5
            existing.storage_path = key
            existing.user_id = str(user.id)
        else:
            db.add(
                ChunkInfo(
                    file_md5=file_md5,
                    chunk_index=chunk_index,
                    chunk_md5=actual_md5,
                    storage_path=key,
                    user_id=str(user.id),
                )
            )
        await db.commit()
        uploaded = await db.scalar(
            select(func.count(ChunkInfo.id)).where(
                ChunkInfo.file_md5 == file_md5,
                ChunkInfo.user_id == str(user.id),
            )
        )
        return {"uploadedChunks": int(uploaded or 0), "totalChunks": total_chunks, "chunkIndex": chunk_index}

    async def status(self, db: AsyncSession, user: User, file_md5: str) -> dict:
        file_md5 = self._normalize_md5(file_md5, "file MD5")
        upload = await db.scalar(
            select(FileUpload).where(FileUpload.file_md5 == file_md5, FileUpload.user_id == str(user.id))
        )
        chunks = list(
            (
                await db.scalars(
                    select(ChunkInfo).where(
                        ChunkInfo.file_md5 == file_md5,
                        ChunkInfo.user_id == str(user.id),
                    )
                )
            ).all()
        )
        return {
            "fileMd5": file_md5,
            "exists": upload is not None,
            "status": upload.status if upload else 0,
            "processStatus": upload.process_status if upload else None,
            "uploadedChunks": sorted([c.chunk_index for c in chunks]),
        }

    async def merge(self, db: AsyncSession, user: User, file_md5: str) -> FileUpload:
        file_md5 = self._normalize_md5(file_md5, "file MD5")
        upload = await db.scalar(
            select(FileUpload).where(FileUpload.file_md5 == file_md5, FileUpload.user_id == str(user.id))
        )
        if not upload:
            raise ValueError("Upload not found")
        upload.file_name = self._safe_file_name(upload.file_name)
        upload.status = 2
        await db.commit()
        chunks = list(
            (
                await db.scalars(
                    select(ChunkInfo)
                    .where(ChunkInfo.file_md5 == file_md5, ChunkInfo.user_id == str(user.id))
                    .order_by(ChunkInfo.chunk_index)
                )
            ).all()
        )
        if not chunks:
            raise ValueError("No chunks found")

        # Reject incomplete/non-contiguous uploads before doing expensive storage I/O.
        expected_chunks = max(1, (upload.total_size + (5 * 1024 * 1024) - 1) // (5 * 1024 * 1024))
        actual_indexes = [chunk.chunk_index for chunk in chunks]
        if actual_indexes != list(range(expected_chunks)):
            raise ValueError("Upload chunks are incomplete")

        key = f"uploads/{user.id}/{file_md5}/{upload.file_name}"
        merged_size, merged_md5 = await storage_service.merge_parts(
            key, [chunk.storage_path for chunk in chunks]
        )
        if upload.total_size and merged_size != upload.total_size:
            # Browser-reported size can be 0 in some clients; only validate positive values.
            await storage_service.delete(key)
            raise ValueError(f"Merged file size mismatch: expected {upload.total_size}, got {merged_size}")
        if merged_md5 != file_md5:
            await storage_service.delete(key)
            raise ValueError("Merged file MD5 mismatch")
        upload.storage_key = key
        upload.status = 1
        upload.merged_at = utcnow()
        upload.process_status = "PENDING"
        await db.commit()
        for chunk in chunks:
            await storage_service.delete(chunk.storage_path)
        await db.execute(
            delete(ChunkInfo).where(ChunkInfo.file_md5 == file_md5, ChunkInfo.user_id == str(user.id))
        )
        await db.commit()
        return upload


upload_service = UploadService()
