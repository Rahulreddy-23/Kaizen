"""Shared, attributed terminology with explicit, version-pinned account selections."""
from datetime import datetime, timezone

from kaizen.terminology.repository import TerminologyRepository
from kaizen.terminology.store import RelationshipStore


class TerminologyCatalog:
    def __init__(self, repository: TerminologyRepository):
        self.repo = repository
        self.db = repository.db
        self.conn = self.db.conn
        # Preserve authors' existing approved work once; never re-add a removed selection on restart.
        with self.db.transaction():
            if not self.conn.execute("SELECT 1 FROM settings WHERE key='terminology_personal_v1'").fetchone():
                self.conn.execute('INSERT OR IGNORE INTO terminology_selections (email,relationship_id,version,selected_at) '
                                  'SELECT r.created_by,r.id,r.version,r.updated_at FROM relationships r JOIN profiles p ON p.email=r.created_by '
                                  "WHERE p.status='approved' AND r.active=1")
                self.conn.execute("INSERT INTO settings VALUES ('terminology_personal_v1','1',?,'system')", (datetime.now(timezone.utc).isoformat(),))

    def defaults(self):
        return {r['id']: self.repo.get_version(r['id'], r['version']) for r in self.conn.execute(
            "SELECT id,MIN(version) AS version FROM relationship_versions WHERE change_type='seed' GROUP BY id")}

    def selections(self, email):
        return {r['relationship_id']: r['version'] for r in self.conn.execute('SELECT relationship_id,version FROM terminology_selections WHERE email=?', (email,))}

    def list(self, email):
        defaults, selected = self.defaults(), self.selections(email)
        approvals = {}
        for record in self.conn.execute("SELECT id,version,changed_by,changed_at,change_type FROM relationship_versions WHERE change_type NOT IN ('deactivate','delete') ORDER BY version"):
            approvals[record['id']] = record
        usage = {r['relationship_id']: r['total'] for r in self.conn.execute(
            'SELECT rr.relationship_id,SUM(rr.used_count) AS total FROM run_relationships rr JOIN runs r ON r.run_id=rr.run_id '
            "WHERE r.deleted_at='' AND (r.owner=? OR EXISTS (SELECT 1 FROM run_shares s WHERE s.run_id=r.run_id AND s.email=?)) GROUP BY rr.relationship_id", (email, email))}
        result = []
        for rel in self.repo.list():
            approval = approvals.get(rel.id)
            default = defaults.get(rel.id)
            enabled = selected.get(rel.id, default.version if default else None) if rel.active else None
            enabled_rule = self.repo.get_version(rel.id, enabled) if enabled and enabled != rel.version else None
            result.append(rel.model_dump(mode='json') | {
                'approved_by': approval['changed_by'] if approval and approval['change_type'] != 'seed' else None,
                'approved_at': approval['changed_at'] if approval and approval['change_type'] != 'seed' else None,
                'is_default': bool(default and default.version == rel.version),
                'selected_version': selected.get(rel.id), 'enabled_version': enabled, 'usage': usage.get(rel.id, 0),
                'enabled_definition': enabled_rule.model_dump(mode='json') if enabled_rule else None,
            })
        return result

    def select(self, email, entries, selected=True):
        with self.db.transaction():
            # Validate the complete batch before any mutation; a stale list cannot silently adopt edits.
            if len({e['id'] for e in entries}) != len(entries):
                raise ValueError('Choose each relationship only once.')
            for entry in entries:
                rel = self.repo.get(entry['id'])
                if not rel:
                    raise KeyError(entry['id'])
                if selected and (not rel.active or rel.version != entry['version']):
                    raise ValueError('Terminology changed. Refresh the list and review its latest version before adding it.')
            at = datetime.now(timezone.utc).isoformat()
            for entry in entries:
                if selected:
                    self.conn.execute('INSERT INTO terminology_selections VALUES (?,?,?,?) ON CONFLICT(email,relationship_id) DO UPDATE SET version=excluded.version,selected_at=excluded.selected_at',
                                      (email, entry['id'], entry['version'], at))
                else:
                    self.conn.execute('DELETE FROM terminology_selections WHERE email=? AND relationship_id=?', (email, entry['id']))
            self.db.audit(email, 'terminology.selected' if selected else 'terminology.removed', ', '.join(f'{e["id"]} v{e["version"]}' for e in entries))
        return {'changed': len(entries)}

    def approve(self, rel, actor):
        """An explicit approval adopts that version for its reviewer, never for other accounts."""
        self.select(actor, [{'id': rel.id, 'version': rel.version}])
        return rel

    def store(self, email):
        with self.db.lock:
            defaults, selected = self.defaults(), self.selections(email)
            rels = []
            for current in self.repo.list(active_only=True):
                version = selected.get(current.id)
                rel = self.repo.get_version(current.id, version) if version else defaults.get(current.id)
                if rel and rel.active:
                    rels.append(rel)
            return RelationshipStore(rels)
