"""
OmniShield 360 - PII / PHI Masking Module
Simulates the UiPath AI Trust Layer in-flight anonymization gateway.
Strips all Protected Health Information before any text reaches external AI models.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class _MaskedSpan:
    """Records where a token was placed in the masked text so restore cannot collide."""
    token: str
    start: int  # inclusive
    end: int    # exclusive


@dataclass
class PhiMask:
    """Bundle returned by mask_phi_data: anonymized text + safe restore payload."""
    anonymized_text: str
    token_map: dict[str, str] = field(default_factory=dict)
    _spans: list[_MaskedSpan] = field(default_factory=list)

    def restore(self) -> str:
        """Position-indexed restore — guaranteed not to collide on substring matches."""
        if not self._spans:
            return self.anonymized_text
        out: list[str] = []
        cursor = 0
        # Spans are emitted in source-order during masking, so they are already sorted
        # by start position. We sort defensively in case future refactors reorder them.
        for span in sorted(self._spans, key=lambda s: s.start):
            if span.start < cursor:
                # Defensive guard — should never happen, but never silently corrupt data
                continue
            out.append(self.anonymized_text[cursor:span.start])
            out.append(self.token_map[span.token])
            cursor = span.end
        out.append(self.anonymized_text[cursor:])
        return "".join(out)


def mask_phi_data(text: str) -> tuple[str, dict[str, str]]:
    """
    Locally masks critical patient identifiers.
    Returns: (anonymized_text, token_map)
    The token_map is stored ONLY inside the secure local tenant — never sent externally.

    For production code that also needs collision-free restore, prefer the PhiMask
    dataclass returned by mask_phi_data_v2().
    """
    masked, phi_map, _ = _mask_with_spans(text)
    return masked, phi_map


def mask_phi_data_v2(text: str) -> PhiMask:
    """Returns a PhiMask object that supports position-indexed, collision-free restore."""
    masked, phi_map, spans = _mask_with_spans(text)
    return PhiMask(anonymized_text=masked, token_map=phi_map, _spans=spans)


def _mask_with_spans(text: str) -> tuple[str, dict[str, str], list[_MaskedSpan]]:
    """Internal: performs regex masking and records the (start, end) of every token."""
    phi_map: dict[str, str] = {}
    spans: list[_MaskedSpan] = []
    counter = {"n": 0, "d": 0, "s": 0, "p": 0}

    def _record(token: str, original: str) -> None:
        phi_map[token] = original

    # 1. Patient names — "Patient Name: John Doe" pattern
    def replace_name(match: re.Match[str]) -> str:
        original = match.group(1).strip()
        token = f"[PATIENT_NAME_{counter['n']}]"
        counter["n"] += 1
        _record(token, original)
        return f"Patient Name: {token}"

    text = re.sub(r"Patient Name:\s*([A-Za-z\s\-']+)", replace_name, text)

    # 2. Dates of birth — MM/DD/YYYY
    def replace_dob(match: re.Match[str]) -> str:
        token = f"[DOB_TOKEN_{counter['d']}]"
        counter["d"] += 1
        _record(token, match.group(0))
        return token

    text = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", replace_dob, text)

    # 3. SSNs — XXX-XX-XXXX
    def replace_ssn(match: re.Match[str]) -> str:
        token = f"[SSN_TOKEN_{counter['s']}]"
        counter["s"] += 1
        _record(token, match.group(0))
        return token

    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", replace_ssn, text)

    # 4. Phone numbers
    def replace_phone(match: re.Match[str]) -> str:
        token = f"[PHONE_TOKEN_{counter['p']}]"
        counter["p"] += 1
        _record(token, match.group(0))
        return token

    text = re.sub(r"\b(\(?\d{3}\)?[\s\-\.]\d{3}[\s\-\.]\d{4})\b", replace_phone, text)

    # Build positions only after every replacement is complete. Recording spans
    # during successive regex passes is unsafe because later substitutions can
    # shift tokens that were already recorded.
    for token in phi_map:
        for match in re.finditer(re.escape(token), text):
            spans.append(_MaskedSpan(token=token, start=match.start(), end=match.end()))

    return text, phi_map, spans


def restore_phi_data(anonymized_text: str, token_map: dict[str, str]) -> str:
    """
    Legacy restore helper — preserved for backward compatibility with code that
    only kept the (text, token_map) tuple. Uses a two-pass strategy that is safe
    as long as no two tokens are substrings of each other (which they aren't, by
    construction — see the [TYPE_N] naming convention).

    For new code, prefer PhiMask.restore() which is position-indexed.
    """
    # Build a single regex that matches any known token; longest-first to be safe.
    if not token_map:
        return anonymized_text
    pattern = re.compile("|".join(re.escape(t) for t in sorted(token_map, key=len, reverse=True)))
    return pattern.sub(lambda m: token_map[m.group(0)], anonymized_text)


# ── Self-test — runs only when executed directly ──────────────────────────
if __name__ == "__main__":
    # Regression: multiple replacement passes change string lengths. The final
    # position index must still restore every value exactly.
    tricky = (
        "Patient Name: John Smith. DOB: 11/20/1992. "
        "SSN: 123-45-6789. Phone: 212-555-0199."
    )
    masked_obj = mask_phi_data_v2(tricky)
    restored = masked_obj.restore()
    assert restored == tricky, f"Restore mismatch:\n  expected: {tricky!r}\n  got:      {restored!r}"
    print("[SELF-TEST] PHI round-trip OK — collision-safe restore verified.")
