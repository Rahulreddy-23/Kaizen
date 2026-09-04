"""Reviewer sessions: who is reviewing, in which slot, and whether they are blind.

Identity used to be a name typed into the browser and blind mode a query parameter, so a reviewer could
switch either of them client-side. Both now live here. The server issues an opaque token, stores the
slot and the blind flag against it, and derives blind mode from the workspace policy rather than from
anything the caller sends. Changing the policy or opening a session is an audit event.

This is not authentication: anyone with access to the machine can open a session under any name. It
makes the reviewer's identity and the blind flag *server-side, explicit and audited*, which is what an
independent-review process needs. A shared deployment still needs real sign-in (see
`docs/security-review.md`).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from kaizen.storage.db import Database

BLIND_REVIEW_KEY = "blind_review"
POLICY_REQUIRED = "required"
POLICY_OPTIONAL = "optional"
POLICIES = (POLICY_REQUIRED, POLICY_OPTIONAL)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class ReviewSession:
    """An open review session. `blind` is decided by the server, never by the client."""

    token: str
    reviewer: str
    slot: int
    blind: bool
    created_at: str

    def to_dict(self, policy: str) -> dict:
        """Session as the API returns it. The token is never included; it travels in a cookie."""
        return {"reviewer": self.reviewer, "slot": self.slot, "blind": self.blind, "created_at": self.created_at, "blind_review_policy": policy}


class SessionStore:
    def __init__(self, db: Database):
        self.db = db
        self.conn = db.conn

    # ---- policy ---------------------------------------------------------------------------------

    def policy(self) -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (BLIND_REVIEW_KEY,)).fetchone()
        return row["value"] if row and row["value"] in POLICIES else POLICY_REQUIRED

    def set_policy(self, value: str, by: str) -> str:
        if value not in POLICIES:
            raise ValueError(f"blind review policy must be one of {', '.join(POLICIES)}")
        with self.db.lock:
            self.conn.execute(
                "INSERT INTO settings (key, value, updated_at, updated_by) VALUES (?,?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at, updated_by = excluded.updated_by",
                (BLIND_REVIEW_KEY, value, _now(), by),
            )
            self.db.audit(by, "session.policy", f"blind review policy set to {value}")
            self.conn.commit()
        return value

    def blind_for(self, slot: int, requested: bool | None = None) -> bool:
        """Blind mode for a slot. Reviewer 1 is never blind; reviewer 2 is blind whenever the policy
        requires it, and may only be unblinded when the policy is optional."""
        if slot != 2:
            return False
        if self.policy() == POLICY_REQUIRED:
            return True
        return True if requested is None else bool(requested)

    # ---- sessions -------------------------------------------------------------------------------

    def open(self, reviewer: str, slot: int, blind: bool | None = None) -> ReviewSession:
        name = (reviewer or "").strip()
        if not name:
            raise ValueError("a reviewer name is required: decisions are recorded against it")
        if slot not in (1, 2):
            raise ValueError("reviewer slot must be 1 (facilitator) or 2 (independent reviewer)")
        s = ReviewSession(secrets.token_urlsafe(32), name, slot, self.blind_for(slot, blind), _now())
        with self.db.lock:
            self.conn.execute(
                "INSERT INTO sessions (token, reviewer, slot, blind, created_at, last_seen_at, ended_at) VALUES (?,?,?,?,?,?,'')",
                (s.token, s.reviewer, s.slot, int(s.blind), s.created_at, s.created_at),
            )
            self.db.audit(s.reviewer, "session.open", f"slot {s.slot}, blind {'on' if s.blind else 'off'} (policy {self.policy()})")
            self.conn.commit()
        return s

    def resolve(self, token: str | None) -> ReviewSession | None:
        if not token:
            return None
        row = self.conn.execute("SELECT * FROM sessions WHERE token = ? AND ended_at = ''", (token,)).fetchone()
        if row is None:
            return None
        with self.db.lock:
            self.conn.execute("UPDATE sessions SET last_seen_at = ? WHERE token = ?", (_now(), token))
            self.conn.commit()
        return ReviewSession(row["token"], row["reviewer"], int(row["slot"]), bool(row["blind"]), row["created_at"])

    def end(self, token: str | None) -> bool:
        s = self.resolve(token)
        if s is None:
            return False
        with self.db.lock:
            self.conn.execute("UPDATE sessions SET ended_at = ? WHERE token = ?", (_now(), token))
            self.db.audit(s.reviewer, "session.end", f"slot {s.slot}")
            self.conn.commit()
        return True

    def active(self) -> list[ReviewSession]:
        rows = self.conn.execute("SELECT * FROM sessions WHERE ended_at = '' ORDER BY created_at").fetchall()
        return [ReviewSession(r["token"], r["reviewer"], int(r["slot"]), bool(r["blind"]), r["created_at"]) for r in rows]
