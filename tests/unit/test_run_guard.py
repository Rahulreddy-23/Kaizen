"""Ordinary requests stay parallel; purge must exclude both reads and writes."""
import asyncio

from kaizen.api.run_guard import RunRequestGuard


def test_purge_conflicts_with_inflight_stream_and_blocks_new_requests():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        messages = []
        async def app(scope, receive, send):
            entered.set()
            await release.wait()
        async def send(message):
            messages.append(message)
        async def receive():
            return {'type': 'http.disconnect'}
        guard = RunRequestGuard(app)
        read = {'type': 'http', 'method': 'GET', 'path': '/api/runs/one/documents/pdf'}
        purge = {'type': 'http', 'method': 'DELETE', 'path': '/api/runs/one/permanent'}
        active = asyncio.create_task(guard(read, receive, send))
        await entered.wait()
        await guard(purge, receive, send)
        assert messages[0]['status'] == 409
        release.set()
        await active
        entered.clear()
        release.clear()
        messages.clear()
        active = asyncio.create_task(guard(purge, receive, send))
        await entered.wait()
        await guard(read, receive, send)
        assert messages[0]['status'] == 409
        release.set()
        await active
        assert guard._active == {} and guard._purging == set()
    asyncio.run(scenario())
