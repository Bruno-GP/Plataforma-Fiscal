from __future__ import annotations

import time
from collections import OrderedDict
from functools import wraps
from threading import RLock
from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(item) for item in value))
    return value


def ttl_cache(ttl_seconds: float = 10.0, maxsize: int = 256) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        cache: OrderedDict[Any, tuple[float, Any]] = OrderedDict()
        lock = RLock()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key_args = args[1:] if args and hasattr(args[0], func.__name__) else args
            key = (_freeze(key_args), _freeze(kwargs))
            now = time.monotonic()

            with lock:
                cached = cache.get(key)
                if cached and cached[0] > now:
                    cache.move_to_end(key)
                    return cached[1]
                if cached:
                    cache.pop(key, None)

            result = func(*args, **kwargs)

            with lock:
                cache[key] = (now + ttl_seconds, result)
                cache.move_to_end(key)
                while len(cache) > maxsize:
                    cache.popitem(last=False)

            return result

        def cache_clear() -> None:
            with lock:
                cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
