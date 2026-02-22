import asyncio
import logging
import random
import time
from functools import wraps
from typing import Callable, Any, Type, Union, Tuple

logger = logging.getLogger(__name__)

def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retry_on: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Exponential backoff decorator.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except retry_on as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class CircuitBreaker:
    """
    Simple in-memory circuit breaker.
    In a real production environment, this would use Redis.
    """
    def __init__(self, service_name: str, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit for {self.service_name} is now OPEN")

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_proceed(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True # HALF_OPEN

_circuit_breakers = {}

def with_circuit_breaker(service_name: str):
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(service_name)
    
    cb = _circuit_breakers[service_name]
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cb.can_proceed():
                raise Exception(f"Circuit breaker for {service_name} is OPEN")
            try:
                result = await func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise e
        return wrapper
    return decorator

def async_timeout_wrapper(seconds: int):
    """Async context manager wrapper for timeouts."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout of {seconds}s reached for {func.__name__}")
                raise
        return wrapper
    return decorator
