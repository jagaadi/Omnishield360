"""
OmniShield 360 - Medical Necessity Validator
Uses UiPath Agent Builder / LLM reasoning to evaluate clinical justification
for billed procedures. Falls back to rule-based approval if AI is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any


# ── Tiny LRU cache for LLM verdicts ──────────────────────────────────────
# Keyed on (cpt_code, chart_hash). Bounded so memory cannot grow unbounded
# in a long-running Orchestrator pod.
_LRU_CAPACITY = 256
_LRU_CACHE: "OrderedDict[tuple[str, str], dict[str, Any]]" = OrderedDict()


def _cache_get(key: tuple[str, str]) -> dict[str, Any] | None:
    if key not in _LRU_CACHE:
        return None
    _LRU_CACHE.move_to_end(key)
    return _LRU_CACHE[key]


def _cache_put(key: tuple[str, str], value: dict[str, Any]) -> None:
    _LRU_CACHE[key] = value
    _LRU_CACHE.move_to_end(key)
    while len(_LRU_CACHE) > _LRU_CAPACITY:
        _LRU_CACHE.popitem(last=False)


# ── Retry wrapper ────────────────────────────────────────────────────────
# Anything that looks transient (network, 5xx, timeout) gets retried. Persistent
# failures fall back to the rule-based path so the workflow never deadlocks.
_MAX_ATTEMPTS = 3
_BASE_BACKOFF_SECONDS = 0.05  # small in test env; real prod uses 0.5+


def _call_llm_with_retry(prompt: str, model: str) -> str:
    """Invoke UiPath AI Trust Layer LLM with exponential backoff on transient errors."""
    # Allow tests to force the fallback path deterministically
    if os.getenv("UIPATH_NO_LLM", "").strip().lower() in {"1", "true", "yes"}:
        raise RuntimeError("UIPATH_NO_LLM is set — forcing rule-based fallback.")

    from uipath.llm import complete  # imported lazily so the stub path stays clean

    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return complete(prompt, model=model, temperature=0)
        except Exception as exc:  # noqa: BLE001 — UI path catches broad
            last_error = exc
            if attempt == _MAX_ATTEMPTS - 1:
                break
            # Exponential backoff: 50ms, 100ms, 200ms ...
            time.sleep(_BASE_BACKOFF_SECONDS * (2 ** attempt))
    assert last_error is not None
    raise last_error


def run_medical_necessity_check(active_claim: dict, chart_text: str) -> dict:
    """
    Evaluates whether the clinical documentation supports medical necessity
    for the billed procedure.

    Uses LLM reasoning via UiPath AI Trust Layer when available; gracefully
    degrades to rule-based fallback otherwise. Verdicts are memoized per
    (cpt_code, chart_hash) so the same chart is only billed once per session.
    """
    cpt = active_claim.get("cpt_code", "")
    policy_types = active_claim.get("policy_types", [])

    # Dental and Accident policies typically don't require medical necessity review
    if any(p in {"DENTAL", "ACCIDENT"} for p in policy_types):
        return {
            "approved": True,
            "reasoning": "Policy type exempt from medical necessity review.",
            "confidence": 1.0,
            "flags": [],
        }

    # ── Memoization ──────────────────────────────────────────────────────
    chart_hash = hashlib.sha256((chart_text or "").encode()).hexdigest()[:16]
    cache_key = (str(cpt), chart_hash)
    cached = _cache_get(cache_key)
    if cached is not None:
        print(f"[STAGE 2] Medical necessity: cache HIT (cpt={cpt}, hash={chart_hash}).")
        return cached

    # ── Attempt LLM-powered evaluation via UiPath AI Trust Layer ──────────
    try:
        prompt = f"""You are a medical necessity reviewer for a US healthcare payer.
Evaluate the clinical documentation below and decide whether the billed procedure meets medical necessity criteria.

CPT Code: {cpt}
Clinical Documentation: {chart_text}
Policy Types: {', '.join(policy_types)}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"approved": true or false, "reasoning": "one clear sentence", "confidence": 0.0 to 1.0, "flags": ["flag1", ...]}}
"""
        response = _call_llm_with_retry(prompt, model="gpt-4o")
        result = json.loads(response)
        print(f"[STAGE 2] Medical necessity AI verdict: approved={result['approved']} (confidence: {result['confidence']:.0%})")
        _cache_put(cache_key, result)
        return result

    except Exception as e:
        # ── Graceful degradation: rule-based fallback ────────────────────────
        # Approve if CPT is a routine office visit / standard evaluation code
        routine_cpts = {
            "99201", "99202", "99203", "99204", "99205",   # E/M new patient
            "99211", "99212", "99213", "99214", "99215",   # E/M established patient
        }

        if cpt in routine_cpts:
            print(f"[STAGE 2] Medical necessity: rule-based approval (CPT {cpt} is routine).")
            result = {
                "approved": True,
                "reasoning": f"Rule-based approval: CPT {cpt} is a standard evaluation code.",
                "confidence": 0.7,
                "flags": ["RULE_BASED_FALLBACK"],
            }
            _cache_put(cache_key, result)
            return result

        # Non-routine CPT without AI — suspend for human review
        print(f"[STAGE 2] Medical necessity: AI unavailable ({e}), CPT {cpt} non-routine — routing to clinical director.")
        result = {
            "approved": False,
            "reasoning": f"CPT {cpt} requires clinical director review. AI unavailable.",
            "confidence": 0.5,
            "flags": ["AI_UNAVAILABLE", "CLINICAL_DIRECTOR_REVIEW"],
        }
        _cache_put(cache_key, result)
        return result
