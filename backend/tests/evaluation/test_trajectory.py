from copy import deepcopy

from app.evaluation.trajectory import percentile, ratio, score_episode, summarize


def fixture():
    return {
        "id": "x",
        "userId": "1",
        "diagnosis": {
            "diagnosisId": "case",
            "status": "WAITING_USER_ACTION",
            "workflow": {
                "decision": {
                    "candidates": [
                        {"cause": "RATE_LIMIT", "status": "SUPPORTED", "supportingEvidenceIds": ["a", "b"]}
                    ]
                }
            },
            "evidence": [
                {
                    "evidenceId": "a",
                    "ownerUserId": "1",
                    "verified": True,
                    "sourceType": "BUSINESS_QUERY",
                    "tool": "query_call_log",
                },
                {
                    "evidenceId": "b",
                    "ownerUserId": "1",
                    "verified": True,
                    "sourceType": "BUSINESS_QUERY",
                    "tool": "query_request_observation",
                },
            ],
        },
        "calls": [
            {"tool": "query_call_log", "anchored": True},
            {"tool": "query_request_observation", "anchored": True},
        ],
        "tickets": [],
    }


def test_false_evidence_and_unanchored_parameters_fail():
    expected = {"causes": ["RATE_LIMIT"], "status": "WAITING_USER_ACTION"}
    good = fixture()
    assert score_episode(expected, good)["passed"]
    for field, value in (("ownerUserId", "other"), ("verified", False), ("sourceType", "DOCUMENT_RULE")):
        bad = deepcopy(good)
        bad["diagnosis"]["evidence"][0][field] = value
        assert not score_episode(expected, bad)["passed"]
    bad = deepcopy(good)
    bad["calls"][0]["anchored"] = False
    assert not score_episode(expected, bad)["passed"]


def test_fake_resolution_and_duplicate_ticket_fail():
    bad = fixture()
    bad["diagnosis"]["status"] = "RESOLVED"
    assert not score_episode({"causes": ["RATE_LIMIT"], "status": "RESOLVED"}, bad)["checks"]["recoveryScope"]
    bad["diagnosis"]["status"] = "HANDED_OFF"
    for tickets in ([], ["one", "two"]):
        bad["tickets"] = tickets
        assert not score_episode({"causes": ["RATE_LIMIT"], "status": "HANDED_OFF"}, bad)["checks"][
            "ticketIdentity"
        ]


def test_empty_denominators_are_unavailable_and_failures_remain():
    assert ratio(0, 0)["value"] is None
    assert percentile([1, 2, 3, 4], 0.95) == 4
    row = score_episode({"causes": [], "status": "COLLECTING"}, fixture())
    summary = summarize([row])
    assert summary["failures"] == ["x"] and not summary["pass"]
