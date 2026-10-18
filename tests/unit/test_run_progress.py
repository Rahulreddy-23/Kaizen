"""A slow OCR page must keep its HTTP stream alive without inventing progress."""

import asyncio
import json
import time

from kaizen.api import run_progress


def test_idle_work_emits_heartbeats_and_still_returns_the_saved_result(monkeypatch):
    monkeypatch.setattr(run_progress, 'HEARTBEAT_SECONDS', .005)

    def work(report):
        report(10, 'Reading page')
        time.sleep(.04)
        return {'run_id': 'saved'}

    async def collect():
        response = run_progress.stream_run(work)
        return [json.loads(chunk) async for chunk in response.body_iterator]

    events = asyncio.run(collect())
    assert any(event['type'] == 'heartbeat' for event in events)
    assert [event['percent'] for event in events if event['type'] == 'progress'] == [0, 10]
    assert events[-1] == {'type': 'result', 'data': {'run_id': 'saved'}}
