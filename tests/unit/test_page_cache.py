from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from kaizen.api.page_cache import PageImageCache


def test_lru_is_bounded_by_bytes_and_oversized_pages_are_not_retained():
    cache = PageImageCache(max_bytes=6)
    cache.get('a', lambda: b'aaa')
    cache.get('b', lambda: b'bbb')
    assert cache.get('a', lambda: pytest.fail('cache miss')) == b'aaa'
    cache.get('c', lambda: b'ccc')
    assert list(cache._images) == ['a', 'c']
    assert cache._bytes == 6
    assert cache.get('huge', lambda: b'1234567') == b'1234567'
    assert 'huge' not in cache._images and cache._bytes == 6


def test_concurrent_same_page_joins_one_render_and_failures_can_be_retried():
    cache = PageImageCache()
    entered, release = Event(), Event()
    calls = []

    def render():
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return b'page'

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(cache.get, 'page', render)
        assert entered.wait(5)
        second = pool.submit(cache.get, 'page', render)
        release.set()
        assert first.result(5) == second.result(5) == b'page'
    assert len(calls) == 1
    with pytest.raises(ValueError):
        cache.get('bad', lambda: (_ for _ in ()).throw(ValueError('broken source')))
    assert cache.get('bad', lambda: b'recovered') == b'recovered'
