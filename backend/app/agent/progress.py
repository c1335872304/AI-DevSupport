"""Public business phases: no model reasoning, prompts, or tool arguments."""

from __future__ import annotations

import time

NODE_PHASES = {
    "load_context": "understanding",
    "extract_entities": "understanding",
    "routing_policy": "understanding",
    "target_specialist_dispatch": "checking",
    "target_execute_tools": "checking",
    "historical_diagnosis": "checking_request",
    "target_evidence_join": "reviewing",
    "target_create_handoff": "creating_handoff",
    "target_generate_response": "answering",
    "clarify": "waiting_for_user",
}


async def publish_progress(send_json, generation_id, phase):
    await send_json(
        {
            "type": "workflow_progress",
            "generationId": generation_id,
            "phase": phase,
            "timestamp": int(time.time() * 1000),
        }
    )


def tool_phase(name):
    if name in {"search_knowledge", "get_document", "list_documents"}:
        return "searching_documents"
    if name in {"query_plan", "query_usage", "query_bill"} or name.startswith("mcp__billing__"):
        return "checking_billing"
    if name.startswith("query_"):
        return "checking_request"
    return None
