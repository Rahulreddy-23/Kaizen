"""Read-only, SKU-scoped projection of saved comparisons and source text.

Only recorded pairings create links. Connected items do not become new accepted
pairings, and exempt rows never become matches. The ordinary review snapshot
supplies current findings; this projection cannot change extraction or decisions.
"""

from collections import Counter, defaultdict
from pathlib import Path

KINDS = ("BOM", "LABEL", "DRAWING")
CHECKS = {"BOM_LABEL", "BOM_DRAWING", "LABEL_DRAWING"}
RANK = {"neutral": 0, "matched": 1, "attention": 2}


def _worst(statuses):
    return max(statuses, key=RANK.get, default="neutral")


def _status(result, snapshot):
    if result.role == "exempt":
        return "neutral"
    paired = result.source_a is not None and result.source_b is not None
    clean = snapshot["effective_classification"] in {"EXACT", "EQUIVALENT"} and not snapshot["pending_review"] and not snapshot["unresolved"]
    return "matched" if paired and clean else "attention"


def build_quick_view(run, snapshots, sku, view, serialize):
    groups = [{"sku": g.sku, "document_ids": g.document_ids} for g in run.groups]
    group = next((g for g in run.groups if g.sku == sku), None)
    if group is None:
        raise KeyError(sku)
    documents = [d for d in run.documents if d.id in group.document_ids and d.doc_type.value in KINDS]
    by_id = {i.id: i for d in documents for i in d.items}
    order = {item_id: n for n, item_id in enumerate(by_id)}
    doc_by_id = {d.id: d for d in documents}
    # Merged BOM comparisons keep one ID plus the original source locators.
    # Every contributing source row retains its own text, quantity and location.
    locators = defaultdict(list)
    for item in by_id.values():
        locators[item.doc_id, item.evidence.locator].append(item.id)

    def source_ids(item):
        if item is None or item.doc_id not in doc_by_id:
            return []
        ids = [item_id for loc in item.attributes.get("merged_locators", []) for item_id in locators[item.doc_id, loc] if item.item_number and by_id[item_id].item_number == item.item_number]
        if item.id in by_id:
            ids.append(item.id)
        return list(dict.fromkeys(ids))

    snapshots = {r["row_id"]: r for r in snapshots}
    links = {}
    related = defaultdict(list)
    neighbours = defaultdict(list)
    for result in run.results:
        if result.sku != sku or result.check.value not in CHECKS or result.role not in {"item", "exempt"}:
            continue
        a, b = source_ids(result.source_a), source_ids(result.source_b)
        if not a and not b:
            continue
        snap = snapshots[result.row_id]
        status = _status(result, snap)
        links[result.row_id] = {
            "row_id": result.row_id,
            "check": result.check.value,
            "status": status,
            "classification": snap["effective_classification"],
            "engine_classification": result.classification.value,
            "state": snap["state"],
            "explanation": result.explanation,
            "findings": snap["current_discrepancies"],
            "merged_rows": max((i.attributes.get("merged_rows", 1) for i in (result.source_a, result.source_b) if i), default=1),
        }
        for item_id in dict.fromkeys(a + b):
            related[item_id].append(result.row_id)
        if result.role == "item":
            for left in a:
                for right in b:
                    neighbours[left].append(right)
                    neighbours[right].append(left)

    statuses = {item_id: _worst(links[r]["status"] for r in related[item_id]) for item_id in by_id}

    def cell(items, text=False):
        if not items:
            return None
        states = []
        for item in items:
            status = statuses.get(item.id, "neutral")
            if text and item.id not in statuses and item.evidence.bbox:
                box = item.evidence.bbox
                area = max(0, box.x1 - box.x0) * max(0, box.y1 - box.y0)
                owners = []
                for component in doc_by_id[item.doc_id].items:
                    other = component.evidence.bbox
                    if not other or component.evidence.page != item.evidence.page or not area:
                        continue
                    overlap = max(0, min(box.x1, other.x1) - max(box.x0, other.x0)) * max(0, min(box.y1, other.y1) - max(box.y0, other.y0))
                    if overlap / area >= 0.8:
                        owners.append(statuses.get(component.id, "neutral"))
                status = _worst(owners)
            states.append(status)
        rendered = [serialize(i) | {"id": i.id} for i in items]
        if text:
            for item in rendered:
                if item["id"] in statuses:
                    item["description"] = item["raw_text"] or item["description"]
        return {"status": _worst(states), "items": rendered}

    rows = []
    used = set()
    if view == "text":
        columns = {kind: [i for d in documents if d.doc_type.value == kind for i in (d.text_lines or d.items)] for kind in KINDS}
        for n in range(max(map(len, columns.values()), default=0)):
            rows.append({"id": f"text:{n}", "status": "neutral", "checks": [], "cells": {kind: cell([column[n]], text=True) if n < len(column) else None for kind, column in columns.items()}})
    else:
        for kind in KINDS:
            for item in list(by_id.values()):
                if item.doc_type.value != kind or item.id in used:
                    continue
                chosen = {item.id, *neighbours[item.id]}
                # An absent direct BOM/drawing pairing may have label evidence.
                # Show that recorded edge, preserving the unresolved BOM check.
                if kind == "BOM" and not any(by_id[i].doc_type.value == "DRAWING" for i in chosen):
                    chosen.update(j for i in list(chosen) if by_id[i].doc_type.value == "LABEL" for j in neighbours[i] if by_id[j].doc_type.value == "DRAWING")
                ordered = sorted(chosen, key=order.get)
                cells = {k: cell([by_id[i] for i in ordered if by_id[i].doc_type.value == k]) for k in KINDS}
                status = _worst(c["status"] for c in cells.values() if c)
                if status == "matched" and any(c is None for c in cells.values()):
                    status = "attention"
                checks = list(dict.fromkeys(r for i in ordered for r in related[i]))
                rows.append({"id": item.id, "status": status, "cells": cells, "checks": [links[r] for r in checks]})
                used.update(chosen)

    return {
        "sku": sku,
        "groups": groups,
        "view": view,
        "rows": rows,
        "counts": {s: sum(r["status"] == s for r in rows) for s in RANK},
        "documents": [{"id": d.id, "doc_type": d.doc_type.value, "file_name": Path(d.path).name, "warnings": d.warnings, "full_text": bool(d.text_lines), "items": len(d.items)} for d in documents],
    }


def filter_quick_view(payload, status, search, offset, limit):
    rows = payload["rows"]
    needle = search.strip().casefold()
    if status == "compared":
        rows = [r for r in rows if r["status"] != "neutral"]
    elif status != "all":
        rows = [r for r in rows if r["status"] == status]
    if needle:
        rows = [
            r
            for r in rows
            if any(
                needle in " ".join(str(i.get(k) or "") for k in ("description", "raw_text", "item_number", "file_name", "locator", "attributes")).casefold()
                for c in r["cells"].values()
                if c
                for i in c["items"]
            )
        ]
    return payload | {"rows": rows[offset : offset + limit], "total": len(rows), "offset": offset, "limit": limit, "filtered_counts": dict(Counter(r["status"] for r in rows))}
