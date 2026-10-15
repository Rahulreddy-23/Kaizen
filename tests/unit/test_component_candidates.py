"""Semantic and workflow regression cases use synthetic component descriptions."""

import pytest

from kaizen.checks.bom_drawing import run_bom_drawing_check
from kaizen.checks.bom_label import run_bom_label_check
from kaizen.checks.label_drawing import run_label_drawing_check
from kaizen.matching.ladder import MatchLadder
from kaizen.matching.normalize import normalize
from kaizen.models import Classification, DiscrepancyType, ItemCategory, SubQuantity, Thresholds
from kaizen.review.mining import relationship_eligible
from kaizen.terminology.store import RelationshipStore
from tests.unit.test_bom_label_check import bom_doc, label_doc
from tests.unit.test_pairing_engine import drawing_doc

TH = Thresholds()


def ladder():
    return MatchLadder(RelationshipStore(), TH)


@pytest.mark.parametrize('erp,label', [
    ('MASK, VAPOR BARRIER', 'Mask'),
    ('GOWN, AAMI LEVEL 3', 'Gown'),
    ('GLOVES, LATEX FREE, PURPLE', 'Gloves'),
    ('GAUZE PAD, 4X4 12 PLY', 'Gauze, 10 cm x 10 cm (4 in. x 4 in.)'),
    ('GAUZE PAD, 2X2 12 PLY', 'Gauze, 5 cm x 5 cm (2 in. × 2 in.)'),
    ('MICROINTRO, 4.5FR X 7CM', 'Microintroducer, 4.5 F (1.6 mm ID x 7 cm Length)'),
])
def test_short_wording_is_a_review_candidate_not_an_automatic_clear(erp, label):
    result = run_bom_label_check(bom_doc([('X100', erp, '1')]), label_doc([(label, '1')]), ladder(), TH)
    rows = [r for r in result if r.role == 'item']
    assert len(rows) == 1 and rows[0].source_a and rows[0].source_b
    assert rows[0].classification is Classification.POTENTIAL and rows[0].requires_validation


@pytest.mark.parametrize('erp,label', [
    ('GAUZE 2X2', 'Gauze 4 in x 4 in'),
    ('PICC 4FR SL', 'Single-Lumen PICC, 5 F'),
    ('PICC 5FR SL', 'Dual-Lumen PICC, 5 F'),
    ('NEEDLE 21G', 'Needle, 25 G'),
    ('SYRINGE 5ML', 'Syringe, saline, 10 mL'),
])
def test_known_specification_conflicts_cannot_be_assigned(erp, label):
    assert not ladder().match(erp, label).assignable


def test_funnel_cannot_consume_a_complete_picc_assembly():
    assert not ladder().match('FUNNEL STYLET', 'Single-Lumen PICC, 4 F, with Stylet Assembly and Stylet Funnel').assignable


def test_prefilled_syringe_and_a_syringe_label_are_not_component_equivalents():
    assert not ladder().match('SYRINGE 10ML LUER LOCK', 'Saline Syringe 10 mL').assignable
    assert not ladder().match('SYRINGE 10ML', 'SYRINGE LABEL').assignable


def test_approved_identity_does_not_clear_an_unknown_package_basis():
    rows = run_bom_label_check(bom_doc([('X1', 'GLOVES', '1')]),
        label_doc([('Gloves', '1', SubQuantity(value=1, kind='pair', raw='(1 pair)'))]), ladder(), TH)
    row = next(r for r in rows if r.role == 'item')
    assert row.classification is Classification.EXACT
    assert row.requires_validation
    assert [d.type for d in row.discrepancies] == [DiscrepancyType.QUANTITY_BASIS_UNCONFIRMED]


def test_assembly_proposal_preserves_all_members_and_requires_review():
    bom = bom_doc([('X1', 'PICC 4FR SL', '1'), ('X2', 'STYLET ASSY', '1'), ('X3', 'FUNNEL STYLET', '1')])
    label = label_doc([('Single-Lumen PICC, 4 F, with Stylet Assembly and Stylet Funnel', '1')])
    rows = [r for r in run_bom_label_check(bom, label, ladder(), TH) if r.role == 'item']
    assert len(rows) == 3 and len({r.source_b.id for r in rows}) == 1
    assert {r.source_a.item_number for r in rows} == {'X1', 'X2', 'X3'}
    assert all(r.classification is Classification.POTENTIAL and r.requires_validation for r in rows)
    assert all(r.source_a.attributes['assembly_candidate'] for r in rows)
    assert all(not relationship_eligible(r) for r in rows)


