from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing():
    hashed = hash_password("hello123")
    assert hashed != "hello123"
    assert verify_password("hello123", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("alice", 123, "USER")
    claims = decode_token(token, "access")
    assert claims["sub"] == "alice"
    assert claims["userId"] == "123"
