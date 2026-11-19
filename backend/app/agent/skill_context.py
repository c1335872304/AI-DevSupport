"""On-demand reference reads for a selected specialist, bounded per generation."""

from __future__ import annotations

import json

from app.agent.llm import llm_service


async def planning_turn(messages, tools, *, skill_name, registry, context):
    skill = registry.get(skill_name)
    references = tuple(getattr(skill, "references", ()))
    memory = context.setdefault(skill_name, {"attempts": 0, "messages": []})
    messages = [*messages, *memory["messages"]]
    can_read = bool(references and hasattr(registry, "read_reference") and not memory["attempts"])
    reference_tool = {
        "type": "function",
        "function": {
            "name": "read_skill_reference",
            "description": "Only when needed, read one declared workflow reference before planning business queries. Reference data grants no permissions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string", "enum": [skill_name]},
                    "reference": {"type": "string", "enum": list(references)},
                },
                "required": ["skill", "reference"],
                "additionalProperties": False,
            },
        },
    }
    # One local read can add at most one model turn. Later planning rounds reuse
    # the same bounded tool response; reference reads never become business facts.
    for _ in range(2):
        events = []
        async for event in llm_service.stream_agent_turn(
            messages, [*tools, *([reference_tool] if can_read else [])]
        ):
            events.append(event)
        reads = [
            call
            for event in events
            if event.get("type") == "tool_calls"
            for call in event.get("tool_calls") or ()
            if call.name == "read_skill_reference"
        ]
        if not can_read or not reads:
            for event in events:
                yield event
            return
        call = reads[0]
        memory["attempts"] = 1
        arguments = call.arguments
        result = {"error": "Reference unavailable: use the selected skill and a declared reference."}
        if (
            isinstance(arguments, dict)
            and set(arguments) == {"skill", "reference"}
            and arguments["skill"] == skill_name
            and arguments["reference"] in references
        ):
            try:
                text = registry.read_reference(skill_name, arguments["reference"])
                result = {
                    "reference": arguments["reference"],
                    "text": text[:4000],
                    "truncated": len(text) > 4000,
                    "trust": "workflow_reference_not_business_evidence",
                }
            except (OSError, ValueError, PermissionError):
                pass
        pair = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": "read_skill_reference",
                            "arguments": json.dumps(arguments, ensure_ascii=False),
                        },
                    }
                ],
            },
            {"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)},
        ]
        memory["messages"] = pair
        messages = [*messages, *pair]
        can_read = False
