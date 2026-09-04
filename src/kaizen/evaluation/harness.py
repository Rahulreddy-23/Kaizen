"""Compares a Run against ground truth. Reports precision/recall for discrepancies, pairing and classification
accuracy, false-missing violations and every disagreement in plain words. Numbers are measured, never invented."""

from dataclasses import dataclass, field
from typing import Any

from kaizen.evaluation.ground_truth import ExpectedRow, GroundTruth
from kaizen.matching.normalize import normalize
from kaizen.models import CheckResult, CheckType, Classification, DiscrepancyType, Run, Severity


@dataclass
class PRCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else (1.0 if self.fn == 0 else 0.0)

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"tp": self.tp, "fp": self.fp, "fn": self.fn, "precision": round(self.precision, 4), "recall": round(self.recall, 4), "f1": round(self.f1, 4)}


@dataclass
class SkuMetrics:
    sku: str
    expected_rows: int = 0
    predicted_rows: int = 0
    pairing_correct: int = 0
    classification_correct: int = 0
    counts: PRCounts = field(default_factory=PRCounts)
    false_missing: list[str] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"expected_rows": self.expected_rows, "predicted_rows": self.predicted_rows, "pairing_correct": self.pairing_correct, "classification_correct": self.classification_correct, **self.counts.to_dict(), "false_missing": self.false_missing, "mismatches": self.mismatches}


@dataclass
class CheckMetrics:
    counts: PRCounts = field(default_factory=PRCounts)
    scored_rows: int = 0
    classification_correct: int = 0
    pairing_correct: int = 0

    @property
    def classification_accuracy(self) -> float:
        return self.classification_correct / self.scored_rows if self.scored_rows else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {**self.counts.to_dict(), "scored_rows": self.scored_rows, "classification_accuracy": round(self.classification_accuracy, 4), "pairing_correct": self.pairing_correct}


@dataclass
class Metrics:
    overall: PRCounts = field(default_factory=PRCounts)
    per_type: dict[str, PRCounts] = field(default_factory=dict)
    per_check: dict[str, CheckMetrics] = field(default_factory=dict)
    per_sku: dict[str, SkuMetrics] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    scored_rows: int = 0
    pairing_correct_total: int = 0
    classification_correct_total: int = 0
    ref_checks: int = 0
    ref_checks_correct: int = 0
    false_missing: int = 0
    mismatches: list[str] = field(default_factory=list)
    missing_skus: list[str] = field(default_factory=list)

    @property
    def pairing_accuracy(self) -> float:
        return self.pairing_correct_total / self.scored_rows if self.scored_rows else 1.0

    @property
    def classification_accuracy(self) -> float:
        return self.classification_correct_total / self.scored_rows if self.scored_rows else 1.0

    @property
    def ref_check_accuracy(self) -> float:
        return self.ref_checks_correct / self.ref_checks if self.ref_checks else 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall.to_dict(),
            "per_type": {k: v.to_dict() for k, v in sorted(self.per_type.items())},
            "per_check": {k: v.to_dict() for k, v in sorted(self.per_check.items())},
            "per_sku": {k: v.to_dict() for k, v in self.per_sku.items()},
            "counts": self.counts,
            "scored_rows": self.scored_rows,
            "pairing_accuracy": round(self.pairing_accuracy, 4),
            "classification_accuracy": round(self.classification_accuracy, 4),
            "ref_check_accuracy": round(self.ref_check_accuracy, 4),
            "false_missing": self.false_missing,
            "mismatches": self.mismatches,
            "missing_skus": self.missing_skus,
            "scoring_note": "INFO-severity discrepancies are scored only when the ground truth expects them.",
        }


def _key(text: str | None) -> str | None:
    return normalize(text).sorted_key if text else None


def _is_header(r: CheckResult) -> bool:
    return r.role in ("header", "reference", "coverage") or (r.source_a is not None and r.source_a.attributes.get("kind") == "header")


