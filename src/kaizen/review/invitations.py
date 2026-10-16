"""Email-bound, one-use invitations. Deliver codes privately after checking the recipient."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from kaizen.review.access import AccessStore, bd_email
from kaizen.review.sessions import UserStore
from kaizen.storage.db import Database

INVALID_INVITATION = 'This invitation is invalid, expired or already used. Ask an administrator for a new invitation.'


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


class InvitationStore:
    def __init__(self, db: Database):
        self.db = db
        self.conn = db.conn

    def list(self):
        # Never return the digest or the secret, including to administrators.
        return [dict(r) for r in self.conn.execute(
            'SELECT id,email,invited_by,created_at,expires_at,consumed_at,revoked_at FROM account_invitations ORDER BY created_at DESC')]

    def create(self, email, actor, hours=72):
        email = bd_email(email)
        if not 1 <= hours <= 168:
            raise ValueError('Invitations must expire within 1–168 hours.')
        with self.db.transaction():
            profile = AccessStore(self.db).profile(email)
            if UserStore(self.db).exists(email) or (profile and profile['status'] in ('approved', 'rejected')):
                raise ValueError('This account already exists. Manage its access or reset its password instead.')
            token = secrets.token_urlsafe(32)
            now = datetime.now(timezone.utc)
            self.conn.execute("UPDATE account_invitations SET revoked_at=? WHERE email=? AND consumed_at='' AND revoked_at=''", (now.isoformat(), email))
            invitation = dict(id=uuid.uuid4().hex, email=email, invited_by=actor, created_at=now.isoformat(),
                              expires_at=(now + timedelta(hours=hours)).isoformat(), consumed_at='', revoked_at='')
            self.conn.execute('INSERT INTO account_invitations (id,email,token_hash,invited_by,created_at,expires_at) VALUES (?,?,?,?,?,?)',
                              (invitation['id'], email, _digest(token), actor, invitation['created_at'], invitation['expires_at']))
            self.db.audit(actor, 'account.invited', f'{email}: invitation {invitation["id"]}')
        return invitation | {'code': token}

    def validate(self, email, token):
        row = self.conn.execute('SELECT * FROM account_invitations WHERE token_hash=? AND email=?', (_digest(token), email)).fetchone()
        inviter = AccessStore(self.db).profile(row['invited_by']) if row else None
        if (not row or row['consumed_at'] or row['revoked_at'] or
                datetime.fromisoformat(row['expires_at']) <= datetime.now(timezone.utc) or
                not inviter or inviter['status'] != 'approved' or not inviter['is_admin']):
            raise ValueError(INVALID_INVITATION)
        profile = AccessStore(self.db).profile(email)
        if profile and profile['status'] == 'rejected':
            raise ValueError(INVALID_INVITATION)
        return dict(row)

    def consume(self, invitation):
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute('UPDATE account_invitations SET consumed_at=? WHERE id=?', (now, invitation['id']))
        self.conn.execute("INSERT INTO profiles (email,status,is_admin,created_at) VALUES (?,'approved',0,?) ON CONFLICT(email) DO UPDATE SET status='approved'", (invitation['email'], now))
        self.db.audit(invitation['email'], 'account.invitation_accepted', f'invited by {invitation["invited_by"]}')

    def revoke(self, invitation_id, actor):
        with self.db.transaction():
            row = self.conn.execute('SELECT * FROM account_invitations WHERE id=?', (invitation_id,)).fetchone()
            if not row:
                raise KeyError(invitation_id)
            if not row['consumed_at'] and not row['revoked_at']:
                self.conn.execute('UPDATE account_invitations SET revoked_at=? WHERE id=?', (datetime.now(timezone.utc).isoformat(), invitation_id))
                self.db.audit(actor, 'account.invitation_revoked', invitation_id)
