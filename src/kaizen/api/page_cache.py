"""Bounded, process-local page images; never persisted or shared with a CDN."""

from collections import OrderedDict
from concurrent.futures import Future
from threading import Lock
from typing import Callable, Hashable


class PageImageCache:
    def __init__(self, max_bytes: int = 64 * 1024 * 1024):
        self.max_bytes = max_bytes
        self._bytes = 0
        self._images: OrderedDict[Hashable, bytes] = OrderedDict()
        self._pending: dict[Hashable, Future] = {}
        self._lock = Lock()

    def get(self, key: Hashable, render: Callable[[], bytes]) -> bytes:
        # The route must authenticate, authorize and stat the source before calling.
        with self._lock:
            if key in self._images:
                self._images.move_to_end(key)
                return self._images[key]
            pending = self._pending.get(key)
            owner = pending is None
            if owner:
                pending = self._pending[key] = Future()
        if not owner:
            return pending.result()
        try:
            image = render()
            with self._lock:
                if len(image) <= self.max_bytes:
                    while self._bytes + len(image) > self.max_bytes:
                        _, old = self._images.popitem(last=False)
                        self._bytes -= len(old)
                    self._images[key] = image
                    self._bytes += len(image)
            pending.set_result(image)
            return image
        except BaseException as exc:
            pending.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._pending.pop(key, None)
