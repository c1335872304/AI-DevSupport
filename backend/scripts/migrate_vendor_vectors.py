"""Offline, explicitly planned corpus replacement using verified existing Qwen vectors.

Run with API/Worker stopped and DB/MinIO/ES backed up. Dry-run writes an exact
allowlist plan. --apply stages all new projections before one DB publish switch;
only the planned legacy IDs are tombstoned and collected. No model calls.
"""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import uuid
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select, func, update
from app.core.config import get_settings
from app.core.time import utcnow
from app.db.models import User, FileUpload, DocumentVector, DocumentParentChunk, ProcessingJob, IndexBuild
from app.db.session import SessionLocal, engine
from app.documents.storage import storage_service
from app.documents.revision_snapshot import remember_revision
from app.documents.lifecycle import collect_garbage
from app.knowledge.elasticsearch import elasticsearch_service as es
from app.knowledge.metadata import apply_metadata_to_file, es_metadata

LEGACY = {"api-getting-started.md","authentication.md","billing-policy.md","error-codes.md",
    "rate-limit.md","refund-policy.md","release-notes.md","security-and-data-handling.md","troubleshooting-faq.md"}


def identity(file):
    return {k:getattr(file,k) for k in ("id","file_md5","file_name","user_id","active_vector_version","input_revision")}


