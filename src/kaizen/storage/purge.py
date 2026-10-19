"""Owner-controlled run erasure, with durable retries for interrupted file removal.

Only app-managed run/upload directories are eligible. Local input folders and
shared terminology are never removed. SQLite reuses freed pages on later writes;
we deliberately avoid a blocking full-database VACUUM during a web request.
"""

import json
import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

RUN_TABLES = (
    'run_shares', 'review_events', 'run_relationships', 'decisions',
    'action_items', 'finals', 'row_views', 'learning_enrollments',
    'learning_labels', 'learning_drawings', 'learning_evaluations', 'learning_jobs',
)


def _managed(ws, path: Path) -> bool:
    """A direct child of our real runs/uploads folder, without symlink traversal."""
    root = ws.path.resolve()
    return (path.parent in (root / 'runs', root / 'uploads')
            and path.parent.resolve() == path.parent
            and path.resolve() == path
            and bool(re.fullmatch(r'[A-Za-z0-9_-]+', path.name)))


def _references(record: dict) -> list[Path] | None:
    """Include deleted runs and legacy imports whose files lie outside input_root."""
    root = Path(record['input_root']).resolve()
    try:
        data = json.loads(Path(record['json_path']).read_text())
        paths = [root, Path(record['json_path']).resolve()]
        sources = [d['path'] for d in data.get('documents', [])]
        sources.extend(i['path'] for i in data.get('metadata', {}).get('inputs', []))
        paths.extend((Path(p) if Path(p).is_absolute() else root / p).resolve() for p in sources)
        return paths
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        # Unknown legacy references are a reason to preserve files, never guess.
        return None


def cleanup_files(ws, run_id: str) -> bool:
    """Return False on an I/O failure; the committed queue survives a restart."""
    with ws.db.transaction():
        job = ws.db.conn.execute('SELECT paths FROM run_file_cleanup WHERE run_id=?', (run_id,)).fetchone()
        if job is None:
            return True
        for value in json.loads(job['paths']):
            path = Path(value)
            if not _managed(ws, path):
                logger.error('Run file cleanup refused an unmanaged directory')
                return False
            try:
                if path.exists():
                    shutil.rmtree(path)
            except OSError:
                logger.warning('Run file cleanup deferred after an I/O failure')
                return False
        ws.db.conn.execute('DELETE FROM run_file_cleanup WHERE run_id=?', (run_id,))
    return True


def resume_cleanup(ws) -> None:
    for job in ws.db.conn.execute('SELECT run_id FROM run_file_cleanup'):
        cleanup_files(ws, job['run_id'])


def purge_run(ws, run_id: str, actor: str) -> dict:
    """Caller guards in-flight requests/jobs. Recheck ownership in the transaction."""
    with ws.db.transaction():
        ws.db.conn.execute('PRAGMA secure_delete=ON')
        record = ws.runs.get(run_id, include_deleted=True)
        if not record or record['owner'] != actor:
            raise KeyError(run_id)
        if not record['deleted_at']:
            raise ValueError('Move this run to Deleted runs before deleting it permanently.')
        root = ws.path.resolve()
        candidates = [root / 'runs' / run_id]
        source = Path(record['input_root']).resolve()
        # Uploaded sources have an isolated UUID directory. Never erase local
        # folders, demo inputs, or the shared uploads/runs parent itself.
        try:
            upload_id = source.relative_to(root / 'uploads').parts[0]
            if re.fullmatch(r'[0-9a-f]{32}', upload_id):
                candidates.append(root / 'uploads' / upload_id)
        except (ValueError, IndexError):
            pass
        others = [dict(r) for r in ws.db.conn.execute('SELECT * FROM runs WHERE run_id != ?', (run_id,))]
        references = [_references(r) for r in others]
        paths = [p for p in candidates if _managed(ws, p) and all(
            refs is not None and not any(ref == p or p in ref.parents for ref in refs)
            for refs in references
        )]
        # Keeping the queue and erasure in one commit makes retries crash-safe.
        # A retained shared source can be reclaimed when its last run is purged.
        ws.db.conn.execute('INSERT INTO run_file_cleanup VALUES (?,?)', (run_id, json.dumps([str(p) for p in paths])))
        for table in RUN_TABLES:
            ws.db.conn.execute(f'DELETE FROM {table} WHERE run_id=?', (run_id,))
        ws.db.conn.execute("UPDATE action_items SET resolved_in_run='' WHERE resolved_in_run=?", (run_id,))
        ws.db.conn.execute("UPDATE runs SET copied_from='' WHERE copied_from=?", (run_id,))
        ws.db.conn.execute('DELETE FROM runs WHERE run_id=?', (run_id,))
        # Keep a minimal deletion receipt, without retaining old run-specific
        # audit details (which can contain annotation/review text).
        ws.db.conn.execute('DELETE FROM audit WHERE instr(detail,?) > 0', (run_id,))
        ws.db.audit(actor, 'run.permanently_deleted', run_id)
    complete = cleanup_files(ws, run_id)
    return {'run_id': run_id, 'deleted': True, 'cleanup_pending': not complete,
            'files_retained': any(p.exists() for p in candidates if p not in paths)}
