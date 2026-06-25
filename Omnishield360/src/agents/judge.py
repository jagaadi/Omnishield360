"""
OmniShield 360 - Agent-as-Judge Layer
A second-pass reasoning step that audits the first-pass decision for internal
contradictions before the claim is finalized. If the verdict is inconsistent,
the judge escalates to a clinical director review rather than rubber-stamping
the result.

The judge:
  1. Runs a deterministic contradiction check on the evidence chain.
  2. Optionally calls an LLM (with the same retry+cache pattern as the
     medical-necessity agent) for a natural-language consistency review.
  3. Returns a structured verdict: {consistent, conflicts, escalate, narrative}.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any


# ── LLM cache (mirrors medical_necessity.py) ──────────────────────────────
_LRU_CAPACITY = 128
_LRU_CACHE: "OrderedDict[str, dict[str, Any]]" = OrderedDict()


def _cache_get(key: str) -> dict[str, Any] | None:
    if key not in _LRU_CACHE:
        return None
    _LRU_CACHE.move_to_end(key)
    return _LRU_CACHE[key]


def _cache_put(key: str, value: dict[str, Any]) -> None:
    _LRU_CACHE[key] = value
    _LRU_CACHE.move_to_end(key)
    while len(_LRU_CACHE) > _LRU_CAPACITY:
        _LRU_CACHE.popitem(last=False)


def _deterministic_check(result: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Pure rule-based contradiction detector. Runs even when the LLM is offline.

    Rules:
      R1: status APPROVED_FOR_INTEGRATION must not coexist with any MEDIUM+
          evidence item in the chain.
      R2: risk_tier LOW must not coexist with human_review_required=True.
      R3: next_action must be present and non-empty.
      R4: evidence list must contain at least one item.
    """
    conflicts: list[str] = []

    status = result.get("status", "")
    risk_tier = result.get("risk_tier", "")
    next_action = result.get("next_action", "")
    human_required = bool(result.get("human_review_required", False))
    evidence_items = result.get("evidence", []) or []

    # R1
    if status == "APPROVED_FOR_INTEGRATION":
        bad_tiers = {"MEDIUM", "HIGH", "CRITICAL"}
        for ev in evidence:
            if ev.get("risk") in bad_tiers:
                conflicts.append(
                    f"R1: APPROVED status paired with {ev.get('risk')} evidence at stage "
                    f"'{ev.get('stage', '?')}'."
                )
                break

    # R2
    if risk_tier == "LOW" and human_required:
        conflicts.append("R2: risk_tier=LOW but human_review_required=True — impossible.")

    # R3
    if not next_action:
        conflicts.append("R3: next_action is empty.")

    # R4
    if not evidence_items:
        conflicts.append("R4: evidence list is empty — cannot defend decision in audit.")

    return {
        "consistent": not conflicts,
        "conflicts": conflicts,
        "escalate": bool(conflicts),
        "narrative": (
            "Deterministic check: no contradictions found."
            if not conflicts
            else f"Deterministic check found {len(conflicts)} contradiction(s)."
        ),
    }


def _llm_judge_review(prompt: str) -> dict[str, Any] | None:
    """Optional LLM pass; returns None on failure so the deterministic check still runs."""
    if os.getenv("UIPATH_NO_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return None

    try:
        from uipath.llm import complete  # lazy import

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = complete(prompt, model="gpt-4o", temperature=0)
                return json.loads(response)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                time.sleep(0.05 * (2 ** attempt))
        if last_error is not None:
            print(f"[JUDGE] LLM unavailable after retries: {last_error}")
        return None
    except Exception as e:
        print(f"[JUDGE] LLM path failed: {e}")
        return None


def run_judge_review(claim_id: str, evidence_chain: list[dict[str, Any]], final_result: dict[str, Any]) -> dict[str, Any]:
    """
    Reviews the first-pass decision and the evidence chain for contradictions.

    Args:
        claim_id: For logging and cache keying.
        evidence_chain: List of per-stage dicts, each {stage, risk, summary, ...}.
        final_result: The current decision dict the orchestrator is about to emit.

    Returns:
        dict with keys: consistent (bool), conflicts (list[str]),
        escalate (bool), narrative (str), and optionally llm_verdict (dict).
    """
    # ── Deterministic check (always runs) ────────────────────────────────
    verdict = _deterministic_check(final_result, evidence_chain)
    if verdict["consistent"]:
        # No need to spend LLM tokens when the rule check is clean
        return verdict

    # ── Optional LLM cross-check on the conflicts we found ───────────────
    cache_key = hashlib.sha256(
        f"{claim_id}|{json.dumps(final_result, sort_keys=True)}|{json.dumps(verdict, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    cached = _cache_get(cache_key)
    if cached is not None:
        return {**verdict, **cached, "narrative": cached.get("narrative", verdict["narrative"])}

    prompt = f"""You are an autonomous judge reviewing a healthcare claim decision for internal consistency.

Claim ID: {claim_id}
Final result: {json.dumps(final_result, sort_keys=True)}
Evidence chain: {json.dumps(evidence_chain, sort_keys=True)}
Deterministic conflicts found: {json.dumps(verdict['conflicts'], sort_keys=True)}

Respond with ONLY valid JSON (no markdown):
{{"consistent": true or false, "conflicts": ["..."], "escalate": true or false, "narrative": "one short sentence"}}
"""
    llm = _llm_judge_review(prompt)
    if llm is not None:
        # Merge: if LLM agrees, keep deterministic; if LLM disagrees, take the union
        merged_conflicts = sorted(set(verdict["conflicts"]) | set(llm.get("conflicts", [])))
        verdict = {
            "consistent": verdict["consistent"] and llm.get("consistent", False),
            "conflicts": merged_conflicts,
            "escalate": bool(merged_conflicts) or bool(llm.get("escalate", False)),
            "narrative": llm.get("narrative", verdict["narrative"]),
            "llm_verdict": llm,
        }
        _cache_put(cache_key, {"conflicts": merged_conflicts, "escalate": verdict["escalate"], "narrative": verdict["narrative"]})

    return verdict