async def migrate(args):
    settings = get_settings()
    archive = zipfile.ZipFile(args.bundle)
    bundle = json.loads(archive.read("bundle.json"))
    assert (bundle["model"],bundle["dimension"]) == (settings.embedding_model,settings.embedding_dimension)
    items = bundle["documents"]
    assert len(items) == 60 and {p:sum(x['manifest']['provider']==p for x in items) for p in ['gpt','qwen','deepseek']} == {'gpt':20,'qwen':20,'deepseek':20}
    for item in items:
        raw = archive.read("sources/"+item["manifest"]["file"])
        assert hashlib.sha256(raw).hexdigest() == item["manifest"]["sha256"]
        assert hashlib.md5(raw).hexdigest() == (item["file"]["source_md5"] or item["file"]["file_md5"])
        assert item["vectors"] and all(v["model_version"] == bundle["model"] and len(json.loads(v["vector_json"])) == bundle["dimension"] for v in item["vectors"])
    bundle_hash = hashlib.sha256(args.bundle.read_bytes()).hexdigest()
    if not args.apply:
        async with SessionLocal() as db:
            assert not await db.scalar(select(func.count()).select_from(ProcessingJob).where(ProcessingJob.status.in_(["PENDING","RUNNING"])))
            owner = await db.scalar(select(User).where(User.username == settings.bootstrap_admin_username))
            assert owner and owner.role == "ADMIN"
            old = list((await db.scalars(select(FileUpload).where(FileUpload.deleted_at.is_(None)).order_by(FileUpload.id))).all())
            assert len(old) == 21 and all(f.file_name in LEGACY or f.file_name.startswith('fixture-') for f in old)
            plan = {"migrationId":uuid.uuid4().hex,"bundleSha256":bundle_hash,"ownerId":str(owner.id),"legacy":[identity(f) for f in old],"documents":60,"vectors":sum(len(x["vectors"]) for x in items),"parents":sum(len(x["parents"]) for x in items),"providerCalls":0}
        assert not args.plan.exists(), "Keep original plan; use --apply to resume"
        args.plan.write_text(json.dumps(plan,indent=2),encoding='utf-8')
        print(json.dumps({"dryRun":True,"legacyDocuments":len(old),"officialDocuments":60,"vectorsReused":plan['vectors'],"providerCalls":0}))
        return
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    assert plan['bundleSha256'] == bundle_hash
    owner = plan['ownerId']; prefix = 'vendor-imports/'+plan['migrationId']+'/'
    async with SessionLocal() as db:
        for expected in plan['legacy']:
            file = await db.get(FileUpload,expected['id'])
            assert file and (file.deleted_at is not None or identity(file) == expected), "Legacy allowlist changed"
    staged = []
    for item in items:
        original = item['file']; name = item['manifest']['file']; raw = archive.read('sources/'+name)
        build = uuid.uuid5(uuid.NAMESPACE_URL,prefix+name).hex
        key = prefix+owner+'/'+original['file_md5']+'/'+name
        await storage_service.put_bytes(key,raw,'text/markdown')
        async with SessionLocal() as db:
            file = await db.scalar(select(FileUpload).where(FileUpload.file_md5==original['file_md5'],FileUpload.user_id==owner))
            if file:
                assert file.storage_key == key and file.deleted_at is None, "Target document collision"
            else:
                file = FileUpload(file_md5=original['file_md5'],source_md5=hashlib.md5(raw).hexdigest(),file_name=name,
                    active_file_name=name,storage_key=key,active_source_key=key,total_size=len(raw),status=1,
                    process_status='IMPORTING',user_id=owner,org_tag='default',is_public=True,input_revision=1,write_epoch=1)
                apply_metadata_to_file(file,item['manifest']['metadata'])
                file.actual_chunk_count=len(item['vectors'])
                # Reused vectors have no new Provider token charge.
                file.actual_embedding_tokens=0
                db.add(file); await db.flush()
                revision = await remember_revision(db,file,raw,key)
                db.add(IndexBuild(build_id=build,file_id=file.id,owner='vendor-vector-migration',epoch=1,input_revision=1,
                    revision_id=revision,profile_id='reused-qwen-v4-256',status='BUILDING',
                    manifest_json=json.dumps({'migrationId':plan['migrationId'],'sourceSha256':item['manifest']['sha256'],'reusedVectors':len(item['vectors']),'providerCalls':0})))
                for v in item['vectors']:
                    values={k:v[k] for k in ('chunk_id','text_content','page_number','location_json','anchor_text','model_version','vector_json')}
                    db.add(DocumentVector(**values,file_md5=file.file_md5,user_id=owner,vector_version=build,org_tag=file.org_tag,is_public=True))
                for p in item['parents']:
                    values={k:p[k] for k in ('parent_chunk_id','text_content','page_number','location_json','start_chunk_id','end_chunk_id')}
                    db.add(DocumentParentChunk(**values,file_md5=file.file_md5,user_id=owner,vector_version=build,org_tag=file.org_tag,is_public=True))
                await db.commit()
            stored = list((await db.scalars(select(DocumentVector).where(DocumentVector.file_md5==file.file_md5,DocumentVector.user_id==owner,DocumentVector.vector_version==build).order_by(DocumentVector.chunk_id))).all())
            assert [(v.chunk_id,v.text_content,v.vector_json) for v in stored] == [(v['chunk_id'],v['text_content'],v['vector_json']) for v in item['vectors']]
            documents=[]
            for v in item['vectors']:
                parents=[p for p in item['parents'] if p['start_chunk_id']<=v['chunk_id']<=p['end_chunk_id']]
                assert len(parents)==1
                documents.append({'fileMd5':file.file_md5,'fileName':name,'chunkId':v['chunk_id'],'parentChunkId':parents[0]['parent_chunk_id'],
                    'indexVersion':build,'embeddingModel':bundle['model'],'embeddingDimension':bundle['dimension'],'textContent':v['text_content'],
                    'pageNumber':v['page_number'],'anchorText':v['anchor_text'],'userId':owner,'orgTag':file.org_tag,'isPublic':True,
                    **es_metadata(file),'vector':json.loads(v['vector_json'])})
            file_id=file.id
        await es.bulk_index(documents)
        await es.verify_version(original['file_md5'],owner,build,len(documents))
        await es.verify_documents(documents)
        staged.append((file_id,build,len(documents)))
        print(json.dumps({'staged':name,'reusedVectors':len(documents)}),flush=True)
    # The only visibility switch: publish all official versions and tombstone the
    # exact preflight allowlist in one transaction; no broad delete-by-owner.
    async with SessionLocal() as db:
        for expected in plan['legacy']:
            file=await db.scalar(select(FileUpload).where(FileUpload.id==expected['id']).with_for_update())
            if file.deleted_at is None:
                assert identity(file)==expected
                file.deleted_at=utcnow();file.active_vector_version=None;file.write_epoch+=1;file.input_revision+=1
                file.process_status='DELETING';file.lease_owner=None;file.lease_until=None
        for file_id,build,count in staged:
            await db.execute(update(FileUpload).where(FileUpload.id==file_id,FileUpload.deleted_at.is_(None)).values(active_vector_version=build,process_status='COMPLETED',process_error=None))
            await db.execute(update(IndexBuild).where(IndexBuild.build_id==build).values(status='PUBLISHED',completed_chunks=count))
        await db.commit()
    for expected in plan['legacy']:
        await collect_garbage(document_id=expected['id'],retention_seconds=0)
    report={'passed':True,'officialDocuments':60,'providers':{'deepseek':20,'qwen':20,'gpt':20},'reusedVectors':plan['vectors'],
        'parents':plan['parents'],'legacyTombstones':len(plan['legacy']),'providerCalls':0,'sourceBundleSha256':bundle_hash,'published':staged}
    args.plan.with_name('migration-result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='published'}))


async def main(args):
    try:
        await migrate(args)
    finally:
        if es.client: await es.client.close()
        await engine.dispose()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--apply',action='store_true')
    asyncio.run(main(parser.parse_args()))
