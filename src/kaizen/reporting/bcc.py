"""BD's BOM cross-check (BCC) template: Label VS BOM, Drawings VS BOM and Combined sheets, each with summary counts.

The template's wording is kept (S.No, Description Match, Approved By Facilitator, Approved by IR, ...). Reviewer
decisions and approvals are applied when a review bundle is supplied; otherwise the engine's results stand.
"""

import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill

from kaizen.checks.bom_drawing import callouts
from kaizen.models import CheckResult, CheckType, DiscrepancyType, DocType, Document, MatchLevel, Run
from kaizen.reporting.excel import ReviewBundle
from kaizen.reporting.sku_excel import BODY_FONT, BOLD_FONT, _sheet_name

EXACT, PARTIAL, POTENTIAL, MISMATCH = "Exact match", "Partial match", "Potential Match", "Mismatch"
QTY_EXACT, QTY_DIFFERENT, NOT_COMPARED = "Exact match", "No match", "N/A"
LABEL_HEADERS = ["S.No", "Label Description", "Label Qty", "BOM Component No", "BOM Description", "BOM Qty", "Description Match", "Qty Match", "Remarks"]
DRAWING_HEADERS = ["S.No", "Drawing Description", "BOM Component No", "BOM Description", "BOM Qty", "Description Match", "Remarks"]
COMBINED_HEADERS = ["S.No", "Label Description", "Drawing Description", "BOM Description", "BOM Component No", "Label VS BOM Description",
                    "Drawing VS BOM Description", "Description Match", "Label Qty", "BOM Qty", "Qty Match", "Status", "Remarks", "Time stamp",
                    "Approved By Facilitator", "Approved by IR"]
WIDTHS = {"S.No": 6, "Label Description": 42, "Drawing Description": 34, "BOM Description": 34, "BOM Component No": 18, "Label Qty": 10,
          "BOM Qty": 10, "Description Match": 22, "Qty Match": 13, "Remarks": 60, "Label VS BOM Description": 22, "Drawing VS BOM Description": 22,
          "Status": 18, "Time stamp": 20, "Approved By Facilitator": 26, "Approved by IR": 26}
HEADER_FILL = PatternFill("solid", fgColor="F5F5F5")
WRAP = Alignment(vertical="top", wrap_text=True)
_QUANTITY_FINDINGS = {DiscrepancyType.QTY_MISMATCH, DiscrepancyType.QUANTITY_BASIS_UNCONFIRMED}
# The combined result is the least favourable individual result.
_RANK = {EXACT: 0, PARTIAL: 1, POTENTIAL: 2, MISMATCH: 4}
_PART_NUMBER_RE = re.compile(r"\b((?:LAB|BAW)\d{5,}[A-Z]?)\b")


def _missing(side: str) -> str:
    return f"Missing data in {side}"


def _rank(result: str) -> int:
    return _RANK.get(result, 3)  # missing data sits between a candidate and a confirmed conflict


def _quantity(value) -> int | float | None:
    if value is None:
        return None
    number = Decimal(str(value))
    return int(number) if number == number.to_integral_value() else float(number)


def _latest(slots: dict) -> Any | None:
    return next((slots[slot] for slot in sorted(slots, reverse=True)), None) if slots else None


def description_match(row: CheckResult, review: ReviewBundle | None, missing_side: tuple[str, str]) -> str:
    """BCC wording for one comparison: the description verdict only; quantities have their own column."""
    decision = _latest(review.decisions.get(row.row_id, {})) if review else None
    final = review.finals.get(row.row_id) if review else None
    override = decision.override_classification if decision and decision.decision == "OVERRIDE" else None
    if override == "MISSING" or (row.source_a is None) != (row.source_b is None) and not override:
        return _missing(missing_side[0] if row.source_a is None else missing_side[1])
    if override:
        return {"EXACT": EXACT, "EQUIVALENT": PARTIAL, "POTENTIAL": POTENTIAL}.get(override, MISMATCH)
    description_findings = [d for d in row.discrepancies if d.type not in _QUANTITY_FINDINGS]
    kind = final.final_decision if final else decision.decision if decision else None
    if kind == "CONFIRM_DISCREPANCY" and description_findings:
        return MISMATCH
    if row.classification.value == "MISMATCH" and any(d.type is DiscrepancyType.DESC_MISMATCH for d in row.discrepancies):
        return MISMATCH
    if row.match_level is MatchLevel.EXACT:
        return EXACT
    if row.match_level is MatchLevel.RELATIONSHIP or kind == "ACCEPT":
        return PARTIAL
    return POTENTIAL


def quantity_match(row: CheckResult) -> str:
    a, b = row.source_a, row.source_b
    if not a or not b or a.quantity is None or b.quantity is None:
        return NOT_COMPARED
    return QTY_EXACT if Decimal(a.quantity) == Decimal(b.quantity) else QTY_DIFFERENT


