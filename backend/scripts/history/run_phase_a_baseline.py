"""Archived Phase A fixture runner, retained to reproduce historical results."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.agent.llm import llm_service
from app.core.config import get_settings
from app.core.langfuse_observability import flush_langfuse, langfuse_span, observation_output
from app.evaluation.customer_service import evaluate_customer_service_case, validate_customer_service_case
from app.evaluation.customer_service_live import run_live_customer_service_case


async def run_case(case: dict, semaphore: asyncio.Semaphore) -> dict:
    async with semaphore, asyncio.timeout(150):
        with langfuse_span(
            "customer_service.phase_a_baseline",
            root=True,
            kind="evaluator",
            attributes={"langfuse.trace.metadata.case_id": case["id"]},
        ) as span:
            artifact = await run_live_customer_service_case(case, llm_service=llm_service)
            score = evaluate_customer_service_case(case, artifact)
            provider_usage = int(artifact["usage"]["totalTokens"] or 0)
            observation_output(span, {"automatedPass": score.passed, "providerUsageRecorded": bool(provider_usage)})
            return {
                "caseId": case["id"],
                "status": "captured" if provider_usage else "no_provider_usage",
                "automatedPass": score.passed,
                "layers": {
                    name: {"passed": layer.passed, "metrics": layer.metrics, "details": layer.details}
                    for name, layer in score.layers.items()
                },
                "artifact": artifact,
                "traceId": f"{span.get_span_context().trace_id:032x}" if span is not None else None,
            }


async def main(concurrency: int) -> None:
    settings = get_settings()
    if not settings.llm_api_key:
        raise SystemExit("The live model is not configured")
    cases = [json.loads(line) for line in sys.stdin if line.strip()]
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise SystemExit("Expected unique benchmark cases on stdin")
    errors = [check for case in cases if not (check := validate_customer_service_case(case))["pass"]]
    if errors:
        raise SystemExit(json.dumps(errors))
    semaphore = asyncio.Semaphore(concurrency)

    async def attempt(case: dict) -> None:
        try:
            result = await run_case(case, semaphore)
        except Exception as exc:
            result = {"caseId": case["id"], "status": "error", "errorType": type(exc).__name__}
        print("PHASE_A_RESULT=" + json.dumps(result, ensure_ascii=True), flush=True)

    print("PHASE_A_MODEL=" + settings.llm_model, flush=True)
    await asyncio.gather(*(attempt(case) for case in cases))
    await asyncio.to_thread(flush_langfuse)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--concurrency", type=int, default=3, choices=range(1, 5))
    asyncio.run(main(parser.parse_args().concurrency))
