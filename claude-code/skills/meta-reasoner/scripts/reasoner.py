"""Meta-cognitive reasoning runner.

Reads a structured invocation (trigger + inputs), executes the five-phase
DECOMPOSE -> SOLVE -> VERIFY -> SYNTHESIZE -> REFLECT loop, and writes an
envelope-wrapped reasoning_trace artifact to disk.

This script is a *runner*: it consumes a pre-built phase plan from the
caller (typically an LLM agent) and persists the result. The agent is
expected to fill in the per-phase reasoning content; this script enforces
schema, threshold, and retry bookkeeping.

Usage::

    python reasoner.py \
        --trigger '{"agent": "spec-creator", "stage": "stage-2", "complexity_signals": ["spec-ambiguity"]}' \
        --plan plan.json \
        --session-id auto-orc-20260515-foo \
        --producer-agent spec-creator \
        --output .orchestrate/<sid>/reasoning-traces/reasoning-trace-<ts>.json
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_LIB = Path(__file__).resolve().parents[3] / "lib"
if str(REPO_LIB) not in sys.path:
    sys.path.insert(0, str(REPO_LIB))

from artifact_envelope import build_envelope  # noqa: E402

THRESHOLD = 0.8
MAX_RETRIES = 3


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def should_skip(inputs: list[Any], context: dict[str, Any]) -> tuple[bool, str]:
    """Return (skip, reason) for simple-question gating."""
    if context.get("force"):
        return False, ""
    if len(inputs) <= 1 and not context.get("alternatives_listed") \
            and not context.get("validator_warnings") \
            and not context.get("in_gate_dispute") \
            and context.get("draft_confidence", 1.0) >= 0.7:
        return True, "single-input lookup; no alternatives; no warnings"
    return False, ""


def _weighted_aggregate(verify: list[dict[str, Any]],
                        weights: dict[str, float]) -> float:
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(
            f"Weights must sum to 1.0, got {total_weight}"
        )
    agg = 0.0
    for v in verify:
        sid = v["sub_id"]
        if sid not in weights:
            raise ValueError(f"Missing weight for sub_id {sid}")
        agg += weights[sid] * float(v["adj_confidence"])
    return round(agg, 6)


def _weakest_sub(verify: list[dict[str, Any]]) -> str:
    return min(verify, key=lambda v: v["adj_confidence"])["sub_id"]


def run_loop(plan: dict[str, Any]) -> dict[str, Any]:
    """Execute the SYNTHESIZE + REFLECT phases against a pre-built plan.

    The plan must include ``decompose``, ``solve``, ``verify``, and a
    ``weights`` mapping. The runner produces ``synthesize``, ``reflect``,
    and ``output_triplet`` sections. Retries are bookkept; the runner
    cannot itself re-solve a sub-problem (the caller LLM does that and
    re-invokes); instead this captures the retry history when provided.
    """
    decompose = plan["decompose"]
    solve = plan["solve"]
    verify = plan["verify"]
    weights = plan["weights"]
    answer_synthesis = plan.get("synthesis_answer", "")
    retry_history = plan.get("retry_history", [])

    aggregate = _weighted_aggregate(verify, weights)
    retries = len(retry_history)
    meets = aggregate >= THRESHOLD

    caveats: list[str] = list(plan.get("caveats", []))
    if not meets:
        weakest = _weakest_sub(verify)
        caveats.append(
            f"aggregate_confidence {aggregate} below {THRESHOLD}; "
            f"weakest sub-problem: {weakest}"
        )

    return {
        "trigger": plan.get("trigger", {}),
        "decompose": decompose,
        "solve": solve,
        "verify": verify,
        "synthesize": {
            "weights": weights,
            "aggregate_confidence": aggregate,
            "answer": answer_synthesis,
        },
        "reflect": {
            "meets_threshold": meets,
            "threshold": THRESHOLD,
            "retries": retries,
            "retry_history": retry_history,
        },
        "output_triplet": {
            "answer": answer_synthesis,
            "confidence": aggregate,
            "key_caveats": caveats,
        },
    }


def _load(arg: str) -> Any:
    if arg.startswith("@"):
        return json.loads(Path(arg[1:]).read_text(encoding="utf-8"))
    return json.loads(arg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--trigger", required=True,
                        help="JSON literal or @path/to/trigger.json")
    parser.add_argument("--inputs", default="[]",
                        help="JSON list of candidate inputs/options")
    parser.add_argument("--plan",
                        help="@path/to/plan.json — required unless --check-skip-only")
    parser.add_argument("--check-skip-only", action="store_true")
    parser.add_argument("--context", default="{}",
                        help="JSON context for skip heuristic")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--stage", default="cross-session")
    parser.add_argument("--producer-agent", required=True)
    parser.add_argument("--output",
                        help="Output path. Required unless --check-skip-only.")
    args = parser.parse_args(argv)

    trigger = _load(args.trigger)
    inputs = _load(args.inputs)
    context = _load(args.context)

    skip, reason = should_skip(inputs, context)
    if skip:
        result = {"skipped": True, "reason": reason}
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(result, indent=2),
                                         encoding="utf-8")
        print(json.dumps(result, indent=2))
        return 0
    if args.check_skip_only:
        print(json.dumps({"skipped": False}, indent=2))
        return 0
    if not args.plan or not args.output:
        print("--plan and --output are required when not skipping",
              file=sys.stderr)
        return 2

    plan = _load(f"@{args.plan}" if not args.plan.startswith("@") else args.plan)
    plan.setdefault("trigger", trigger)
    body = run_loop(plan)

    artifact_id = (
        f"reasoning-trace-{args.stage}-"
        f"{uuid.uuid4().hex[:8]}-"
        f"{_utc_now_iso().replace(':', '').replace('-', '').replace('.', '')}"
    )
    envelope = build_envelope(
        artifact_type="reasoning_trace",
        artifact_id=artifact_id,
        session_id=args.session_id,
        stage=args.stage,
        producer_agent=f"skill:meta-reasoner@{args.producer_agent}",
        body=body,
        status="ok" if body["reflect"]["meets_threshold"] else "warn",
        verdict="n/a",
        confidence={
            "value": body["synthesize"]["aggregate_confidence"],
            "reasoning_trace": args.output,
            "caveats": body["output_triplet"]["key_caveats"],
        },
    )

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out),
                      "aggregate_confidence":
                          body["synthesize"]["aggregate_confidence"],
                      "meets_threshold":
                          body["reflect"]["meets_threshold"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