def test_overlabel_is_a_configuration_question_not_a_confirmed_absence():
    bom = bom_doc([('X1', 'SYRINGE 5ML', '1'), ('O1', 'STICKER, NO SALINE', '1', ItemCategory.LABEL)])
    label = label_doc([('Syringe, sodium chloride (saline), 10 mL', '1')])
    row = next(r for r in run_bom_label_check(bom, label, ladder(), TH) if r.source_b and 'saline' in r.source_b.description)
    assert row.source_a.item_number == 'O1'
    assert row.classification is Classification.POTENTIAL and row.requires_validation
    assert [d.type for d in row.discrepancies] == [DiscrepancyType.LABEL_CONFIGURATION_REVIEW]
    assert not relationship_eligible(row)


def test_a_different_referenced_drawing_blocks_component_findings():
    bom = bom_doc([('X1', 'MASK', '1'), ('DWG1234567', 'ASSEMBLY DRAWING', '0')])
    drawing = drawing_doc(['GOWN'])
    drawing.header['drawing_number'] = 'DWG7654321'
    rows = run_bom_drawing_check(bom, drawing, ladder(), TH)
    assert len(rows) == 1 and rows[0].role == 'reference'
    assert rows[0].discrepancies[0].type is DiscrepancyType.DRAWING_APPLICABILITY_UNCONFIRMED
    rows = run_label_drawing_check(label_doc([('Mask', '1')]), drawing, ladder(), TH, applicable=False)
    assert len(rows) == 1 and rows[0].role == 'reference'


def test_fused_scientific_words_keep_meaning_and_numbers():
    assert normalize('FlexuraTMGuidewire').tokens == normalize('Flexura Guidewire').tokens
    assert normalize('0.5mmODx 16mm Length').tokens == normalize('0.5 mm OD x 16 mm Length').tokens
    assert normalize('LidocaineHCl1%,5mLampule').tokens == normalize('Lidocaine HCl 1%, 5 mL ampule').tokens
    assert normalize('Gauze 2 in. × 2 in.').tokens == normalize('Gauze 2 in x 2 in').tokens


@pytest.mark.parametrize('part,accessory', [
    ('Single lumen PICC 6 F', 'PICC sterile barrier drape'),
    ('Needle 23 G', 'Needle holder with protective tube'),
    ('Nitrile gloves size M', 'Glove wallet'),
    ('Latex gloves size XL', 'Glove box'),
    ('Elastic bands', 'Remote cover with elastic bands'),
    ('Stylet', 'Catheter with stylet'),
    ('PICC 6 F', 'Catheter trimming device'),
    ('Catheter', 'Catheter trimming device'),
])
def test_component_and_accessory_are_distinct_for_unseen_wording(part, accessory):
    assert not ladder().match(part, accessory).assignable


@pytest.mark.parametrize('reverse', [False, True])
def test_drawing_assignment_uses_object_identity_independent_of_order_and_item_codes(reverse):
    descriptions = ['PICC barrier drape', 'Glove wallet', 'Needle holder with protective tube',
                    'Catheter inside tube', 'Gloves', 'Safety needle']
    if reverse:
        descriptions.reverse()
    bom = bom_doc([('RANDOM-A', 'PICC 6 F TL', '1'), ('RANDOM-B', 'NITRILE GLOVES XL', '1'),
                   ('RANDOM-C', 'NEEDLE 23G', '1')], parent='UNSEEN-KIT')
    rows = run_bom_drawing_check(bom, drawing_doc(descriptions), ladder(), TH)
    paired = {r.source_a.item_number: r for r in rows if r.role == 'item' and r.source_a and r.source_b}
    assert {key: row.source_b.description for key, row in paired.items()} == {
        'RANDOM-A': 'Catheter inside tube', 'RANDOM-B': 'Gloves', 'RANDOM-C': 'Safety needle'}
    assert all(r.requires_validation and r.classification is Classification.POTENTIAL for r in paired.values())


def test_both_barrier_variants_remain_ambiguous_without_specific_evidence():
    rows = run_label_drawing_check(label_doc([('Full body fenestrated drape', '1')]),
        drawing_doc(['PICC barrier drape', 'Other catheter barrier drape']), ladder(), TH)
    paired = next(r for r in rows if r.source_a)
    assert paired.requires_validation
    assert any(d.type is DiscrepancyType.AMBIGUOUS_MATCH for d in paired.discrepancies)


@pytest.mark.parametrize('alternative', ['Scissors', 'Catheter trimming device'])
def test_explicit_or_supports_each_alternative_without_teaching_equivalence(alternative):
    rows = run_label_drawing_check(label_doc([(alternative, '1')]),
        drawing_doc([('Scissors with protective tube OR catheter trimming device', True)]), ladder(), TH)
    row = next(r for r in rows if r.source_a)
    assert row.source_b and row.classification is Classification.POTENTIAL
    assert 'OR alternatives' in row.explanation
    assert not relationship_eligible(row)