def _score_discrepancies(m: Metrics, sm: SkuMetrics, pred: CheckResult | None, exp, label: str, check: str = "BOM_LABEL") -> None:
    expected = {d.value for d in exp.discrepancies} if exp else set()
    predicted = set()
    if pred is not None:
        predicted = {d.type.value for d in pred.discrepancies if d.severity is not Severity.INFO or d.type.value in expected}
    for t in predicted & expected:
        _bump(m, sm, t, "tp", check)
    for t in predicted - expected:
        _bump(m, sm, t, "fp", check)
        sm.mismatches.append(f"{label}: unexpected discrepancy {t}")
    for t in expected - predicted:
        _bump(m, sm, t, "fn", check)
        sm.mismatches.append(f"{label}: expected discrepancy {t} not reported")


def _bump(m: Metrics, sm: SkuMetrics, t: str, kind: str, check: str = "BOM_LABEL") -> None:
    for counts in (m.overall, sm.counts, m.per_type.setdefault(t, PRCounts()), m.per_check.setdefault(check, CheckMetrics()).counts):
        setattr(counts, kind, getattr(counts, kind) + 1)


def _pco_number(r: CheckResult) -> str:
    parts = r.row_id.split("-")
    return parts[1] if len(parts) >= 3 else ""


def evaluate(run: Run, gt: GroundTruth) -> Metrics:
    m = Metrics()
    for r in run.results:
        if not _is_header(r):
            m.counts[r.classification.value] = m.counts.get(r.classification.value, 0) + 1
    for sku, exp_sku in gt.skus.items():
        sm = SkuMetrics(sku=sku, expected_rows=len(exp_sku.expected))
        m.per_sku[sku] = sm
        rows = [r for r in run.results if r.sku == sku and r.check is CheckType.BOM_LABEL]
        m.scored_rows += len(exp_sku.expected)
        bl = m.per_check.setdefault("BOM_LABEL", CheckMetrics())
        bl.scored_rows += len(exp_sku.expected)
        _score_pco(m, sm, run, sku, exp_sku)
        _score_pairing(m, sm, run, sku, CheckType.BOM_DRAWING, exp_sku.bom_drawing, "bom_item", "drawing")
        _score_pairing(m, sm, run, sku, CheckType.LABEL_DRAWING, exp_sku.label_drawing, "label", "drawing")
        _score_drawing_ref(m, sm, run, sku, exp_sku)
        _score_revision(m, sm, run, sku, exp_sku)
        if not rows and not exp_sku.expected:
            continue
        if not rows:
            m.missing_skus.append(sku)
            for exp in exp_sku.expected:
                _score_discrepancies(m, sm, None, exp, f"{sku} {exp.bom_item or exp.label}")
                sm.mismatches.append(f"{sku}: no results produced for this SKU")
            continue
        headers = [r for r in rows if _is_header(r)]
        item_rows = [r for r in rows if not _is_header(r) and r.role != "exempt"]
        sm.predicted_rows = len(item_rows)
        m.ref_checks += 1
        if headers:
            h = headers[0]
            ok = (h.classification is Classification.EXACT) if exp_sku.ref_check == "EXACT" else any(d.type.value == exp_sku.ref_check for d in h.discrepancies)
            if ok:
                m.ref_checks_correct += 1
            else:
                sm.mismatches.append(f"{sku}: REF/parent row expected {exp_sku.ref_check}, got {h.classification.value} {[d.type.value for d in h.discrepancies]}")
        by_item = {r.source_a.item_number: r for r in item_rows if r.source_a is not None}
        label_only = {_key(r.source_b.description): r for r in item_rows if r.source_a is None and r.source_b is not None}
        covered: set[str] = set()
        for exp in exp_sku.expected:
            if exp.bom_item is not None:
                pred = by_item.get(exp.bom_item)
                label = f"{sku} item {exp.bom_item}"
                if pred is None:
                    sm.mismatches.append(f"{label}: no result row produced")
                    _score_discrepancies(m, sm, None, exp, label)
                    continue
                covered.add(pred.row_id)
                predicted_label = pred.source_b.description if pred.source_b is not None else None
                acceptable = {_key(x) for x in exp.acceptable_labels()}
                pairing_ok = _key(predicted_label) in acceptable
            else:
                acceptable_keys = [_key(x) for x in exp.acceptable_labels()]
                pred = next((label_only[k] for k in acceptable_keys if k in label_only), None)
                label = f"{sku} label-only '{exp.label or (exp.label_any_of or ['?'])[0]}'"
                if pred is None:
                    sm.mismatches.append(f"{label}: no missing-in-BOM row produced")
                    _score_discrepancies(m, sm, None, exp, label)
                    continue
                covered.add(pred.row_id)
                pairing_ok = True
            if pairing_ok:
                sm.pairing_correct += 1
                m.pairing_correct_total += 1
                bl.pairing_correct += 1
            else:
                sm.mismatches.append(f"{label}: paired with '{pred.source_b.description if pred.source_b else None}', expected one of {exp.acceptable_labels()}")
            if pred.classification is exp.classification:
                sm.classification_correct += 1
                m.classification_correct_total += 1
                bl.classification_correct += 1
            else:
                sm.mismatches.append(f"{label}: classified {pred.classification.value}, expected {exp.classification.value}")
            _score_discrepancies(m, sm, pred, exp, label)
        for r in item_rows:
            if r.row_id in covered:
                continue
            who = f"{sku} item {r.source_a.item_number}" if r.source_a else f"{sku} label-only '{r.source_b.description if r.source_b else '?'}'"
            extra = [d.type.value for d in r.discrepancies if d.severity is not Severity.INFO]
            if extra:
                sm.mismatches.append(f"{who}: row not in ground truth reports {extra}")
                for t in extra:
                    _bump(m, sm, t, "fp")
        for item in exp_sku.not_compared:
            if item in by_item:
                sm.false_missing.append(item)
                m.false_missing += 1
                sm.mismatches.append(f"{sku} item {item}: must not be compared (non-physical/inactive) but a row was produced ({by_item[item].classification.value})")
        m.mismatches.extend(sm.mismatches)
    _score_coverage(m, run, gt)
    return m


