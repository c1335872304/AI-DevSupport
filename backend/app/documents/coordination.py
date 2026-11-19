"""Durable document leases and monotonic fencing epochs."""

import uuid
from dataclasses import dataclass
from datetime import timedelta
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.core.config import get_settings
from app.db.models import FileUpload, User


class IndexBusy(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentLease:
    file_id: int
    owner: str
    epoch: int
    input_revision: int


async def database_now(db):
    return await db.scalar(select(func.current_timestamp()))


def lease_predicate(lease):
    return (
        FileUpload.id == lease.file_id,
        FileUpload.lease_owner == lease.owner,
        FileUpload.write_epoch == lease.epoch,
        FileUpload.input_revision == lease.input_revision,
        FileUpload.deleted_at.is_(None),
        FileUpload.lease_until > func.current_timestamp(),
    )


async def claim_document(sessions, file_id):
    settings = get_settings()
    async with sessions() as db:
        file = await db.get(FileUpload, file_id)
        if not file or file.deleted_at is not None or not file.storage_key:
            return None
        await db.execute(select(User.id).where(User.id == int(file.user_id)).with_for_update())
        now = await database_now(db)
        active = await db.scalar(
            select(func.count())
            .select_from(FileUpload)
            .where(
                FileUpload.user_id == file.user_id,
                FileUpload.lease_until > now,
                FileUpload.deleted_at.is_(None),
            )
        )
        if active >= max(1, settings.index_max_active_per_user):
            raise IndexBusy("Owner indexing concurrency limit reached")
        owner = uuid.uuid4().hex
        result = await db.execute(
            update(FileUpload)
            .where(
                FileUpload.id == file_id,
                FileUpload.deleted_at.is_(None),
                or_(FileUpload.lease_until.is_(None), FileUpload.lease_until <= now),
            )
            .values(
                lease_owner=owner,
                lease_until=now + timedelta(seconds=max(3, settings.index_lease_seconds)),
                write_epoch=FileUpload.write_epoch + 1,
                process_status="PROCESSING",
                process_error=None,
            )
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise IndexBusy("Document already has a live indexing lease")
        await db.refresh(file)
        lease = DocumentLease(file_id, owner, file.write_epoch, file.input_revision)
        await db.commit()
        return lease


async def renew_document(sessions, lease):
    async with sessions() as db:
        now = await database_now(db)
        result = await db.execute(
            update(FileUpload)
            .where(*lease_predicate(lease))
            .values(lease_until=now + timedelta(seconds=max(3, get_settings().index_lease_seconds)))
        )
        await db.commit()
        if result.rowcount != 1:
            raise LeaseLost("Document lease expired, input changed, or document deleted")


async def release_document(sessions, lease):
    async with sessions() as db:
        await db.execute(
            update(FileUpload)
            .where(
                FileUpload.id == lease.file_id,
                FileUpload.lease_owner == lease.owner,
                FileUpload.write_epoch == lease.epoch,
            )
            .values(lease_owner=None, lease_until=None)
        )
        await db.commit()


def session_factory(db):
    return async_sessionmaker(db.bind, expire_on_commit=False)
