"""
Error Recovery and Retry Logic for LangGraph Nodes

Provides decorators and utilities for handling:
- Tool timeouts
- MCP connection errors
- API rate limits
- Transient failures

Based on currentPrompt.md requirements:
- Retry failed tools
- Circuit breaker for persistent failures
- Graceful degradation
"""

import asyncio
import logging
from typing import Callable, Any, Dict, Optional
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff."""
        import random

        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            delay = delay * (0.5 + random.random())  # 50-150% of calculated delay

        return delay


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Failure threshold exceeded, requests blocked
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record successful request."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker: HALF_OPEN -> CLOSED (service recovered)")
                self.state = "CLOSED"
                self.failure_count = 0
                self.success_count = 0
        elif self.state == "CLOSED":
            self.failure_count = 0

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == "CLOSED":
            if self.failure_count >= self.failure_threshold:
                logger.warning(
                    f"Circuit breaker: CLOSED -> OPEN "
                    f"({self.failure_count} failures)"
                )
                self.state = "OPEN"

        elif self.state == "HALF_OPEN":
            logger.warning("Circuit breaker: HALF_OPEN -> OPEN (test failed)")
            self.state = "OPEN"
            self.success_count = 0

    def can_attempt(self) -> bool:
        """Check if request can be attempted."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if recovery timeout elapsed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    logger.info("Circuit breaker: OPEN -> HALF_OPEN (testing recovery)")
                    self.state = "HALF_OPEN"
                    self.success_count = 0
                    return True

            return False

        if self.state == "HALF_OPEN":
            return True

        return False


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for service."""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker()
    return _circuit_breakers[service_name]


def with_retry(
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic to async functions.

    Args:
        retry_config: Retry configuration (uses defaults if None)
        circuit_breaker_name: Name for circuit breaker (disabled if None)
        retryable_exceptions: Tuple of exception types to retry

    Example:
        @with_retry(
            retry_config=RetryConfig(max_retries=3),
            circuit_breaker_name="piapi_mcp",
            retryable_exceptions=(TimeoutError, ConnectionError)
        )
        async def call_mcp_tool(...):
            ...
    """
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            circuit_breaker = get_circuit_breaker(circuit_breaker_name) if circuit_breaker_name else None

            for attempt in range(retry_config.max_retries + 1):
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.can_attempt():
                    logger.warning(
                        f"Circuit breaker '{circuit_breaker_name}' is OPEN, "
                        f"skipping {func.__name__}"
                    )
                    raise Exception(
                        f"Circuit breaker '{circuit_breaker_name}' is OPEN "
                        f"(service unavailable)"
                    )

                try:
                    result = await func(*args, **kwargs)

                    # Success - record it
                    if circuit_breaker:
                        circuit_breaker.record_success()

                    # Log retry success
                    if attempt > 0:
                        logger.info(
                            f"✅ Retry #{attempt} succeeded: {func.__name__}"
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Record failure
                    if circuit_breaker:
                        circuit_breaker.record_failure()

                    # Check if we should retry
                    if attempt < retry_config.max_retries:
                        delay = retry_config.get_delay(attempt)
                        logger.warning(
                            f"⚠️  Retry #{attempt + 1}/{retry_config.max_retries}: "
                            f"{func.__name__} failed with {type(e).__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"❌ Max retries ({retry_config.max_retries}) exceeded "
                            f"for {func.__name__}: {e}"
                        )
                        raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def with_timeout(seconds: float):
    """
    Decorator to add timeout to async functions.

    Args:
        seconds: Timeout in seconds

    Example:
        @with_timeout(30.0)
        async def slow_operation(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"⏱️  Timeout ({seconds}s) exceeded for {func.__name__}"
                )
                raise TimeoutError(
                    f"{func.__name__} exceeded timeout of {seconds}s"
                )

        return wrapper

    return decorator


def safe_node_execution(node_name: str):
    """
    Decorator for LangGraph nodes to handle errors gracefully.

    Ensures nodes always return a dict (never raise unhandled exceptions).

    Args:
        node_name: Name of the node (for logging)

    Example:
        @safe_node_execution("content_creation")
        async def content_creation_node(state: VideoWorkflowState) -> Dict[str, Any]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await func(state)
                return result

            except Exception as e:
                logger.error(
                    f"❌ Node '{node_name}' failed: {type(e).__name__}: {e}",
                    exc_info=True
                )

                # Return error state update
                return {
                    "workflow_status": "failed",
                    "current_phase": node_name,
                    "error_message": f"{node_name} failed: {str(e)}",
                    "retry_count": state.get("retry_count", 0) + 1,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }

        return wrapper

    return decorator


# Predefine common retry configurations

FAST_RETRY = RetryConfig(
    max_retries=2,
    initial_delay=0.5,
    max_delay=5.0
)

STANDARD_RETRY = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0
)

PERSISTENT_RETRY = RetryConfig(
    max_retries=5,
    initial_delay=2.0,
    max_delay=60.0
)


# Common retryable exception types

TRANSIENT_ERRORS = (
    TimeoutError,
    ConnectionError,
    asyncio.TimeoutError,
)

API_ERRORS = (
    TimeoutError,
    ConnectionError,
    # Add specific API client exceptions here
)

MCP_ERRORS = (
    TimeoutError,
    ConnectionError,
    # Add MCP-specific exceptions here
)
