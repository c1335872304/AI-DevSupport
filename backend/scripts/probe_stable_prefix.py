"""Real-provider formatting experiment on frozen, already-authorized evidence.

Run after the natural E2E cases and before stopping this evaluation container.
No simultaneous observer traffic: the separate process restores the cumulative
request budget, and the server must be restarted before any later provider call.
This is a format-only experiment, not a replacement for retrieval E2E testing.
"""

import argparse
import asyncio
import copy
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/evaluation")


def freeze_inputs():
    from app.agent.document_context import pack_document_context

    target = ROOT / "private/probe-inputs.json"
    assert not target.exists()
    plan = json.loads((ROOT / "cache-probe-plan.json").read_text(encoding="utf-8"))
    result = []
    for group in plan["groups"]:
        artifact = json.loads((ROOT / "baseline" / (group["case"] + ".json")).read_text(encoding="utf-8"))
        assert artifact["status"] == "COMPLETED"
        assert all(c["status"] == 200 for c in artifact["citations"])
        evidence = next(
            e["summary"]
            for e in artifact["events"]
            if e.get("type") == "evidence_summary" and e["summary"].get("knowledgeExcerpts")
        )
        # The pre-packing evidence contains every retrieved candidate, whereas
        # the completed snapshot has already removed unused source mappings.
        references = evidence.get("citations") or list(artifact["snapshot"]["referenceMappings"].values())
        packed = pack_document_context(artifact["case"]["question"], evidence, references)
        assert packed.bounded
        payload = json.loads(packed.messages[1]["content"])
        units = copy.deepcopy(payload["excerpts"])
        positions = {}
        for unit in units:
            unit["_origins"] = []
            for ref in unit["refs"]:
                position = positions.get(ref, 0)
                unit["_origins"].append([ref, position])
                positions[ref] = position + 1
        result.append(
            {
                **group,
                "system": packed.messages[0]["content"],
                "references": packed.references,
                "units": units,
                "authorizedNaturalArtifactSha256": hashlib.sha256(
                    (ROOT / "baseline" / (group["case"] + ".json")).read_bytes()
                ).hexdigest(),
            }
        )
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Frozen three authorized evidence sets; source signatures stay private")


def rearrange(group, step):
    references = copy.deepcopy(group["references"])
    slots = [r["referenceNumber"] for r in references]
    if step == 1:
        references.reverse()
    elif step == 2:
        references = references[1:] + references[:1]
    remap = {r["referenceNumber"]: slot for r, slot in zip(references, slots)}
    for ref in references:
        ref["referenceNumber"] = remap[ref["referenceNumber"]]
    units = copy.deepcopy(group["units"])
    for unit in units:
        unit["refs"] = [remap[ref] for ref in unit["refs"]]
        unit["_origins"] = [[remap[ref], position] for ref, position in unit["_origins"]]
    # Preserve within-source block order but vary source order, as a retrieval
    # ranking change would. The selected words and evidence membership are fixed.
    units.sort(key=lambda u: min(u["refs"]))
    return references, units


def messages_for(group, step, phase, namespace):
    references, units = rearrange(group, step)
    question = group["questions"][step]
    if phase == "final":
        from app.agent.document_context import canonical_document_messages

        messages, references, _remap, _prefix = canonical_document_messages(question, units, references)
        payload = json.loads(messages[1]["content"])
    else:
        payload = {
            "question": question,
            "sources": [{"ref": r["referenceNumber"], "fileName": r["fileName"]} for r in references],
            "excerpts": [{"refs": u["refs"], "text": u["text"]} for u in units],
        }
    # A fresh, constant namespace per arm/group prevents a previously warmed
    # whole-document prefix from deciding the comparison before priming.
    payload = {"cacheExperiment": f"{namespace}-{phase}-{group['id']}", **payload}
    return [
        {"role": "system", "content": group["system"]},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
    ], references