def remarks(row: CheckResult, review: ReviewBundle | None) -> str:
    parts = [d.detail for d in row.discrepancies if d.severity.value != "INFO" or row.requires_validation]
    if row.match_level is MatchLevel.RELATIONSHIP and row.relationship_id:
        parts.insert(0, f"Equivalent wording per approved terminology {row.relationship_id}")
    elif row.source_a and row.source_b and row.match_level not in (MatchLevel.EXACT, MatchLevel.RELATIONSHIP) and row.score is not None:
        parts.insert(0, f"Similar wording (score {row.score:.2f}); confirm the pairing")
    decision = _latest(review.decisions.get(row.row_id, {})) if review else None
    if decision and decision.comment:
        parts.append(f"Reviewer: {decision.comment}")
    return "; ".join(dict.fromkeys(parts))


def _timestamp(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return value


def review_status(rows: list[CheckResult], review: ReviewBundle | None) -> dict:
    """Status, time stamp and names for one or more comparisons shown on a single line."""
    decisions = [d for r in rows if review for d in [_latest(review.decisions.get(r.row_id, {}))] if d]
    finals = [f for r in rows if review for f in [review.finals.get(r.row_id)] if f]
    # A comparison the engine cleared needs no review; the line is settled once every other one is approved.
    open_rows = [r for r in rows if r.requires_validation and not (review and review.finals.get(r.row_id))]
    if not open_rows:
        status = "Approved" if finals else "Cleared by engine"
    elif decisions or finals:
        status = "Awaiting approval"
    else:
        status = "Not reviewed"
    approvers = [f"{f.finalized_by}{' (self-approved)' if getattr(f, 'self_approved', False) or f.note.startswith('Self-approved.') else ''}" for f in finals]
    stamps = [f.finalized_at for f in finals] or [d.decided_at for d in decisions]
    return {"Status": status, "Time stamp": _timestamp(max(stamps)) if stamps else None,
            "Approved By Facilitator": ", ".join(dict.fromkeys(d.reviewer for d in decisions)) or None,
            "Approved by IR": ", ".join(dict.fromkeys(approvers)) or None}


def _label_part_number(labels: list[Document], bom: Document | None) -> str:
    numbers = []
    for label in labels:
        printed = next((m.group(1) for line in label.text_lines if (m := _PART_NUMBER_RE.search(line.description))), None)
        named = _PART_NUMBER_RE.search(Path(label.path).stem.upper())
        numbers.append(printed or (named.group(1) if named else None))
    if not any(numbers) and bom:
        unit = next((i.item_number for i in bom.items if i.item_number and _PART_NUMBER_RE.fullmatch(i.item_number) and "UNIT LABEL" in i.description.upper()), None)
        numbers = [unit]
    return ", ".join(dict.fromkeys(n for n in numbers if n)) or ", ".join(label.sku or "" for label in labels) or "not supplied"


def _drawing_number(drawings: list[Document]) -> str:
    named = [f"{d.header.get('drawing_number') or Path(d.path).stem}" + (f" Rev {d.header['revision']}" if d.header.get("revision") else "") for d in drawings]
    return ", ".join(dict.fromkeys(named)) or "not supplied"


def _write_table(ws, start: int, headers: list[str], rows: list[dict]) -> int:
    for col, label in enumerate(headers, 1):
        cell = ws.cell(start, col, label)
        cell.font, cell.fill, cell.alignment = BOLD_FONT, HEADER_FILL, WRAP
        ws.column_dimensions[cell.column_letter].width = WIDTHS.get(label, 16)
    line = start
    for line, values in enumerate(rows, start + 1):
        for col, label in enumerate(headers, 1):
            cell = ws.cell(line, col, values.get(label))
            cell.font, cell.alignment = BODY_FONT, WRAP
    return line


def _write_metrics(ws, start: int, counts: dict[str, int], notes: list[str]) -> None:
    for col, label in ((2, "Metric"), (3, "Count")):
        cell = ws.cell(start, col, label)
        cell.font, cell.fill = BOLD_FONT, HEADER_FILL
    for line, (label, count) in enumerate(counts.items(), start + 1):
        ws.cell(line, 2, label).font = BODY_FONT
        ws.cell(line, 3, count).font = BODY_FONT
    for line, note in enumerate(dict.fromkeys(notes), start + len(counts) + 2):
        ws.cell(line, 2, f"Note: {note}").font = BODY_FONT


def _notes(results: list[CheckResult]) -> list[str]:
    """Document-level findings (identity, revision, applicability) that no component line carries."""
    return [d.detail for r in results if r.role in ("header", "reference") for d in r.discrepancies]


def _check_rows(results: list[CheckResult], check: CheckType) -> list[CheckResult]:
    return [r for r in results if r.check is check and r.role == "item"]


def _label_sheet(ws, rows: list[CheckResult], results: list[CheckResult], labels: list[Document], bom: Document | None, review) -> None:
    table = [{"Label Description": r.source_b.description if r.source_b else None, "Label Qty": _quantity(r.source_b.quantity) if r.source_b else None,
              "BOM Component No": r.source_a.item_number if r.source_a else None, "BOM Description": r.source_a.description if r.source_a else None,
              "BOM Qty": _quantity(r.source_a.quantity) if r.source_a else None, "Description Match": description_match(r, review, ("BOM", "Label")),
              "Qty Match": quantity_match(r), "Remarks": remarks(r, review)} for r in rows]
    for n, values in enumerate(table, 1):
        values["S.No"] = n
    last = _write_table(ws, 1, LABEL_HEADERS, table)
    if not labels:
        ws.cell(last + 1, 2, "No label document in this set; nothing to compare.").font = BODY_FONT
        last += 1
    paired = [t for t in table if t["Label Description"] and t["BOM Component No"]]
    _write_metrics(ws, last + 3, {
        "Total Label Components": sum(len(label.items) for label in labels),
        "Components Found in BOM": len(bom.items) if bom else 0,
        "Label components found in BOM": len({t["Label Description"] for t in paired}),
        "Description Mismatches": sum(t["Description Match"] == MISMATCH or t["Description Match"].startswith("Missing") for t in table),
        "Qty Mismatches": sum(t["Qty Match"] == QTY_DIFFERENT for t in table),
        "Fully Matched Components": sum(t["Description Match"] in (EXACT, PARTIAL) and t["Qty Match"] == QTY_EXACT for t in table),
    }, _notes([r for r in results if r.check is CheckType.BOM_LABEL]))


def _drawing_sheet(ws, rows: list[CheckResult], results: list[CheckResult], drawings: list[Document], bom: Document | None, review) -> None:
    table = [{"Drawing Description": r.source_b.description if r.source_b else None, "BOM Component No": r.source_a.item_number if r.source_a else None,
              "BOM Description": r.source_a.description if r.source_a else None, "BOM Qty": _quantity(r.source_a.quantity) if r.source_a else None,
              "Description Match": description_match(r, review, ("BOM", "Drawing")), "Remarks": remarks(r, review)} for r in rows]
    for n, values in enumerate(table, 1):
        values["S.No"] = n
    last = _write_table(ws, 1, DRAWING_HEADERS, table)
    if not drawings:
        ws.cell(last + 1, 2, "No drawing in this set; nothing to compare.").font = BODY_FONT
        last += 1
    _write_metrics(ws, last + 3, {
        "Total Drawing Components": sum(len(callouts(d)) for d in drawings),
        "Total Components Found in BOM": len(bom.items) if bom else 0,
        "Drawing components found in BOM": len({t["Drawing Description"] for t in table if t["Drawing Description"] and t["BOM Component No"]}),
        "Description Mismatches": sum(t["Description Match"] == MISMATCH or t["Description Match"].startswith("Missing") for t in table),
        "Fully Matched Components": sum(t["Description Match"] in (EXACT, PARTIAL) for t in table),
    }, _notes([r for r in results if r.check is CheckType.BOM_DRAWING]))


def _combined_sheet(ws, label_rows, drawing_rows, results, labels, drawings, bom: Document | None, sku: str, review) -> None:
    lines = [f"SKU Number - {sku} (BOM Parent Item number)", f"Label Part number - {_label_part_number(labels, bom)} (Label part number)",
             f"Drawing Number - {_drawing_number(drawings)} (Drawing number)"]
    for n, text in enumerate(lines, 1):
        ws.cell(n, 1, text).font = BOLD_FONT if n == 1 else BODY_FONT
        ws.merge_cells(start_row=n, start_column=1, end_row=n, end_column=len(COMBINED_HEADERS))
    # One line per BOM component, then label lines and drawing callouts that no BOM component explains.
    by_component: dict[str, dict[str, list[CheckResult]]] = {}
    extra: list[tuple[str, CheckResult]] = []
    for kind, rows in (("label", label_rows), ("drawing", drawing_rows)):
        for row in rows:
            if row.source_a is None:
                extra.append((kind, row))
            else:
                by_component.setdefault(row.source_a.id, {"label": [], "drawing": []})[kind].append(row)
    order = [i.id for i in bom.items] if bom else []
    table = []
    for component in sorted(by_component, key=lambda key: order.index(key) if key in order else len(order)):
        table.append(_combined_line(by_component[component]["label"], by_component[component]["drawing"], review))
    table.extend(_combined_line([row] if kind == "label" else [], [row] if kind == "drawing" else [], review) for kind, row in extra)
    for n, values in enumerate(table, 1):
        values["S.No"] = n
    totals = {"Label Description": f"Total components = {sum(len(label.items) for label in labels)}",
              "Drawing Description": f"Total components = {sum(len(callouts(d)) for d in drawings)}",
              "BOM Description": f"Total components = {len(bom.items) if bom else 0}"}
    _write_table(ws, 4, COMBINED_HEADERS, [])
    for col, label in enumerate(COMBINED_HEADERS, 1):
        if label in totals:
            cell = ws.cell(5, col, totals[label])
            cell.font, cell.fill = BOLD_FONT, HEADER_FILL
    for line, values in enumerate(table, 6):
        for col, label in enumerate(COMBINED_HEADERS, 1):
            cell = ws.cell(line, col, values.get(label))
            cell.font, cell.alignment = BODY_FONT, WRAP
    for line, note in enumerate(dict.fromkeys(_notes(results)), 6 + len(table) + 1):
        ws.cell(line, 2, f"Note: {note}").font = BODY_FONT
    ws.freeze_panes = "B6"


def _combined_line(label_rows: list[CheckResult], drawing_rows: list[CheckResult], review) -> dict:
    label_results = [description_match(r, review, ("BOM", "Label")) for r in label_rows]
    drawing_results = [description_match(r, review, ("BOM", "Drawing")) for r in drawing_rows]
    individual = label_results + drawing_results
    bom_item = next((r.source_a for r in label_rows + drawing_rows if r.source_a), None)
    quantities = [quantity_match(r) for r in label_rows]
    remarks_text = [f"Label: {text}" for r in label_rows if (text := remarks(r, review))] + [f"Drawing: {text}" for r in drawing_rows if (text := remarks(r, review))]
    return {
        "Label Description": "; ".join(dict.fromkeys(r.source_b.description for r in label_rows if r.source_b)) or None,
        "Drawing Description": "; ".join(dict.fromkeys(r.source_b.description for r in drawing_rows if r.source_b)) or None,
        "BOM Description": bom_item.description if bom_item else None, "BOM Component No": bom_item.item_number if bom_item else None,
        "Label VS BOM Description": max(label_results, key=_rank) if label_results else "Not applicable",
        "Drawing VS BOM Description": max(drawing_results, key=_rank) if drawing_results else "Not applicable",
        "Description Match": max(individual, key=_rank),
        "Label Qty": "; ".join(dict.fromkeys(str(_quantity(r.source_b.quantity)) for r in label_rows if r.source_b and r.source_b.quantity is not None)) or None,
        "BOM Qty": _quantity(bom_item.quantity) if bom_item else None,
        "Qty Match": QTY_DIFFERENT if QTY_DIFFERENT in quantities else QTY_EXACT if QTY_EXACT in quantities else NOT_COMPARED,
        "Remarks": "\n".join(remarks_text), **review_status(label_rows + drawing_rows, review),
    }


def bcc_workbook(run: Run, review: ReviewBundle | None = None) -> Workbook:
    wb = Workbook()
    wb.remove(wb.active)
    docs = {d.id: d for d in run.documents}
    used: set[str] = set()
    groups = run.groups or []
    for group in groups:
        members = [docs[i] for i in group.document_ids if i in docs]
        bom = next((d for d in members if d.doc_type is DocType.BOM), None)
        labels = [d for d in members if d.doc_type is DocType.LABEL and d.header.get("revision_role") != "old"]
        drawings = [d for d in members if d.doc_type is DocType.DRAWING]
        results = [r for r in run.results if r.sku == group.sku]
        label_rows, drawing_rows = _check_rows(results, CheckType.BOM_LABEL), _check_rows(results, CheckType.BOM_DRAWING)
        prefix = "" if len(groups) == 1 else f"{group.sku} "
        _label_sheet(wb.create_sheet(_sheet_name(f"{prefix}Label VS BOM", used)), label_rows, results, labels, bom, review)
        _drawing_sheet(wb.create_sheet(_sheet_name(f"{prefix}Drawings VS BOM", used)), drawing_rows, results, drawings, bom, review)
        _combined_sheet(wb.create_sheet(_sheet_name(f"{prefix}Combined", used)), label_rows, drawing_rows, results, labels, drawings, bom, group.sku, review)
    if not groups:
        wb.create_sheet("Combined").cell(1, 1, "No document sets in this run.")
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 100
        ws.page_setup.orientation = "landscape"
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    return wb


def export_bcc(workspace, run: Run, path: Path | str) -> Path:
    """The BCC workbook with the workspace's current decisions and approvals."""
    from kaizen.reporting.excel import review_store

    review, _ = review_store(workspace, run)
    rid = run.metadata.run_id
    with workspace.db.lock:
        bundle = ReviewBundle(decisions=review.all_decisions(rid), finals=review.finals(rid))
    path = Path(path)
    bcc_workbook(run, bundle).save(path)
    return path
