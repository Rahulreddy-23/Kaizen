"""Request-scoped progress streams; no shared job IDs or cross-account state."""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

Progress = Callable[[int, str], None]
HEARTBEAT_SECONDS = 15


def stream_run(work: Callable[[Progress], Any]) -> StreamingResponse:
    async def events():
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def report(percent, stage):
            loop.call_soon_threadsafe(queue.put_nowait, {'type': 'progress', 'percent': percent, 'stage': stage})

        async def execute():
            try:
                result = await run_in_threadpool(work, report)
                await queue.put({'type': 'result', 'data': result})
            except HTTPException as exc:
                await queue.put({'type': 'error', 'status': exc.status_code, 'detail': exc.detail})
            except Exception:
                reference = uuid.uuid4().hex[:12]
                logging.getLogger(__name__).exception('Cross-check failed. Error reference: %s', reference)
                await queue.put({'type': 'error', 'status': 500, 'detail': f'Cross-check failed. Error reference: {reference}'})

        task = asyncio.create_task(execute())
        try:
            yield json.dumps({'type': 'progress', 'percent': 0, 'stage': 'Preparing documents'}) + '\n'
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
                except TimeoutError:
                    # Long OCR pages need no invented percentage, but a live
                    # stream must not look idle to an upstream HTTP proxy.
                    yield json.dumps({'type': 'heartbeat'}) + '\n'
                    continue
                yield json.dumps(event) + '\n'
                if event['type'] != 'progress':
                    break
        finally:
            # OCR cannot be interrupted safely. Keep the worker and its cleanup alive if a tab closes.
            await asyncio.shield(task)

    return StreamingResponse(events(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store', 'X-Accel-Buffering': 'no'})
