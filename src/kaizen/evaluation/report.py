"""Console and JSON rendering of evaluation metrics."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from kaizen.evaluation.harness import Metrics


def render_console(m: Metrics, console: Console | None = None) -> None:
    console = console or Console()
    t = Table(title="Discrepancy detection vs ground truth")
    for col in ("Type", "TP", "FP", "FN", "Precision", "Recall", "F1"):
        t.add_column(col, justify="right" if col != "Type" else "left")
    for name, c in sorted(m.per_type.items()):
        t.add_row(name, str(c.tp), str(c.fp), str(c.fn), f"{c.precision:.3f}", f"{c.recall:.3f}", f"{c.f1:.3f}")
    o = m.overall
    t.add_row("[bold]OVERALL", f"[bold]{o.tp}", f"[bold]{o.fp}", f"[bold]{o.fn}", f"[bold]{o.precision:.3f}", f"[bold]{o.recall:.3f}", f"[bold]{o.f1:.3f}")
    console.print(t)
    c = Table(title="Per check")
    for col in ("Check", "Scored rows", "Class. accuracy", "TP", "FP", "FN", "Precision", "Recall", "F1"):
        c.add_column(col, justify="right" if col != "Check" else "left")
    for name, cm in sorted(m.per_check.items()):
        c.add_row(name, str(cm.scored_rows), f"{cm.classification_accuracy:.3f}", str(cm.counts.tp), str(cm.counts.fp), str(cm.counts.fn), f"{cm.counts.precision:.3f}", f"{cm.counts.recall:.3f}", f"{cm.counts.f1:.3f}")
    console.print(c)
    s = Table(title="Per SKU")
    for col in ("SKU", "Expected", "Pairing OK", "Class OK", "TP", "FP", "FN", "False missing"):
        s.add_column(col, justify="right" if col != "SKU" else "left")
    for sku, sm in m.per_sku.items():
        s.add_row(sku, str(sm.expected_rows), str(sm.pairing_correct), str(sm.classification_correct), str(sm.counts.tp), str(sm.counts.fp), str(sm.counts.fn), str(len(sm.false_missing)))
    console.print(s)
    console.print(f"Predicted classification counts: {m.counts}")
    console.print(f"Pairing accuracy {m.pairing_accuracy:.3f} | classification accuracy {m.classification_accuracy:.3f} | REF/parent accuracy {m.ref_check_accuracy:.3f} | false-missing violations {m.false_missing} | scored rows {m.scored_rows}")
    if m.missing_skus:
        console.print(f"[red]SKUs in ground truth with no results: {m.missing_skus}")
    if m.mismatches:
        console.print(f"[yellow]{len(m.mismatches)} disagreement(s) with ground truth:")
        for x in m.mismatches:
            console.print(f"  - {x}")
    else:
        console.print("[green]No disagreements with ground truth.")


def write_json(m: Metrics, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m.to_dict(), indent=2), encoding="utf-8")
    return path
