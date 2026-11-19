from datetime import datetime, timezone

from app.agent.diagnostic_window import diagnostic_window, render_window_result


NOW = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)


def user(*turns):
    return [{"role": "user", "content": text} for text in turns]


def test_collects_alternative_anchors_one_at_a_time():
    denied = "我没有请求号。"
    endpoint = "接口是 /v1/chat。"
    occurred = "发生在 2026-11-18 17:30。"
    assert "接口路径" in diagnostic_window(denied, [], diagnostic=True).next_question(NOW)
    assert "哪天" in diagnostic_window(endpoint, user(denied), diagnostic=True).next_question(NOW)
    assert "哪个时区" in diagnostic_window(occurred, user(denied, endpoint), diagnostic=False).next_question(NOW)
    assert "错误码" in diagnostic_window("北京时间", user(denied, endpoint, occurred), diagnostic=False).next_question(NOW)
    window = diagnostic_window(
        "HTTP 429", user(denied, endpoint, occurred, "北京时间"), diagnostic=False,
    )
    assert window.next_question(NOW) == ""
    assert window.arguments(NOW) == {
        "endpoint": "/v1/chat", "window": "explicit",
        "start_at": "2026-11-18T09:25:00+00:00", "end_at": "2026-11-18T09:35:00+00:00",
    }


def test_uses_corrected_endpoint_but_excludes_new_topics_and_new_request_ids():
    history = user("没有请求号，/v1/completions 返回 HTTP 429。")
    current = "刚才接口说错了，是 /v1/chat。"
    window = diagnostic_window(current, history, diagnostic=True)
    assert (window.endpoint, window.error) == ("/v1/chat", "429")
    assert diagnostic_window("找到了，请求号 req_123abc。", history, diagnostic=True) is None
    assert diagnostic_window("换个问题，查账单。", history, diagnostic=False) is None


def test_keeps_full_path_and_does_not_read_status_from_path():
    window = diagnostic_window(
        "请求号拿不到，接口是 /api/v1/jobs/503，2026-11-18 17:30 北京时间。",
        [], diagnostic=True,
    )
    assert window.endpoint == "/api/v1/jobs/503"
    assert not window.error
    assert "错误码" in window.next_question(NOW)


def test_window_summary_limits_claims_to_counts_and_handles_empty_results():
    data = {"windowStart": "start", "windowEnd": "end", "total": 2, "byStatus": {429: 1}}
    assert "HTTP 429 有 1 条" in render_window_result(data, "429")
    assert "无法确认其中哪条" in render_window_result(data, "429")
    assert "未查到调用记录" in render_window_result({**data, "total": 0}, "429")