def _score_pco(m: Metrics, sm: SkuMetrics, run: Run, sku: str, exp_sku) -> None:
    if not exp_sku.pco_bom:
        return
    cm = m.per_check.setdefault("PCO_BOM", CheckMetrics())
    rows = [r for r in run.results if r.sku == sku and r.check is CheckType.PCO_BOM and r.source_a is not None and r.source_a.attributes.get("kind") == "change"]
    by_key = {r.source_a.attributes.get("change_key"): r for r in rows}
    covered = set()
    for exp in exp_sku.pco_bom:
        cm.scored_rows += 1
        m.scored_rows += 1
        label = f"{sku} PCO {exp.change_key}"
        pred = by_key.get(exp.change_key)
        if pred is None:
            sm.mismatches.append(f"{label}: no PCO ↔ BOM row produced")
            _score_discrepancies(m, sm, None, exp, label, "PCO_BOM")
            continue
        covered.add(pred.row_id)
        cm.pairing_correct += 1
        m.pairing_correct_total += 1
        if pred.classification is exp.classification:
            cm.classification_correct += 1
            m.classification_correct_total += 1
        else:
            sm.mismatches.append(f"{label}: classified {pred.classification.value}, expected {exp.classification.value}")
        _score_discrepancies(m, sm, pred, exp, label, "PCO_BOM")
    for r in rows:
        if r.row_id in covered:
            continue
        extra = [d.type.value for d in r.discrepancies if d.severity is not Severity.INFO]
        if extra:
            sm.mismatches.append(f"{sku} PCO {r.source_a.attributes.get('change_key')}: row not in ground truth reports {extra}")
            for t in extra:
                _bump(m, sm, t, "fp", "PCO_BOM")


