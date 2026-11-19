"""Export a read-only, manifest-bound official corpus with existing real vectors.

No users, credentials, billing ledgers or application configuration are exported.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def export(database,manifest_path,output):
    assert not output.exists(), "Refuse to overwrite an existing migration bundle"
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    assert Counter(d['provider'] for d in manifest['documents']) == {'gpt':20,'qwen':20,'deepseek':20}
    db=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    items=[]
    with db,zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as archive:
        for document in manifest['documents']:
            name=document['file']
            assert Path(name).name==name
            files=db.execute('SELECT * FROM file_upload WHERE file_name=? AND deleted_at IS NULL',(name,)).fetchall()
            assert len(files)==1,name
            file=dict(files[0]);raw=(manifest_path.parent/name).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==document['sha256']
            assert hashlib.md5(raw).hexdigest()==(file['source_md5'] or file['file_md5'])
            parameters=(file['file_md5'],file['user_id'],file['active_vector_version'])
            vectors=[dict(r) for r in db.execute('SELECT * FROM document_vectors WHERE file_md5=? AND user_id=? AND vector_version=? ORDER BY chunk_id',parameters)]
            parents=[dict(r) for r in db.execute('SELECT * FROM document_parent_chunks WHERE file_md5=? AND user_id=? AND vector_version=? ORDER BY parent_chunk_id',parameters)]
            assert vectors and parents and all(v['model_version']=='text-embedding-v4' and len(json.loads(v['vector_json']))==256 for v in vectors)
            assert [v['chunk_id'] for v in vectors]==list(range(len(vectors)))
            assert all(sum(p['start_chunk_id']<=v['chunk_id']<=p['end_chunk_id'] for p in parents)==1 for v in vectors)
            items.append({'manifest':document,'file':file,'vectors':vectors,'parents':parents})
            archive.writestr('sources/'+name,raw)
        archive.writestr('bundle.json',json.dumps({'model':'text-embedding-v4','dimension':256,'documents':items},ensure_ascii=False))
    db.close()
    return {'documents':len(items),'vectors':sum(len(d['vectors']) for d in items),'parents':sum(len(d['parents']) for d in items),
        'bundleSha256':hashlib.sha256(output.read_bytes()).hexdigest(),'providerCalls':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=ROOT/'data/paismart.db')
    parser.add_argument('--manifest',type=Path,default=ROOT/'vendor_knowledge/manifest.json')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(export(args.database,args.manifest,args.output)))
