"""Evicted parsed runs remain available from the private workspace on disk."""

from kaizen.api.app import RunCache
from kaizen.workspace import Workspace
from tests.unit.test_quick_view import fixture


def test_cache_evicts_least_recently_read_and_reloads_from_disk(tmp_path):
    ws = Workspace(tmp_path / 'workspace')
    cache = RunCache(ws, max_entries=2)
    try:
        for name in ('first', 'second'):
            run = fixture()
            run.metadata.run_id = name
            cache.put(run)
        assert cache.get('first').metadata.run_id == 'first'
        run = fixture()
        run.metadata.run_id = 'third'
        cache.put(run)
        assert list(cache._runs) == ['first', 'third']
        assert cache.get('second').metadata.run_id == 'second'
        assert list(cache._runs) == ['third', 'second']
        assert len(ws.runs.list()) == 3
    finally:
        ws.db.close()
