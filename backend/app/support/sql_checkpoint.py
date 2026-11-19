"""LangGraph approval checkpoints in the same transaction as the business row."""
from __future__ import annotations

import asyncio
import base64
import json

from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple, WRITES_IDX_MAP, get_checkpoint_id
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from sqlalchemy import select

from app.db.models import ApprovalCheckpoint, ApprovalWrite


class SQLApprovalSaver(BaseCheckpointSaver):
    def __init__(self, db):
        super().__init__(serde=JsonPlusSerializer(allowed_msgpack_modules=[]))
        self.db = db
        self.lock = asyncio.Lock()

    def encode(self, value):
        kind, raw = self.serde.dumps_typed(value)
        return json.dumps([kind, base64.b64encode(raw).decode('ascii')])

    def decode(self, raw):
        kind, body = json.loads(raw)
        return self.serde.loads_typed((kind, base64.b64decode(body)))

    @staticmethod
    def config(thread, ns, checkpoint):
        return {'configurable': {'thread_id': thread, 'checkpoint_ns': ns, 'checkpoint_id': checkpoint}}

    async def aget_tuple(self, config):
        c = config['configurable']
        thread, ns = str(c['thread_id']), c.get('checkpoint_ns', '')
        query = select(ApprovalCheckpoint).where(ApprovalCheckpoint.thread_id == thread,
                                                ApprovalCheckpoint.checkpoint_ns == ns)
        if checkpoint := get_checkpoint_id(config):
            query = query.where(ApprovalCheckpoint.checkpoint_id == checkpoint)
        async with self.lock:
            row = await self.db.scalar(query.order_by(ApprovalCheckpoint.checkpoint_id.desc()).limit(1).with_for_update())
            if not row:
                return None
            writes = (await self.db.scalars(select(ApprovalWrite).where(
                ApprovalWrite.thread_id == thread, ApprovalWrite.checkpoint_ns == ns,
                ApprovalWrite.checkpoint_id == row.checkpoint_id,
            ).order_by(ApprovalWrite.task_id, ApprovalWrite.idx).with_for_update())).all()
            return CheckpointTuple(self.config(thread, ns, row.checkpoint_id), self.decode(row.value_json),
                json.loads(row.metadata_json), self.config(thread, ns, row.parent_id) if row.parent_id else None,
                [(w.task_id, w.channel, self.decode(w.value_json)) for w in writes])

    async def aput(self, config, checkpoint, metadata, new_versions):
        c = config['configurable']
        thread, ns = str(c['thread_id']), c.get('checkpoint_ns', '')
        async with self.lock:
            await self.db.merge(ApprovalCheckpoint(thread_id=thread, checkpoint_ns=ns,
                checkpoint_id=checkpoint['id'], parent_id=c.get('checkpoint_id'),
                value_json=self.encode(checkpoint), metadata_json=json.dumps(metadata, default=str)))
            await self.db.flush()
        return self.config(thread, ns, checkpoint['id'])

    async def aput_writes(self, config, writes, task_id, task_path=''):
        c = config['configurable']
        async with self.lock:
            for idx, (channel, value) in enumerate(writes):
                identity = (str(c['thread_id']), c.get('checkpoint_ns', ''), c['checkpoint_id'],
                            task_id, WRITES_IDX_MAP.get(channel, idx))
                row = await self.db.get(ApprovalWrite, identity)
                if row and channel not in WRITES_IDX_MAP:
                    continue
                if not row:
                    row = ApprovalWrite(thread_id=identity[0], checkpoint_ns=identity[1],
                        checkpoint_id=identity[2], task_id=identity[3], idx=identity[4])
                    self.db.add(row)
                row.channel, row.value_json = channel, self.encode(value)
            await self.db.flush()
