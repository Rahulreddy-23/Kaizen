"""Keep permanent erasure from racing file responses or in-flight run writes.

Ordinary requests remain parallel. A purge fails fast with a retryable conflict
if the run is in use, and blocks new requests until its response completes.
"""
import re
import threading
from collections.abc import Callable
from urllib.parse import unquote

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse


class RunRequestGuard:
    def __init__(self, app, original_id: Callable[[str], str] | None = None):
        self.app = app
        self._original_id = original_id
        self._lock = threading.Lock()
        self._active: dict[str, int] = {}
        self._purging: set[str] = set()

    async def __call__(self, scope, receive, send):
        match = re.fullmatch(r'/api/runs/([^/]+)(/.*)?', scope.get('path', '')) if scope['type'] == 'http' else None
        if not match:
            return await self.app(scope, receive, send)
        rid = unquote(match[1])
        if self._original_id is not None:
            rid = await run_in_threadpool(self._original_id, rid)
        purge = scope['method'] == 'DELETE' and match[2] == '/permanent'
        with self._lock:
            conflict = rid in self._purging or (purge and self._active.get(rid, 0) > 0)
            if not conflict:
                if purge:
                    self._purging.add(rid)
                self._active[rid] = self._active.get(rid, 0) + 1
        if conflict:
            return await JSONResponse({'detail': 'This run is in use. Wait for its requests to finish, then try again.'}, status_code=409)(scope, receive, send)
        try:
            await self.app(scope, receive, send)
        finally:
            with self._lock:
                self._active[rid] -= 1
                if not self._active[rid]:
                    del self._active[rid]
                if purge:
                    self._purging.discard(rid)