def _score_pairing(m: Metrics, sm: SkuMetrics, run: Run, sku: str, check: CheckType, expected: list[ExpectedRow], a_key: str, b_key: str) -> None:
    """Score a presence/identity check: A-side rows keyed by BOM item number or normalised label text, B-only
    rows keyed by normalised B text. Exempt rows (conditional/packaging) are ignored unless ground truth lists them."""
    if not expected:
        return
    cm = m.per_check.setdefault(check.value, CheckMetrics())
    rows = [r for r in run.results if r.sku == sku and r.check is check and not _is_header(r)]
    scored = [r for r in rows if r.role != "exempt"]

    def a_of(r: CheckResult):
        return (r.source_a.item_number if a_key == "bom_item" else _key(r.source_a.description)) if r.source_a is not None else None

    by_a = {a_of(r): r for r in scored if r.source_a is not None}
    b_only = {_key(r.source_b.description): r for r in scored if r.source_a is None and r.source_b is not None}
    covered: set[str] = set()
    for exp in expected:
        cm.scored_rows += 1
        m.scored_rows += 1
        exp_a = exp.bom_item if a_key == "bom_item" else exp.label
        acceptable_b = exp.acceptable_drawings() if b_key == "drawing" else exp.acceptable_labels()
        if exp_a is not None:
            key = exp_a if a_key == "bom_item" else _key(exp_a)
            pred = by_a.get(key)
            label = f"{sku} {check.value} {exp_a}"
            if pred is None:
                sm.mismatches.append(f"{label}: no result row produced")
                _score_discrepancies(m, sm, None, exp, label, check.value)
                continue
            covered.add(pred.row_id)
            predicted_b = pred.source_b.description if pred.source_b is not None else None
            pairing_ok = _key(predicted_b) in {_key(x) for x in acceptable_b}
        else:
            keys = [_key(x) for x in acceptable_b]
            pred = next((b_only[k] for k in keys if k in b_only), None)
            label = f"{sku} {check.value} {check.value.split('_')[1].lower()}-only '{acceptable_b[0]}'"
            if pred is None:
                sm.mismatches.append(f"{label}: no B-only row produced")
                _score_discrepancies(m, sm, None, exp, label, check.value)
                continue
            covered.add(pred.row_id)
            pairing_ok = True
        if pairing_ok:
            cm.pairing_correct += 1
            m.pairing_correct_total += 1
        else:
            sm.mismatches.append(f"{label}: paired with '{pred.source_b.description if pred.source_b else None}', expected one of {acceptable_b}")
        if pred.classification is exp.classification:
            cm.classification_correct += 1
            m.classification_correct_total += 1
        else:
            sm.mismatches.append(f"{label}: classified {pred.classification.value}, expected {exp.classification.value}")
        _score_discrepancies(m, sm, pred, exp, label, check.value)
    for r in scored:
        if r.row_id in covered:
            continue
        extra = [d.type.value for d in r.discrepancies if d.severity is not Severity.INFO]
        if extra:
            who = f"{sku} {check.value} {a_of(r) or ''}{'' if r.source_a is not None else 'B-only ' + (r.source_b.description if r.source_b else '?')}"
            sm.mismatches.append(f"{who}: row not in ground truth reports {extra}")
            for t in extra:
                _bump(m, sm, t, "fp", check.value)


def _score_drawing_ref(m: Metrics, sm: SkuMetrics, run: Run, sku: str, exp_sku) -> None:
    refs = [r for r in run.results if r.sku == sku and r.check is CheckType.BOM_DRAWING and r.role == "reference"]
    if not refs and not exp_sku.bom_drawing:
        return
    cm = m.per_check.setdefault("BOM_DRAWING", CheckMetrics())
    cm.scored_rows += 1
    m.scored_rows += 1
    if not refs:
        sm.mismatches.append(f"{sku}: no drawing reference row produced")
        return
    h = refs[0]
    want = exp_sku.drawing_ref
    ok = (h.classification is Classification.EXACT) if want == "EXACT" else (h.classification is Classification.POTENTIAL) if want == "POTENTIAL" else any(d.type.value == want for d in h.discrepancies)
    if ok:
        cm.classification_correct += 1
        m.classification_correct_total += 1
        cm.pairing_correct += 1
        m.pairing_correct_total += 1
    else:
        sm.mismatches.append(f"{sku}: drawing reference row expected {want}, got {h.classification.value} {[d.type.value for d in h.discrepancies]}")


