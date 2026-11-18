from app.core.redaction import redact_data, redact_text


def test_redaction_masks_credentials_but_keeps_diagnostic_ids():
    text = "Authorization: Bearer abc.def; api_key=sk-test-secret-123456; request_id=req_123"
    redacted = redact_text(text)
    assert "abc.def" not in redacted
    assert "sk-test-secret-123456" not in redacted
    assert "req_123" in redacted
    assert "Authorization: Bearer [REDACTED]" in redacted
    assert redact_text("Authorization: Bearer <API_KEY>") == "Authorization: Bearer <API_KEY>"


def test_redaction_recurses_through_tool_arguments():
    payload = {
        "api_key": "sk-secret-123456",
        "api_key_id": "key_demo",
        "nested": [{"password": "hidden"}],
    }
    redacted = redact_data(payload)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["api_key_id"] == "key_demo"
    assert redacted["nested"][0]["password"] == "[REDACTED]"

