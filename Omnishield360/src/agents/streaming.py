"""
OmniShield 360 - Streaming OCR Confidence Monitor
Aggregates a stream of per-region confidence scores emitted by Document
Understanding into a single gating decision, with a small per-event log
stream that lands in the Orchestrator Jobs panel.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StreamingConfidenceMonitor:
    """
    Collects OCR confidence samples and surfaces a single gating verdict.

    The monitor mirrors the production UiPath DU streaming output: each
    region (header, body, footer, signature) emits a confidence value as
    it is processed. We pick the *minimum* — because a single low-confidence
    region can still poison an entire document — and stream every sample
    to the Orchestrator log so the operator can see the worst case live.
    """

    threshold: float = 0.85
    samples: list[tuple[float, float]] = field(default_factory=list)  # (timestamp, value)
    _emitted: int = 0

    def add_sample(self, value: float, region: str = "region") -> None:
        now = time.monotonic()
        self.samples.append((now, float(value)))
        self._emitted += 1
        # Stream every sample to stdout — UiPath routes print() to Job Logs
        # and UiPath Integration Service also picks them up via the local
        # file collector. Avoids a black-box 30s wait.
        print(f"[DU-STREAM] sample {self._emitted:>2} | region={region:<10} | confidence={value:.3f}")

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {"min": 0.0, "max": 0.0, "mean": 0.0, "samples": 0, "passed": False}
        values = [v for _, v in self.samples]
        return {
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "samples": len(values),
            "passed": min(values) >= self.threshold,
        }

    def gate_value(self) -> float:
        """Returns the minimum sample (the most conservative gate value)."""
        if not self.samples:
            return 0.0
        return min(v for _, v in self.samples)


def _read_input_confidence(base: float) -> float:
    """Allow tests to force the gate to pass/fail deterministically."""
    override = os.getenv("UIPATH_DU_OVERRIDE_CONFIDENCE", "").strip()
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    return base


def build_streaming_samples(base_confidence: float, *, n: int = 5, jitter: float = 0.02) -> list[float]:
    """
    Produces a deterministic spread of N samples around `base_confidence`.

    The spread is fully deterministic — based on a hash of the value — so
    the same input always produces the same gate. This is important for
    test repeatability: run_tests.py checks expected_status and we don't
    want flaky random confidence values to push a claim into the wrong
    branch.
    """
    import hashlib

    seed = int(hashlib.sha256(f"{base_confidence:.4f}".encode()).hexdigest(), 16)
    # xorshift-style deterministic pseudo-random walk
    state = seed & 0xFFFFFFFF
    samples: list[float] = []
    for _ in range(n):
        state ^= (state << 13) & 0xFFFFFFFF
        state ^= (state >> 17) & 0xFFFFFFFF
        state ^= (state << 5) & 0xFFFFFFFF
        state &= 0xFFFFFFFF
        normalized = (state & 0xFFFF) / 0xFFFF  # 0..1
        offset = (normalized - 0.5) * 2.0 * jitter
        samples.append(max(0.0, min(1.0, base_confidence + offset)))
    return samples


def stream_document_understanding(raw_chart_text: str, base_confidence: float, threshold: float = 0.85) -> tuple[StreamingConfidenceMonitor, float]:
    """
    Simulate a streaming DU pipeline: emit N region samples, return the
    monitor and the gating value (min sample).
    """
    monitor = StreamingConfidenceMonitor(threshold=threshold)
    samples = build_streaming_samples(_read_input_confidence(base_confidence))
    # Modulate the spread by length to make long charts slightly more variable
    # (a real production DU is more likely to fail on a long, mixed-media chart)
    length_factor = min(0.02, len(raw_chart_text or "") / 10000.0)
    samples = [max(0.0, min(1.0, s + (length_factor * (i / max(1, len(samples) - 1))))) for i, s in enumerate(samples)]
    for i, v in enumerate(samples):
        region = ["header", "body", "footer", "signature", "amendment"][i % 5]
        monitor.add_sample(v, region=region)
    print(
        f"[DU-STREAM] {len(samples)} samples | min={monitor.summary()['min']:.3f} | "
        f"max={monitor.summary()['max']:.3f} | mean={monitor.summary()['mean']:.3f} | "
        f"gate={'PASS' if monitor.gate_value() >= threshold else 'HALT'}"
    )
    return monitor, monitor.gate_value()
