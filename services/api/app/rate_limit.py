"""Small single-process limiter for local MVP auth endpoints.

Production deployments should replace this with a shared Redis-backed limiter so
limits are consistent across workers and instances.
"""
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import Request
from fastapi.responses import JSONResponse

_requests: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()

async def auth_rate_limit(request: Request, call_next):
    limited_paths={
        '/auth/register','/auth/login','/auth/refresh','/auth/verify-email',
        '/auth/password/request-reset','/auth/password/confirm-reset',
    }
    # Session reads and logout are authenticated operations and must not share
    # the anti-brute-force bucket used by credential endpoints.
    if request.url.path not in limited_paths or request.method == 'OPTIONS':
        return await call_next(request)
    address = request.client.host if request.client else 'unknown'
    key = f'{address}:{request.url.path}'
    now = monotonic()
    with _lock:
        bucket = _requests[key]
        while bucket and bucket[0] < now - 60:
            bucket.popleft()
        if len(bucket) >= 10:
            return JSONResponse({'detail':'Demasiados intentos. Vuelve a intentarlo en un minuto.'},status_code=429,headers={'Retry-After':'60'})
        bucket.append(now)
        if len(_requests) > 5000:
            for old_key in [k for k,v in _requests.items() if not v or v[-1] < now-60]:
                _requests.pop(old_key,None)
    return await call_next(request)
