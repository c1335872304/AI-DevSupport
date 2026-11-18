"""Canonical immutable source snapshot shared by request creation and builders."""

import hashlib
import json
from types import SimpleNamespace
from app.db.models import DocumentRevision
from app.knowledge.metadata import SCALAR_FIELDS, apply_metadata_to_file, file_metadata


def source_revision(file, raw, storage_key, *, apply_desired=True, revision_number=None):
    attributes = {column: getattr(file, column, None) for column in SCALAR_FIELDS.values()}
    attributes.update(
        knowledge_effective_date=file.knowledge_effective_date,
        knowledge_effective_until=file.knowledge_effective_until,
    )
    value = SimpleNamespace(**attributes)
    if apply_desired and file.desired_metadata_json:
        apply_metadata_to_file(value, json.loads(file.desired_metadata_json))
    metadata = file_metadata(value)
    number = file.input_revision if revision_number is None else revision_number
    identity = {
        "fileId": file.id,
        "inputRevision": number,
        "fileName": file.file_name,
        "content": hashlib.sha256(raw).hexdigest(),
        "metadata": metadata,
    }
    revision_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()
    return DocumentRevision(
        revision_id=revision_id,
        file_id=file.id,
        content_hash=identity["content"],
        storage_key=storage_key,
        metadata_json=json.dumps(
            {**metadata, "source_file_name": file.file_name, "input_revision": number},
            ensure_ascii=False,
            default=str,
        ),
    )


async def remember_revision(db, file, raw, key, **kwargs):
    revision = source_revision(file, raw, key, **kwargs)
    if not await db.get(DocumentRevision, revision.revision_id):
        db.add(revision)
    return revision.revision_id
