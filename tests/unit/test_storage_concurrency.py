"""One SQLite connection, many API threads: every statement must be serialised, reads included.

Seen live: the mining page fires the worklist and the suggestions requests together; both read decisions and
relationships on the shared connection and one of them died with `sqlite3.InterfaceError: bad parameter or
other API misuse`. The connection wrapper now takes the lock for every statement and hands back materialised
rows, so no cursor is ever stepped outside the lock.
"""

import threading

from kaizen.review.store import ReviewStore
from kaizen.storage.db import Database
from kaizen.workspace import Workspace


def test_concurrent_reads_and_writes_on_the_shared_connection_do_not_raise(tmp_path):
    ws = Workspace(tmp_path / "ws")
    store = ReviewStore(ws.db)
    errors: list[BaseException] = []

    def guarded(fn):
        def run():
            try:
                fn()
            except BaseException as e:
                errors.append(e)
        return run

    def writer(i: int):
        for k in range(25):
            store.mark_opened("run", f"R-{i}-{k}", 1)
            store.decide("run", f"R-{i}-{k}", 1, "Dharma", "ACCEPT")

    def reader():
        for _ in range(60):
            store.all_decisions("run")
            store.finals("run")
            ws.repository.list()
            list(ws.db.conn.execute("SELECT * FROM audit"))
            store.state_counts("run", [])

    threads = [threading.Thread(target=guarded(lambda i=i: writer(i))) for i in range(6)]
    threads += [threading.Thread(target=guarded(reader)) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [], f"{len(errors)} thread(s) failed, first: {errors[0]!r}"
    assert len(store.all_decisions("run")) == 6 * 25


def test_rows_are_usable_after_the_statement_returns(tmp_path):
    db = Database(tmp_path / "bare.db")  # no seeded relationships, so the audit log starts empty
    db.audit("t", "x", "1")
    db.audit("t", "x", "2")
    db.conn.commit()
    rows = db.conn.execute("SELECT actor, action, detail FROM audit ORDER BY seq")
    first = rows.fetchone()
    assert first["detail"] == "1" and [r["detail"] for r in rows] == ["2"]
    assert db.conn.execute("SELECT COUNT(*) AS n FROM audit").fetchone()["n"] == 2
    assert db.conn.execute("SELECT * FROM audit WHERE detail = 'nope'").fetchone() is None
    assert db.conn.execute("SELECT * FROM audit").fetchall()[1]["detail"] == "2"
