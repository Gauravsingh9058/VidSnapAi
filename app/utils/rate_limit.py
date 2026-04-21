import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, request


_RATE_LIMIT_BUCKETS = defaultdict(deque)


def rate_limit(key_prefix, limit=10, window_seconds=60):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            remote = request.headers.get("X-Forwarded-For", request.remote_addr or "anonymous")
            bucket_key = f"{key_prefix}:{remote}"
            timestamps = _RATE_LIMIT_BUCKETS[bucket_key]
            now = time.time()

            while timestamps and now - timestamps[0] > window_seconds:
                timestamps.popleft()

            if len(timestamps) >= limit:
                abort(429)

            timestamps.append(now)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
