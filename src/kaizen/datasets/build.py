"""Builds datasets/golden: documents, ground truth and SCENARIOS.md from the scenario definitions. Deterministic."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

from kaizen.datasets._stable import stabilize_zip
from kaizen.datasets.catalog import DRAWING_EXTRAS, DRAWING_NUMBER, DRAWING_PLANT, DRAWING_TITLE
from kaizen.datasets.drawing_docs import CalloutSpec, DrawingSpec, render_drawing_pdf
from kaizen.datasets.pco_docs import PcoSpec, render_pco_pdf, write_pco_xlsx
from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
from kaizen.datasets.scenarios import PCOS, SCENARIOS, Line, Scenario
from kaizen.ingest.quantity import parse_label_line

REQUIRED_SCENARIOS = [
    "exact", "reordered", "relationship", "qty-mismatch", "missing-on-label", "extra-label-item", "ref-mismatch", "ambiguous",
    "non-physical", "inactive", "parenthetical-quantity", "wrapped-line", "similar-descriptions", "fuzzy-must-not-accept",
]
TABLE_HEADER = ["Level", "Component Item", "Component Description", "Branch/Plant", "Quantity Per", "Ext Qty", "UM", "T", "Effective From", "Effective Thru", "Oper Seq No"]
FIXED_TIME = datetime(2026, 9, 3, tzinfo=timezone.utc)


def _label_line(l: Line) -> str:
    return f"{l.label_qty} Each - {l.label_text}"


def _parsed_label_desc(l: Line) -> str | None:
    return parse_label_line(_label_line(l)).description if l.label_text else None


def _bom_rows(s: Scenario) -> list[BomRowSpec]:
    rows = []
    for l in s.lines:
        if l.item is None:
            continue
        rows.append(BomRowSpec(item=l.item, description=l.bom_desc or "", qty_per=l.bom_qty or "", t=l.t, oper_seq=l.oper_seq, eff_thru=l.eff_thru))
    return rows


def _table_rows(s: Scenario) -> list[list[str]]:
    out = []
    for r in _bom_rows(s):
        ext = f"{float(r.qty_per):.6f}" if r.qty_per not in ("", None) else ""
        out.append([r.level, r.item, r.description, r.branch, r.qty_per, ext, r.um, r.t, r.eff_from, r.eff_thru, r.oper_seq])
    return out


def _write_xlsx(s: Scenario, path: Path) -> None:
    wb = openpyxl.Workbook()
    wb.properties.created = FIXED_TIME
    wb.properties.modified = FIXED_TIME
    wb.properties.creator = "Kaizen synthetic dataset"
    wb.properties.lastModifiedBy = "Kaizen synthetic dataset"
    ws = wb.active
    ws.title = "BOM"
    ws.append(["Bill of Material Print"])
    ws.append(["Parent Item", s.parent_item, None, "Parent Description", s.parent_description])
    ws.append(["Branch/Plant", "5150", None, "As of Date", "09/03/25"])
    ws.append([])
    ws.append(TABLE_HEADER)
    for row in _table_rows(s):
        ws.append(row)
    wb.save(path)
    stabilize_zip(path)


def _write_csv(s: Scenario, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Parent Item", s.parent_item])
        w.writerow(["Parent Description", s.parent_description])
        w.writerow(["As of Date", "09/03/25"])
        w.writerow(TABLE_HEADER)
        for row in _table_rows(s):
            w.writerow(row)


def _drawing_spec(s: Scenario) -> DrawingSpec:
    callouts = [CalloutSpec(l.callout, l.callout_es or l.callout) for l in s.lines if l.callout]
    callouts += [CalloutSpec(en, es, conditional=cond) for en, es, cond in DRAWING_EXTRAS]
    callouts += [CalloutSpec(x.en, x.es, conditional=x.conditional) for x in s.extra_callouts]
    return DrawingSpec(drawing_number=DRAWING_NUMBER, revision=s.drawing_rev, title=DRAWING_TITLE, plant=DRAWING_PLANT, callouts=callouts, cavities=["2", "3", "5"], checked_by="Prasanth Kannan")


def _drawing_rows(s: Scenario) -> tuple[list[dict], list[dict]]:
    bom_rows, label_rows = [], []
    for l in s.lines:
        if l.item and l.expected is not None and l.expected_drawing is not None:
            bom_rows.append({"bom_item": l.item, "drawing": l.callout, "classification": l.expected_drawing.classification, "discrepancies": list(l.expected_drawing.discrepancies), "scenario": l.expected_drawing.scenario})
        elif l.item is None and l.callout and l.expected_drawing is not None:
            bom_rows.append({"bom_item": None, "drawing": l.callout, "classification": l.expected_drawing.classification, "discrepancies": list(l.expected_drawing.discrepancies), "scenario": l.expected_drawing.scenario})
        if l.expected_label_drawing is not None and (l.label_text or l.callout):
            label_rows.append({"label": _parsed_label_desc(l) if l.label_text else None, "drawing": l.callout, "classification": l.expected_label_drawing.classification, "discrepancies": list(l.expected_label_drawing.discrepancies), "scenario": l.expected_label_drawing.scenario})
    for x in s.extra_callouts:
        if x.expected_bom is not None:
            bom_rows.append({"bom_item": None, "drawing": x.en, "classification": x.expected_bom.classification, "discrepancies": list(x.expected_bom.discrepancies), "scenario": x.expected_bom.scenario})
        if x.expected_label is not None:
            label_rows.append({"label": None, "drawing": x.en, "classification": x.expected_label.classification, "discrepancies": list(x.expected_label.discrepancies), "scenario": x.expected_label.scenario})
    return bom_rows, label_rows


def _old_label_contents(s: Scenario) -> list[str]:
    out = []
    for l in s.lines:
        if not l.label_text:
            continue
        if l.label_text in s.old_label_remove:
            continue
        text = s.old_label_replace.get(l.label_text, l.label_text)
        qty = s.old_label_qty.get(l.label_text, l.label_qty)
        out.append(f"{qty} Each - {text}")
    return out + list(s.old_label_add)


def _ground_truth_entry(s: Scenario) -> dict:
    expected = []
    not_compared = []
    for l in s.lines:
        if l.expected is None:
            if l.item:
                not_compared.append(l.item)
            continue
        row = {"bom_item": l.item, "classification": l.expected.classification, "discrepancies": list(l.expected.discrepancies), "scenario": l.expected.scenario}
        if l.expected.label_any_of:
            row["label_any_of"] = [parse_label_line(f"1 Each - {t}").description for t in l.expected.label_any_of]
        else:
            row["label"] = _parsed_label_desc(l)
        expected.append(row)
    pco_rows = [{"change_key": e.change_key, "classification": e.classification, "discrepancies": list(e.discrepancies), "scenario": e.scenario} for e in s.pco_bom]
    bom_drawing, label_drawing = _drawing_rows(s)
    rev_rows = [{"change_key": e.change_key, "classification": e.classification, "discrepancies": list(e.discrepancies), "scenario": e.scenario} for e in s.label_revision]
    return {"folder": s.folder, "ref_check": s.ref_check, "expected": expected, "bom_drawing": bom_drawing, "label_drawing": label_drawing, "drawing_ref": s.drawing_ref, "label_revision": rev_rows, "pco_bom": pco_rows, "not_compared": not_compared, "note": s.notes}


def _scenarios_md(scenarios: list[Scenario]) -> str:
    out = ["# Golden dataset scenarios", "", "Generated by `kaizen dataset build`. Each SKU plants known cases; `ground-truth.json` is generated from the same definitions.", ""]
    for s in scenarios:
        out += [f"## {s.folder} — parent {s.parent_item}, label REF {s.ref}, BOM as {s.bom_format.upper()}", "", s.notes, "", f"Tags: {', '.join(s.tags)}", "", "| BOM item | BOM description | BOM qty | Label line | Expected | Discrepancies | Case |", "|---|---|---|---|---|---|---|"]
        for l in s.lines:
            if l.expected is None:
                continue
            out.append(f"| {l.item or '—'} | {l.bom_desc or '—'} | {l.bom_qty if l.bom_qty else '(blank)' if l.item else '—'} | {_label_line(l) if l.label_text else '— (absent)'} | {l.expected.classification} | {', '.join(l.expected.discrepancies) or '—'} | {l.expected.scenario} |")
        skipped = [f"{l.item} ({l.bom_desc})" for l in s.lines if l.expected is None and l.item]
        out += ["", f"Not compared (non-physical or inactive): {', '.join(skipped)}", ""]
        if s.pco_bom:
            out += ["PCO ↔ BOM expectations:", ""] + [f"- {e.change_key}: {e.classification} {', '.join(e.discrepancies) or ''} ({e.scenario})" for e in s.pco_bom] + [""]
        if s.label_revision:
            out += ["Old ↔ New label expectations (label_old.pdf → label.pdf):", ""] + [f"- {e.change_key}: {e.classification} {', '.join(e.discrepancies) or ''} ({e.scenario})" for e in s.label_revision] + [""]
        bom_rows, label_rows = _drawing_rows(s)
        out += [f"Drawing {DRAWING_NUMBER} rev {s.drawing_rev} (reference row expected {s.drawing_ref}); BOM ↔ Drawing findings: " + (", ".join(f"{r['bom_item'] or r['drawing']} {r['classification']} {'/'.join(r['discrepancies'])}" for r in bom_rows if r["discrepancies"]) or "none") + "; Label ↔ Drawing findings: " + (", ".join(f"{r['label'] or r['drawing']} {r['classification']} {'/'.join(r['discrepancies'])}" for r in label_rows if r["discrepancies"]) or "none"), ""]
    out += ["## PCOs", ""]
    for pco in PCOS:
        out += [f"### {pco.number} rev {pco.revision} ({pco.fmt.upper()}) — affected codes: {', '.join(pco.affected_codes)}", "", pco.notes, ""]
        for r in pco.rows:
            out.append(f"- {r.item_actual or '—'} → {r.item_proposed or '—'}: {r.description} (qty {r.qty_proposed or '—'}, seq {r.seq_proposed or '—'})")
        if pco.missing_codes:
            out.append(f"- affected codes without a BOM in the set: {', '.join(pco.missing_codes)} → BOM_MISSING_FOR_AFFECTED_CODE")
        out.append("")
    return "\n".join(out)


def build_golden(root: Path | str) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    gt = {"version": 1, "description": "Synthetic PowerPICC-style product family with seeded cross-check cases. Expectations are declared by hand in kaizen.datasets.scenarios.", "skus": {}}
    for s in SCENARIOS:
        folder = root / s.folder
        folder.mkdir(parents=True, exist_ok=True)
        for stale in folder.glob("bom.*"):
            stale.unlink()
        spec = BomSpec(parent_item=s.parent_item, parent_description=s.parent_description, rows=_bom_rows(s), annotations=list(s.annotations))
        if s.bom_format == "pdf":
            render_bom_pdf(spec, folder / "bom.pdf")
        elif s.bom_format == "xlsx":
            _write_xlsx(s, folder / "bom.xlsx")
        else:
            _write_csv(s, folder / "bom.csv")
        contents = [_label_line(l) for l in s.lines if l.label_text]
        render_label_pdf(LabelSpec(ref=s.ref, product_name=s.product_name, contents=contents), folder / "label.pdf")
        for stale in folder.glob("label_old.pdf"):
            stale.unlink()
        if s.old_label:
            render_label_pdf(LabelSpec(ref=s.ref, product_name=s.product_name, contents=_old_label_contents(s)), folder / "label_old.pdf")
        render_drawing_pdf(_drawing_spec(s), folder / "drawing.pdf")
        gt["skus"][s.parent_item] = _ground_truth_entry(s)
    pco_dir = root / "pco"
    pco_dir.mkdir(parents=True, exist_ok=True)
    for stale in pco_dir.glob("*"):
        stale.unlink()
    missing = []
    for pco in PCOS:
        spec = PcoSpec(pco_number=pco.number, revision=pco.revision, branch=pco.branch, affected_codes=pco.affected_codes, rows=pco.rows)
        if pco.fmt == "pdf":
            render_pco_pdf(spec, pco_dir / f"{pco.number}.pdf")
        else:
            write_pco_xlsx(spec, pco_dir / f"{pco.number}.xlsx")
        missing += [{"pco": pco.number, "code": c} for c in pco.missing_codes]
    gt["coverage"] = {"missing_boms": missing}
    (root / "ground-truth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "SCENARIOS.md").write_text(_scenarios_md(SCENARIOS), encoding="utf-8")
    return root
