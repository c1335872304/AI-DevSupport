"""Stable correlation between an authenticated chat generation and its root trace."""

import hashlib


def generation_trace_id(generation_id: str) -> str:
    return hashlib.sha256(f"paismart:chat:{generation_id}".encode()).hexdigest()[:32]
