from app.agent.entities import extract_entities, resolve_entities


def test_extracts_legacy_diagnostic_entities():
    entities = extract_entities("请求 req_demo_401 返回 401，接口 /v1/chat，错误 AUTH_KEY_EXPIRED，应用 app_demo")
    assert entities == {
        "request_id": "req_demo_401",
        "error_code": "AUTH_KEY_EXPIRED",
        "http_status": "401",
        "endpoint": "/v1/chat",
        "app_id": "app_demo",
    }


def test_follow_up_reuses_history_entities_and_marks_sources():
    entities, sources = resolve_entities(
        "那为什么？",
        [{"role": "user", "content": "请求 req_demo_401 返回 401，错误 AUTH_KEY_EXPIRED"}],
        remembered_entities={},
        follow_up=True,
    )
    assert entities["request_id"] == "req_demo_401"
    assert entities["error_code"] == "AUTH_KEY_EXPIRED"
    assert sources == {"request_id": "history", "http_status": "history", "error_code": "history"}


def test_new_topic_does_not_inject_stale_entities_into_current_route():
    entities, sources = resolve_entities(
        "请介绍退款政策",
        [{"role": "user", "content": "请求 req_demo_401 返回 401"}],
        remembered_entities={"request_id": "req_demo_401"},
        follow_up=False,
    )
    assert entities == {}
    assert sources == {}