async def run(phase):
    import httpx
    from observer import CASE, ProviderObserver

    from app.agent.document_context import filter_document_absence_claims
    from app.agent.graph.answer_content import ensure_reference_citations
    from app.agent.llm import llm_service
    from app.core.config import get_settings

    plan_path = ROOT / "cache-probe-plan.json"
    frozen = json.loads((ROOT / "frozen-inputs.json").read_text())
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == frozen["cacheProbePlanSha256"]
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    groups = json.loads((ROOT / "private/probe-inputs.json").read_text(encoding="utf-8"))
    for group in groups:
        assert (
            hashlib.sha256((ROOT / "baseline" / (group["case"] + ".json")).read_bytes()).hexdigest()
            == group["authorizedNaturalArtifactSha256"]
        )
        prepared = [messages_for(group, step, phase, plan["namespace"])[0] for step in range(4)]
        assert prepared[0] == prepared[3], "Exact-repeat control must be byte identical"
        if phase == "final":
            prefixes = [m[1]["content"][: m[1]["content"].rindex(',"question":')] for m in prepared]
            assert len(set(prefixes)) == 1, "Source/rank permutations must preserve the full document prefix"
    observer = ProviderObserver(get_settings(), ROOT / "provider-usage.jsonl")
    original = httpx.AsyncClient.send

    async def observed(client, request, **kwargs):
        return await observer.send(original, client, request, **kwargs)

    httpx.AsyncClient.send = observed
    output = ROOT / phase / "cache-probe"
    output.mkdir(exist_ok=True)
    prime = {}
    for step in range(4):
        for group in groups:
            case_id = f"P-{group['id']}-{step + 1}"
            path = output / (case_id + ".json")
            assert not path.exists(), "Every experiment attempt must be retained"
            messages, references = messages_for(group, step, phase, plan["namespace"])
            serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode()
            prime.setdefault(group["id"], serialized)
            common = 0
            for a, b in zip(prime[group["id"]], serialized):
                if a != b:
                    break
                common += 1
            row = {
                "id": case_id,
                "phase": phase,
                "vendor": group["vendor"],
                "step": step + 1,
                "question": group["questions"][step],
                "requiredClaims": group["requiredClaims"],
                "startedAt": datetime.now(UTC).isoformat(),
                "messageSha256": hashlib.sha256(serialized).hexdigest(),
                "messageBytes": len(serialized),
                "commonPrefixBytesWithPrime": common,
                "references": references,
                "formatOnlyExperiment": True,
            }
            if phase == "final":
                payload = messages[1]["content"]
                prefix = payload[: payload.rindex(',"question":')]
                row["documentPrefixSha256"] = hashlib.sha256(prefix.encode()).hexdigest()
            token = CASE.set(case_id)
            started = time.perf_counter()
            chunks = []
            try:
                async for chunk in llm_service.stream_messages(messages, force_no_tools=True):
                    if not chunks:
                        row["firstContentMs"] = round((time.perf_counter() - started) * 1000, 2)
                    chunks.append(chunk)
                raw_answer = "".join(chunks)
                guarded, removed = filter_document_absence_claims(raw_answer)
                row.update(
                    status="COMPLETED",
                    rawAnswer=raw_answer,
                    answer=ensure_reference_citations(guarded, references),
                    filteredAbsenceSentences=removed,
                )
            except Exception as exc:  # noqa: BLE001 - persist failed paid attempts before stopping
                row.update(status="ERROR", errorType=type(exc).__name__, answer="".join(chunks))
            finally:
                CASE.reset(token)
            row["elapsedMs"] = round((time.perf_counter() - started) * 1000, 2)
            path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
            print(case_id, row["status"], row["elapsedMs"], "ms", flush=True)
            assert row["status"] == "COMPLETED", "Preserve failure; do not silently continue or rerun"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "baseline", "final"])
    args = parser.parse_args()
    if args.action == "freeze":
        freeze_inputs()
    else:
        asyncio.run(run(args.action))
