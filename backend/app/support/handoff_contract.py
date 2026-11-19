from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass

HANDOFF_CREATE = "create_support_handoff"
VALID_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT"}
HANDOFF_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string", "minLength": 3, "maxLength": 2000},
        "summary": {"type": "string", "minLength": 10, "maxLength": 6000},
        "category": {"type": "string", "maxLength": 64, "default": "GENERAL"},
        "priority": {"type": "string", "enum": sorted(VALID_PRIORITIES), "default": "NORMAL"},
    },
    "required": ["reason", "summary"],
    "additionalProperties": False,
}


def normalize_handoff(reason: str, summary: str, category: str, priority: str) -> dict[str, str]:
    return {
        "reason": reason.strip()[:2000],
        "summary": summary.strip()[:6000],
        "category": (category or "GENERAL").strip().upper()[:64],
        "priority": (priority or "NORMAL").strip().upper(),
    }


def _fingerprint(payload: dict[str, str]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class HandoffAuthorization:
    """In-process capability passed only by the graph's post-evidence write node."""

    authorization_id: str
    action: str
    user_id: str
    generation_id: str
    fingerprint: str
    expires_at: float

    def permits(self, user_id: str, generation_id: str, payload: dict[str, str]) -> bool:
        return (
            self.action == HANDOFF_CREATE
            and self.user_id == user_id
            and self.generation_id == generation_id
            and self.fingerprint == _fingerprint(payload)
            and time.monotonic() < self.expires_at
        )


def authorize_handoff(user_id: str, generation_id: str, arguments: dict[str, str]) -> HandoffAuthorization:
    payload = normalize_handoff(
        arguments["reason"], arguments["summary"],
        arguments.get("category", "GENERAL"), arguments.get("priority", "NORMAL"),
    )
    return HandoffAuthorization(
        authorization_id=secrets.token_hex(12),
        action=HANDOFF_CREATE,
        user_id=user_id,
        generation_id=generation_id,
        fingerprint=_fingerprint(payload),
        expires_at=time.monotonic() + 60,
    )
