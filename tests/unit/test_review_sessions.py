"""Reviewer sessions: identity and blind mode live on the server, not in the client's request.

The prototype used to take `viewer` and `blind` from the query string, so a reviewer could switch blind
mode off from the browser. Identity is now a server-side session; blind mode follows from the workspace
policy and the reviewer's slot, and the client cannot choose it.
"""

import pytest

from kaizen.models import CheckResult, CheckType, Classification, MatchLevel
from kaizen.review.sessions import POLICY_OPTIONAL, POLICY_REQUIRED, SessionStore
from kaizen.review.store import ReviewStore
from kaizen.storage.db import Database


@pytest.fixture()
def db(tmp_path):
    return Database(tmp_path / "kaizen.db")


@pytest.fixture()
def sessions(db):
    return SessionStore(db)


def _row(row_id: str = "R-1") -> CheckResult:
    return CheckResult(
        row_id=row_id, sku="1295108NS", check=CheckType.BOM_LABEL, role="item",
        classification=Classification.MISMATCH, match_level=MatchLevel.EXACT, score=1.0,
        explanation="quantity differs", requires_validation=True,
    )


# ---- policy -------------------------------------------------------------------------------------


def test_blind_review_is_required_by_default(sessions):
    assert sessions.policy() == POLICY_REQUIRED


def test_policy_change_is_persisted_and_audited(db, sessions):
    sessions.set_policy(POLICY_OPTIONAL, by="Rahul")
    assert SessionStore(db).policy() == POLICY_OPTIONAL
    actions = [r["action"] for r in db.conn.execute("SELECT action FROM audit")]
    assert "session.policy" in actions


def test_unknown_policy_value_is_rejected(sessions):
    with pytest.raises(ValueError):
        sessions.set_policy("off", by="Rahul")


# ---- opening a session --------------------------------------------------------------------------


def test_second_reviewer_is_blind_when_the_policy_requires_it(sessions):
    s = sessions.open(reviewer="Hemant", slot=2)
    assert s.slot == 2 and s.blind is True


def test_client_cannot_turn_blind_mode_off_while_the_policy_requires_it(sessions):
    s = sessions.open(reviewer="Hemant", slot=2, blind=False)
    assert s.blind is True, "the policy, not the caller, decides blind mode for reviewer 2"


def test_second_reviewer_may_be_unblinded_when_the_policy_is_optional(sessions):
    sessions.set_policy(POLICY_OPTIONAL, by="Rahul")
    assert sessions.open(reviewer="Hemant", slot=2, blind=False).blind is False
    assert sessions.open(reviewer="Hemant", slot=2, blind=True).blind is True


def test_first_reviewer_is_never_blind(sessions):
    assert sessions.open(reviewer="Dharma", slot=1, blind=True).blind is False


def test_reviewer_name_is_required(sessions):
    with pytest.raises(ValueError):
        sessions.open(reviewer="   ", slot=1)


def test_slot_must_be_one_or_two(sessions):
    with pytest.raises(ValueError):
        sessions.open(reviewer="Dharma", slot=3)


def test_opening_a_session_is_audited_with_slot_and_blind_flag(db, sessions):
    sessions.open(reviewer="Hemant", slot=2)
    row = db.conn.execute("SELECT actor, action, detail FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    assert row["actor"] == "Hemant" and row["action"] == "session.open"
    assert "slot 2" in row["detail"] and "blind" in row["detail"]


def test_tokens_are_unique_and_not_guessable(sessions):
    tokens = {sessions.open(reviewer="Dharma", slot=1).token for _ in range(5)}
    assert len(tokens) == 5
    assert all(len(t) >= 32 for t in tokens)


# ---- resolving and ending -----------------------------------------------------------------------


def test_resolve_returns_the_open_session(sessions):
    s = sessions.open(reviewer="Dharma", slot=1)
    got = sessions.resolve(s.token)
    assert got is not None and got.reviewer == "Dharma" and got.slot == 1


def test_resolve_rejects_unknown_and_ended_tokens(sessions):
    assert sessions.resolve("nope") is None
    assert sessions.resolve(None) is None
    s = sessions.open(reviewer="Dharma", slot=1)
    sessions.end(s.token)
    assert sessions.resolve(s.token) is None


def test_ending_a_session_is_audited(db, sessions):
    s = sessions.open(reviewer="Dharma", slot=1)
    sessions.end(s.token)
    assert "session.end" in [r["action"] for r in db.conn.execute("SELECT action FROM audit")]


# ---- what a blind reviewer must not see ---------------------------------------------------------


def test_blind_reviewer_two_sees_neither_the_decision_nor_its_effect(db):
    """Reviewer 1 overrode the classification. Reviewer 2, blind, must not see the override either
    directly (`decisions`) or indirectly (`effective_classification`, `state`)."""
    review = ReviewStore(db)
    row = _row()
    review.decide("run1", row.row_id, slot=1, reviewer="Dharma", decision="OVERRIDE", override_classification="EQUIVALENT", comment="same part")

    blind = review.rows_for_viewer("run1", [row], viewer_slot=2, blind=True)[0]
    assert blind["decisions"][1] is None
    assert blind["effective_classification"] == "MISMATCH", "reviewer 1's override leaked through effective_classification"
    assert blind["state"] == "ENGINE_RECOMMENDED", "row state revealed that reviewer 1 had already decided"

    open_view = review.rows_for_viewer("run1", [row], viewer_slot=1, blind=False)[0]
    assert open_view["decisions"][1]["decision"] == "OVERRIDE"
    assert open_view["effective_classification"] == "EQUIVALENT"


def test_blind_reviewer_two_does_not_see_a_final_decision_taken_without_them(db):
    review = ReviewStore(db)
    row = _row()
    review.decide("run1", row.row_id, slot=1, reviewer="Dharma", decision="CONFIRM_DISCREPANCY")
    review.finalize("run1", row.row_id, "CONFIRM_DISCREPANCY", by="Dharma", note="early close")
    blind = review.rows_for_viewer("run1", [row], viewer_slot=2, blind=True)[0]
    assert blind["final"] is None and blind["decisions"][1] is None


def test_everything_becomes_visible_once_reviewer_two_has_decided(db):
    review = ReviewStore(db)
    row = _row()
    review.decide("run1", row.row_id, slot=1, reviewer="Dharma", decision="OVERRIDE", override_classification="EQUIVALENT")
    review.decide("run1", row.row_id, slot=2, reviewer="Hemant", decision="ACCEPT", blind=True)
    view = review.rows_for_viewer("run1", [row], viewer_slot=2, blind=True)[0]
    assert view["decisions"][1]["decision"] == "OVERRIDE"
    assert view["effective_classification"] == "EQUIVALENT"
    assert view["state"] == "DISAGREEMENT"
