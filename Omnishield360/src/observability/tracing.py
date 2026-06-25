"""
OmniShield 360 - Lightweight observability primitives.

A `span` is a labelled region of execution with attributes and a duration.
We don't depend on the OpenTelemetry SDK — we emit a structured `[TRACE]`
log line that UiPath Orchestrator already routes to Jobs → Logs, and we
also call `sdk.logs.write_information` when cloud credentials are present
so the trace appears in Maestro's timeline.

Usage:
    from src.observability import span

    with span("stage.ocr.gate") as s:
        s.set("confidence", 0.97)
        s.set("threshold", 0.85)
        # ... do work ...
"""

from __future__ import annotations

import os
import time
import uuid
import importlib
from contextlib import contextmanager
from typing import Any, Iterator

otel_trace: Any = None
try:
    otel_trace = importlib.import_module("opentelemetry.trace")
except ImportError:  # pragma: no cover - structured logging remains available
    pass


# A single trace ID per `main()` invocation. Spans inherit it implicitly via
# the `span()` context manager. We don't need a global mutable — spans
# just print the trace_id with each emission.
_TRACE_ID: str = ""


def current_trace_id() -> str:
    return _TRACE_ID


def new_trace_id() -> str:
    global _TRACE_ID
    _TRACE_ID = uuid.uuid4().hex[:12]
    return _TRACE_ID


def _emit(name: str, duration_ms: float, attrs: dict[str, Any]) -> None:
    """Stream a trace line. Best-effort write to Orchestrator logs."""
    trace_id = _TRACE_ID or "-"
    payload = f"[TRACE] {name} | trace_id={trace_id} | dur_ms={duration_ms:.2f} | attrs={attrs}"
    print(payload)
    try:
        from uipath.platform import UiPath

        sdk = UiPath()
        folder = os.getenv("UIPATH_FOLDER_NAME", "Healthcare_Operations_Prod")
        sdk.logs.write_information(folder_path=folder, message=payload)
    except Exception:
        # Local fallback only — Orchestrator log write is best-effort
        pass


class _Span:
    def __init__(self, name: str, otel_span: Any = None) -> None:
        self.name = name
        self.attrs: dict[str, Any] = {}
        self._start: float = 0.0
        self._otel_span = otel_span

    def set(self, key: str, value: Any) -> None:
        self.attrs[key] = value
        if self._otel_span is not None:
            self._otel_span.set_attribute(key, value)


@contextmanager
def span(name: str, **initial_attrs: Any) -> Iterator[_Span]:
    """
    Context-manager span. Auto-closes on exit, measures wall-clock duration,
    and emits a single structured log line.

    Example:
        with span("stage.ocr.gate", claim_id=claim_id) as s:
            s.set("confidence", conf)
    """
    if not _TRACE_ID:
        new_trace_id()
    tracer = otel_trace.get_tracer("omnishield360") if otel_trace is not None else None
    otel_context = tracer.start_as_current_span(name) if tracer is not None else None
    otel_span = otel_context.__enter__() if otel_context is not None else None
    s = _Span(name, otel_span)
    for key, value in initial_attrs.items():
        s.set(key, value)
    t0 = time.monotonic()
    try:
        yield s
    except Exception as exc:
        if otel_span is not None:
            otel_span.record_exception(exc)
        raise
    finally:
        duration_ms = (time.monotonic() - t0) * 1000.0
        _emit(name, duration_ms, s.attrs)
        if otel_context is not None:
            otel_context.__exit__(None, None, None)
