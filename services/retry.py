import time
from typing import Callable, TypeVar


Result = TypeVar("Result")


def retry_call(
    operation: Callable[[], Result],
    attempts: int,
    base_delay_seconds: float,
    retryable: tuple[type[Exception], ...] = (Exception,),
) -> Result:
    """Run an external operation with bounded exponential backoff."""
    for attempt in range(attempts):
        try:
            return operation()
        except retryable:
            if attempt == attempts - 1:
                raise
            time.sleep(base_delay_seconds * (2 ** attempt))
    raise RuntimeError("Retry loop completed without a result")