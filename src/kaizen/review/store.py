"""Reviewer decisions. The engine recommendation is never overwritten; decisions are stored beside it with an
explicit state machine and a full history (engine → reviewer 1 → reviewer 2 → final)."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from kaizen.models import CheckResult, Classification
from kaizen.storage.db import Database

DECISIONS = ("ACCEPT", "OVERRIDE", "CONFIRM_DISCREPANCY", "NEEDS_MORE_INFORMATION")
STATES = ("ENGINE_RECOMMENDED", "REVIEWER_1_COMPLETE", "REVIEWER_2_COMPLETE", "AGREED", "DISAGREEMENT", "FINALIZED")


@dataclass(frozen=True)
class Decision:
    slot: int
    reviewer: str
    decision: str
    comment: str
    override_classification: str | None
    decided_at: str
    blind: bool


@dataclass(frozen=True)
class Final:
    final_decision: str
    finalized_by: str
    finalized_at: str
    note: str


@dataclass(frozen=True)
class RowView:
    row_id: str
    state: str
    decisions: dict[int, Decision]
    final: Final | None

    @property
    def effective_classification(self) -> str | None:
        """Classification after reviewer overrides (None → the engine classification stands)."""
        for slot in (2, 1):
            d = self.decisions.get(slot)
            if d and d.decision == "OVERRIDE" and d.override_classification:
                return d.override_classification
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ReviewStore:
    def __init__(self, db: Database):
        self.db = db
        self.conn = db.conn

    def decide(self, run_id: str, row_id: str, slot: int, reviewer: str, decision: str, comment: str = "", override_classification: str | None = None, blind: bool = False) -> Decision:
        if slot not in (1, 2):
            raise ValueError("reviewer slot must be 1 or 2")
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
        if decision == "OVERRIDE":
            if not override_classification or override_classification not in {c.value for c in Classification}:
                raise ValueError("OVERRIDE requires an override_classification (EXACT, EQUIVALENT, POTENTIAL, MISMATCH, MISSING)")
        else:
            override_classification = None
        d = Decision(slot, reviewer, decision, comment or "", override_classification, _now(), bool(blind))
        with self.db.lock:
            self.conn.execute("INSERT OR REPLACE INTO decisions (run_id, row_id, reviewer_slot, reviewer_name, decision, comment, decided_at, blind, override_classification) VALUES (?,?,?,?,?,?,?,?,?)", (run_id, row_id, slot, reviewer, decision, d.comment, d.decided_at, int(d.blind), override_classification or ""))
            self.db.audit(reviewer, f"review.decision.slot{slot}", f"{run_id} {row_id}: {decision}{' → ' + override_classification if override_classification else ''}{' [blind]' if blind else ''} {comment}".strip())
            self.conn.commit()
        return d

    def finalize(self, run_id: str, row_id: str, final_decision: str, by: str, note: str = "") -> Final:
        if final_decision not in DECISIONS:
            raise ValueError(f"final decision must be one of {DECISIONS}")
        f = Final(final_decision, by, _now(), note or "")
        with self.db.lock:
            self.conn.execute("INSERT OR REPLACE INTO finals VALUES (?,?,?,?,?,?)", (run_id, row_id, final_decision, by, f.finalized_at, f.note))
            self.db.audit(by, "review.final", f"{run_id} {row_id}: {final_decision} {note}".strip())
            self.conn.commit()
        return f

    def decisions(self, run_id: str, row_id: str) -> dict[int, Decision]:
        rows = self.conn.execute("SELECT * FROM decisions WHERE run_id = ? AND row_id = ?", (run_id, row_id)).fetchall()
        return {r["reviewer_slot"]: Decision(r["reviewer_slot"], r["reviewer_name"], r["decision"], r["comment"], r["override_classification"] or None, r["decided_at"], bool(r["blind"])) for r in rows}

    def all_decisions(self, run_id: str) -> dict[str, dict[int, Decision]]:
        out: dict[str, dict[int, Decision]] = {}
        for r in self.conn.execute("SELECT * FROM decisions WHERE run_id = ?", (run_id,)):
            out.setdefault(r["row_id"], {})[r["reviewer_slot"]] = Decision(r["reviewer_slot"], r["reviewer_name"], r["decision"], r["comment"], r["override_classification"] or None, r["decided_at"], bool(r["blind"]))
        return out

    def finals(self, run_id: str) -> dict[str, Final]:
        return {r["row_id"]: Final(r["final_decision"], r["finalized_by"], r["finalized_at"], r["note"]) for r in self.conn.execute("SELECT * FROM finals WHERE run_id = ?", (run_id,))}

    @staticmethod
    def state_of(decisions: dict[int, Decision], final: Final | None) -> str:
        if final is not None:
            return "FINALIZED"
        d1, d2 = decisions.get(1), decisions.get(2)
        if d1 and d2:
            same = d1.decision == d2.decision and (d1.override_classification or None) == (d2.override_classification or None)
            return "AGREED" if same else "DISAGREEMENT"
        if d1:
            return "REVIEWER_1_COMPLETE"
        if d2:
            return "REVIEWER_2_COMPLETE"
        return "ENGINE_RECOMMENDED"

    def row_state(self, run_id: str, row_id: str) -> RowView:
        decisions = self.decisions(run_id, row_id)
        final = self.finals(run_id).get(row_id)
        return RowView(row_id, self.state_of(decisions, final), decisions, final)

    def history(self, run_id: str, row_id: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{"event": "engine", "detail": "engine recommendation recorded with the run"}]
        for slot, d in sorted(self.decisions(run_id, row_id).items()):
            out.append({"event": f"reviewer_{slot}", **asdict(d)})
        final = self.finals(run_id).get(row_id)
        if final:
            out.append({"event": "final", **asdict(final)})
        return out

    @staticmethod
    def is_blind_hidden(decisions: dict[int, Decision], viewer_slot: int, blind: bool) -> bool:
        """True when reviewer 1's work must stay hidden: a blind reviewer 2 who has not yet decided."""
        return bool(blind) and viewer_slot == 2 and 2 not in decisions

    def rows_for_viewer(self, run_id: str, results: list[CheckResult], viewer_slot: int = 1, blind: bool = False) -> list[dict[str, Any]]:
        """Rows with decisions merged. In blind mode reviewer 2 does not see reviewer 1's decision until they
        have submitted their own; the engine recommendation is always visible."""
        all_d = self.all_decisions(run_id)
        finals = self.finals(run_id)
        out = []
        for r in results:
            decisions = all_d.get(r.row_id, {})
            final = finals.get(r.row_id)
            view = {slot: (asdict(decisions[slot]) if slot in decisions else None) for slot in (1, 2)}
            if self.is_blind_hidden(decisions, viewer_slot, blind):
                # Hide reviewer 1 completely: the decision itself, the state that reveals they have
                # decided, any final taken without reviewer 2, and any override that would otherwise
                # leak through the effective classification.
                view[1] = None
                decisions, final = {}, None
            out.append({
                "row_id": r.row_id, "sku": r.sku, "check": r.check.value, "role": r.role,
                "engine": {"classification": r.classification.value, "match_level": r.match_level.value, "score": r.score, "relationship_id": r.relationship_id, "requires_validation": r.requires_validation, "severity": r.severity.value if r.severity else None, "discrepancies": [d.type.value for d in r.discrepancies], "explanation": r.explanation},
                "decisions": view, "state": self.state_of(decisions, final), "final": asdict(final) if final else None,
                "effective_classification": RowView(r.row_id, "", decisions, final).effective_classification or r.classification.value,
            })
        return out

    def bulk_accept_clean(self, run_id: str, results: list[CheckResult], slot: int, reviewer: str) -> int:
        existing = self.all_decisions(run_id)
        n = 0
        for r in results:
            if r.requires_validation or slot in existing.get(r.row_id, {}):
                continue
            self.decide(run_id, r.row_id, slot, reviewer, "ACCEPT", comment="bulk accept: exact/equivalent with no discrepancy")
            n += 1
        return n

    def state_counts(self, run_id: str, results: list[CheckResult], viewer_slot: int = 1, blind: bool = False) -> dict[str, int]:
        """Counts as this viewer may see them: rows hidden from a blind reviewer 2 count as undecided."""
        all_d = self.all_decisions(run_id)
        finals = self.finals(run_id)
        counts = {s: 0 for s in STATES}
        for r in results:
            decisions = all_d.get(r.row_id, {})
            final = finals.get(r.row_id)
            if self.is_blind_hidden(decisions, viewer_slot, blind):
                decisions, final = {}, None
            counts[self.state_of(decisions, final)] += 1
        return counts

    def clear_run(self, run_id: str) -> None:
        self.conn.execute("DELETE FROM decisions WHERE run_id = ?", (run_id,))
        self.conn.execute("DELETE FROM finals WHERE run_id = ?", (run_id,))
        self.conn.commit()
