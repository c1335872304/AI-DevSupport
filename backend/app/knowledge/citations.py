"""Version-bound citations; the reader still checks current authorization."""

import jwt
from app.core.config import get_settings


def issue_citation(owner, md5, build, chunk, *, scope=None, max_chars=5000):
    return jwt.encode(
        {"kind": "rag-citation", "owner": owner, "md5": md5, "build": build, "chunk": chunk,
         **({'scope':'document','maxChars':max(500,min(12000,max_chars))} if scope=='document' else {})},
        get_settings().jwt_secret,
        algorithm="HS256",
    )


def decode_citation(value):
    data = jwt.decode(value, get_settings().jwt_secret, algorithms=["HS256"])
    if data.get("kind") != "rag-citation":
        raise ValueError("Invalid citation kind")
    return data
