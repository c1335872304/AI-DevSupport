"""Backfill only missing ES profile fields after proving active DB/vector identity.

Dry run by default. Never calls an embedding provider or rewrites vector/source
content. A stale/mismatched projection stops the run rather than being relabelled.
"""

import argparse
import asyncio
import json
import math
from sqlalchemy import and_, or_, select
from app.db.models import DocumentVector, FileUpload
from app.db.session import SessionLocal, engine
from app.knowledge.elasticsearch import elasticsearch_service as es


async def repair(apply=False):
    assert es.client, "Requires Elasticsearch backend"
    await es.ensure_index()
    pending = []
    examined = 0
    async with SessionLocal() as db:
        rows = await db.stream(select(DocumentVector,FileUpload).join(FileUpload,and_(
            FileUpload.file_md5 == DocumentVector.file_md5,
            FileUpload.user_id == DocumentVector.user_id)).where(
                FileUpload.deleted_at.is_(None),or_(
                    FileUpload.active_vector_version == DocumentVector.vector_version,
                    and_(FileUpload.active_vector_version.is_(None),DocumentVector.vector_version == "legacy"))))
        async for vector, file in rows:
            identity = {"userId":str(vector.user_id),"fileMd5":vector.file_md5,
                "indexVersion":vector.vector_version,"chunkId":vector.chunk_id}
            identifier = es._document_id(identity)
            result = await es.client.get(index=es.settings.elasticsearch_index,id=identifier)
            source = result["_source"]
            assert all(source.get(k) == v for k,v in identity.items()), "Projection identity mismatch"
            assert source.get("textContent") == vector.text_content, "Projection text mismatch"
            stored = json.loads(vector.vector_json)
            actual = source.get("vector",[])
            assert len(actual) == len(stored) and all(math.isclose(a,b,rel_tol=1e-6,abs_tol=1e-8)
                for a,b in zip(actual,stored)), "Projection vector mismatch"
            profile = {"embeddingModel":vector.model_version,"embeddingDimension":len(stored)}
            assert all(source.get(k) in (None,v) for k,v in profile.items()), "Existing profile conflicts with DB"
            missing = {k:v for k,v in profile.items() if source.get(k) is None}
            examined += 1
            if missing:
                pending.append((identifier,missing,result["_seq_no"],result["_primary_term"]))
    # Finish all preflight checks before the first mutation. Optimistic ES guards
    # reject a concurrent change instead of overwriting an unseen source version.
    if apply:
        for identifier,fields,sequence,term in pending:
            await es.client.update(index=es.settings.elasticsearch_index,id=identifier,
                doc=fields,if_seq_no=sequence,if_primary_term=term)
        await es.client.indices.refresh(index=es.settings.elasticsearch_index)
    report = {"examined":examined,"missingProfiles":len(pending),"updated":len(pending) if apply else 0,
        "dryRun":not apply,"providerCalls":0,"vectorContentChanged":False,"databaseChanged":False}
    print(json.dumps(report))
    return report


async def main(apply):
    try:
        await repair(apply)
    finally:
        await es.client.close()
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply",action="store_true")
    asyncio.run(main(parser.parse_args().apply))
