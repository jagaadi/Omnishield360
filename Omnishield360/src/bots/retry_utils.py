"""Retry helpers used by bot automation flows."""

from __future__ import annotations

from typing import Callable, TypeVar

T = TypeVar("T")


def run_with_retry(
    operation: Callable[[], T],
    retries: int = 2,
    retryable_errors: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Run a callable with a small retry loop for transient failures."""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return operation()
        except retryable_errors as exc:
            last_error = exc
            if attempt == retries:
                raise
    if last_error is not None:
        raise last_error
    raise RuntimeError("run_with_retry failed without a captured error")