def revision_change_key(r: CheckResult) -> str:
    """Stable key for an Old ↔ New row, derived from what changed (not from row ids)."""
    if r.role == "header":
        return "HEADER"
    e = r.explanation
    a_desc = _key(r.source_a.description) if r.source_a is not None else None
    b_desc = _key(r.source_b.description) if r.source_b is not None else None
    if "EXPECTED CHANGE ABSENT" in e:
        return f"ABSENT:{a_desc or b_desc}"
    if "already present" in e or "already absent" in e or "already applied" in e:
        return f"SATISFIED:{a_desc or b_desc}"
    if "DESCRIPTION CHANGED" in e:
        return f"DESC:{b_desc}"
    if "QUANTITY CHANGED" in e:
        return f"QTY:{b_desc}"
    if e.startswith("EXPECTED REMOVED") or e.startswith("REMOVED"):
        return f"REMOVED:{a_desc}"
    if e.startswith("EXPECTED ADDED") or e.startswith("ADDED"):
        return f"ADDED:{b_desc}"
    return f"UNCHANGED:{b_desc or a_desc}"


def _score_revision(m: Metrics, sm: SkuMetrics, run: Run, sku: str, exp_sku) -> None:
    if not exp_sku.label_revision:
        return
    cm = m.per_check.setdefault("LABEL_REVISION", CheckMetrics())
    rows = [r for r in run.results if r.sku == sku and r.check is CheckType.LABEL_REVISION and r.role in ("change", "header")]
    by_key = {revision_change_key(r): r for r in rows}
    covered = set()
    for exp in exp_sku.label_revision:
        cm.scored_rows += 1
        m.scored_rows += 1
        kind, _, text = exp.change_key.partition(":")
        key = kind if kind == "HEADER" else f"{kind}:{_key(text)}"
        label = f"{sku} LABEL_REVISION {exp.change_key}"
        pred = by_key.get(key)
        if pred is None:
            sm.mismatches.append(f"{label}: no revision row produced (have {sorted(by_key)})")
            _score_discrepancies(m, sm, None, exp, label, "LABEL_REVISION")
            continue
        covered.add(pred.row_id)
        cm.pairing_correct += 1
        m.pairing_correct_total += 1
        if pred.classification is exp.classification:
            cm.classification_correct += 1
            m.classification_correct_total += 1
        else:
            sm.mismatches.append(f"{label}: classified {pred.classification.value}, expected {exp.classification.value}")
        _score_discrepancies(m, sm, pred, exp, label, "LABEL_REVISION")
    for r in rows:
        if r.row_id in covered:
            continue
        extra = [d.type.value for d in r.discrepancies if d.severity is not Severity.INFO]
        if extra:
            sm.mismatches.append(f"{sku} LABEL_REVISION {revision_change_key(r)}: row not in ground truth reports {extra}")
            for t in extra:
                _bump(m, sm, t, "fp", "LABEL_REVISION")


def _score_coverage(m: Metrics, run: Run, gt: GroundTruth) -> None:
    expected = {(x.pco, x.code) for x in gt.coverage.missing_boms}
    predicted = {(_pco_number(r), r.sku) for r in run.results if r.check is CheckType.PCO_BOM and any(d.type is DiscrepancyType.BOM_MISSING_FOR_AFFECTED_CODE for d in r.discrepancies)}
    if not expected and not predicted:
        return
    cm = m.per_check.setdefault("COVERAGE", CheckMetrics())
    dummy = SkuMetrics(sku="COVERAGE")
    for _ in predicted & expected:
        _bump(m, dummy, "BOM_MISSING_FOR_AFFECTED_CODE", "tp", "COVERAGE")
    for pair in predicted - expected:
        _bump(m, dummy, "BOM_MISSING_FOR_AFFECTED_CODE", "fp", "COVERAGE")
        m.mismatches.append(f"coverage: unexpected missing-BOM finding for {pair[0]} / {pair[1]}")
    for pair in expected - predicted:
        _bump(m, dummy, "BOM_MISSING_FOR_AFFECTED_CODE", "fn", "COVERAGE")
        m.mismatches.append(f"coverage: expected missing-BOM finding for {pair[0]} / {pair[1]} not reported")
    cm.scored_rows += len(expected)
    cm.classification_correct += len(predicted & expected)