def test_catheter_and_drape_shared_or_phrase_does_not_become_a_catheter_candidate():
    from kaizen.matching.ladder import MatchContext
    from kaizen.models import DocType
    assert not ladder().match('PICC 6 F', 'PICC OR other catheter barrier drape',
        MatchContext(doc_types=(DocType.BOM, DocType.DRAWING))).assignable


def test_shipping_tape_context_is_page_local_and_preserves_original_evidence():
    from kaizen.checks.bom_drawing import callouts
    drawing = drawing_doc(['SHIP CASE', 'INSERT/SPACER', 'TAPE', 'SURGICAL TAPE'])
    drawing.items[-1].evidence.page = 7
    original = [i.model_dump() for i in drawing.items]
    rows = run_label_drawing_check(label_doc([('Surgical tape', '1')]), drawing, ladder(), TH)
    paired = next(r for r in rows if r.source_a)
    assert paired.source_b.description == 'SURGICAL TAPE'
    sealing = next(r for r in rows if r.source_b and r.source_b.description == 'TAPE')
    assert sealing.role == 'exempt' and not sealing.requires_validation
    assert sealing.source_b.evidence.page == 1
    assert [i.model_dump() for i in drawing.items] == original
    assert len(callouts(drawing)) == 4
    # On a mixed clinical/packing page the word TAPE alone remains uncertain.
    drawing.items[-1].evidence.page = 1
    assert not next(i for i in callouts(drawing) if i.description == 'TAPE').attributes.get('matching_description')


@pytest.mark.parametrize('erp,callout', [
    ('CATH SECUREM DEV POUCHED', 'Catheter securement device'),
    ('TAPE MEASURING PAPER', 'Tape measure'),
    ('TRAY UPPER STERILE', 'Tray'),
    ('SHIPPING CASE SINGLE TRAY', 'Ship case'),
    ('INSERT SPACING FOAM', 'Insert/spacer'),
])
def test_abbreviated_and_packaging_counterparts_are_candidates(erp, callout):
    from kaizen.matching.ladder import MatchContext
    from kaizen.models import DocType
    out = ladder().match(erp, callout, MatchContext(doc_types=(DocType.BOM, DocType.DRAWING)))
    assert out.assignable and out.needs_confirmation


def test_approved_identity_reuse_preserves_scope_anchor_and_known_values():
    from kaizen.matching.ladder import MatchContext
    from kaizen.models import DocType, Relationship
    store = RelationshipStore([Relationship(id='REL-888', canonical='Safety scalpel', aliases=['DISPOSABLE SHARP'],
        item_anchors=['OPAQUE-9'], scope='sku:OTHER-KIT', doc_types=[DocType.BOM, DocType.DRAWING])])
    match = MatchLadder(store, TH)
    ctx = MatchContext(sku='OTHER-KIT', item_number='OPAQUE-9', doc_types=(DocType.BOM, DocType.DRAWING))
    out = match.match('Supplier opaque wording', 'Scalpel', ctx)
    assert out.assignable and out.needs_confirmation and out.level.value == 'L3_FUZZY'
    assert 'REL-888' in out.reason
    assert not match.match('Supplier opaque wording', 'Scalpel',
        MatchContext(sku='WRONG-KIT', item_number='OPAQUE-9', doc_types=ctx.doc_types)).assignable
    assert not match.match('Supplier opaque wording', 'Scalpel',
        MatchContext(sku=ctx.sku, item_number='WRONG-ITEM', doc_types=ctx.doc_types)).assignable
    assert not match.match('Supplier opaque wording', 'Scalpel',
        MatchContext(sku=ctx.sku, item_number=ctx.item_number, doc_types=(DocType.BOM, DocType.LABEL))).assignable
    assert store.get('REL-888').aliases == ['DISPOSABLE SHARP']


def test_missing_antiseptic_tint_is_unknown_instead_of_assumed_clear():
    from kaizen.matching.components import component
    assert 'tinted' not in component('ANTISEPTIC CHLORAPREP').values
    assert component('CHLORAPREP CLEAR').values['tinted'] is False
    assert not ladder().match('CHLORAPREP CLEAR 2ML', 'CHLORAPREP TINTED 2ML').assignable


def test_insertion_word_is_not_an_instruction_insert():
    from kaizen.matching.components import component
    assert component('CATHETER INSERTION').kind == 'catheter'
