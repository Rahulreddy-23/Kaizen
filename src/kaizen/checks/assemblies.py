"""Apply independently verified component membership with explicit per-unit allocations."""

from decimal import Decimal

from kaizen.checks.pairing import disc
from kaizen.matching.components import compatible
from kaizen.matching.components import component as describe_component
from kaizen.matching.normalize import normalize
from kaizen.models import CheckResult, CheckType, Classification, DiscrepancyType, MatchLevel, Severity


def apply_assemblies(a_items, b_items, rules, sku, ids, thresholds):
    claimed_a, claimed_b, results = set(), set(), []
    # Conflicting/overlapping rules never choose a winner silently.
    proposals = []
    for rule in rules:
        if rule["sku"] != sku:
            continue
        labels = [b for b in b_items if normalize(b.description).sorted_key == rule["label_key"]]
        members = []
        missing = []
        for member in rule["members"]:
            hits = [a for a in a_items if a.item_number == member["item_number"] and normalize(a.description).sorted_key == member["description_key"]]
            if len(hits) != 1:
                missing.append(member['item_number'])
            else:
                members.append((hits[0], Decimal(str(member["quantity_per_unit"]))))
        if len(labels) == 1:
            proposals.append((rule, members, labels[0], missing))
    for rule, members, label, missing in proposals:
        member_ids = {a.id for a, _ in members}
        overlap = any(other is not rule and (label.id == other_label.id or member_ids & {a.id for a, _ in other_members}) for other, other_members, other_label, _ in proposals)
        if overlap or member_ids & claimed_a or label.id in claimed_b:
            continue
        for component, per_unit in members:
            expected = label.quantity * per_unit if label.quantity is not None else None
            equal = expected is not None and component.quantity == expected
            differences = []
            cls = Classification.EQUIVALENT if equal else Classification.MISMATCH
            if missing and equal:
                cls = Classification.POTENTIAL
                differences.append(disc(DiscrepancyType.MISSING_IN_BOM, Severity.MAJOR, f"Verified assembly members absent or changed: {', '.join(missing)}."))
            if not equal:
                differences.append(disc(DiscrepancyType.QTY_MISMATCH, Severity.MAJOR, f"Assembly member requires {per_unit} per label unit: BOM {component.quantity}, expected {expected}."))
            if min(component.extraction_confidence, label.extraction_confidence) < thresholds.low_confidence:
                differences.append(disc(DiscrepancyType.LOW_EXTRACTION_CONFIDENCE, Severity.INFO, "Assembly source extraction needs review."))
            results.append(CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_LABEL,
                source_a=component.model_copy(update={"attributes": {**component.attributes, "assembly_rule": rule["id"], "assembly_quantity_per_unit": str(per_unit), "assembly_member_ids": sorted(member_ids)}}),
                source_b=label, classification=cls, match_level=MatchLevel.RELATIONSHIP, score=1.0,
                explanation=f"Verified assembly {rule['id']}: '{label.description}' includes item {component.item_number}; allocation {per_unit} per label unit. BOM quantity {component.quantity}, required {expected}.",
                discrepancies=differences, requires_validation=bool(differences)))
        if missing:
            detail = f"Verified assembly {rule['id']} requires BOM members {', '.join(missing)}; these items are absent or their descriptions changed."
            results.append(CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_LABEL, source_b=label,
                classification=Classification.MISSING, match_level=MatchLevel.NONE, explanation=detail,
                discrepancies=[disc(DiscrepancyType.MISSING_IN_BOM, Severity.MAJOR, detail)], requires_validation=True))
        claimed_a.update(member_ids)
        claimed_b.add(label.id)
    return [a for a in a_items if a.id not in claimed_a], [b for b in b_items if b.id not in claimed_b], results


def propose_assemblies(a_items, b_items, sku, ids):
    """Keep explicitly described assemblies together as review-only proposals.

    An inferred member never establishes an approved allocation or consumes a
    complete assembly as a one-to-one match for just a funnel or stylet.
    """
    claimed_a, claimed_b, rows = set(), set(), []
    for label in b_items:
        text = normalize(label.description).normalized
        if describe_component(text).kind != "picc" or "WITH" not in text or "STYLET" not in text:
            continue
        required = ["picc", "stylet"] + (["funnel"] if "FUNNEL" in text else [])
        members = {}
        for kind in required:
            hits = [a for a in a_items if a.id not in claimed_a and describe_component(normalize(a.description).normalized).kind == kind]
            if kind == "picc":
                hits = [a for a in hits if not compatible(describe_component(normalize(a.description).normalized), describe_component(text))[0]]
            if len(hits) == 1:
                members[kind] = hits[0]
        if "picc" not in members or "stylet" not in members:
            continue
        missing = [kind for kind in required if kind not in members]
        for kind, item in members.items():
            detail = (f"ASSEMBLY CANDIDATE: label '{label.description}' explicitly includes a PICC and stylet"
                      f"{' and funnel' if 'funnel' in required else ''}; BOM {item.item_number} '{item.description}' is a possible {kind} member. "
                      "Confirm membership, specification and quantity per assembly before approval.")
            if missing:
                detail += f" No unique BOM candidate for: {', '.join(missing)}; an integrated component or missing member needs confirmation."
            differences = []
            if item.quantity is None or label.quantity is None or item.quantity != label.quantity:
                differences.append(disc(DiscrepancyType.QTY_MISMATCH, Severity.MINOR,
                                        f"Possible assembly allocation: BOM {item.quantity} versus label {label.quantity}; per-unit membership is unverified."))
            rows.append(CheckResult(row_id=ids.next(), sku=sku, check=CheckType.BOM_LABEL,
                        source_a=item.model_copy(update={"attributes": {**item.attributes, "assembly_candidate": True,
                            "assembly_member_ids": sorted(x.id for x in members.values()), "assembly_missing_member_types": missing}}),
                        source_b=label, classification=Classification.POTENTIAL, match_level=MatchLevel.FUZZY,
                        score=.9, candidate_score=.9, explanation=detail, discrepancies=differences, requires_validation=True))
            claimed_a.add(item.id)
        claimed_b.add(label.id)
    return [a for a in a_items if a.id not in claimed_a], [b for b in b_items if b.id not in claimed_b], rows
