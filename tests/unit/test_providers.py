"""Optional AI layer: NullProvider by default; suggestions are labelled, never authoritative; every call audited."""

from kaizen.ai.providers import AnthropicProvider, NullProvider, Suggestion, get_provider
from kaizen.matching.ladder import MatchLadder
from kaizen.models import MatchLevel, Thresholds
from kaizen.terminology.store import RelationshipStore


def test_null_provider_is_default_and_never_suggests(monkeypatch):
    monkeypatch.delenv("KAIZEN_AI_PROVIDER", raising=False)
    p = get_provider()
    assert isinstance(p, NullProvider) and p.name == "null"
    assert p.adjudicate("ABSORBENT TOWEL", "Towel, Absorbent", context={}) is None
    assert p.describe() == {"provider": "null", "model": None, "status": "disabled (no external calls)"}


def test_anthropic_provider_requires_explicit_opt_in_and_key(monkeypatch):
    monkeypatch.setenv("KAIZEN_AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = get_provider()
    assert isinstance(p, NullProvider)
    assert "ANTHROPIC_API_KEY" in p.reason


def test_anthropic_provider_with_fake_client_labels_output_as_suggestion(monkeypatch):
    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)

            class Block:
                text = '{"verdict": "SAME_ITEM", "confidence": 0.9, "rationale": "Both describe a 3 mL ChloraPrep applicator."}'

            class Msg:
                content = [Block()]
                model = kwargs["model"]

            return Msg()

    class FakeClient:
        messages = FakeMessages()

    p = AnthropicProvider(client=FakeClient(), model="claude-sonnet-5")
    s = p.adjudicate("CHLORAPREP APPLICATOR 3ML", "ChloraPrep Solution One-Step Applicator, 3 mL", context={"sku": "1295108NS"})
    assert isinstance(s, Suggestion)
    assert s.label == "AI SUGGESTION" and s.verdict == "SAME_ITEM" and s.confidence == 0.9 and "ChloraPrep" in s.rationale
    assert s.provider == "anthropic" and s.model == "claude-sonnet-5" and s.prompt_version and s.timestamp
    assert calls and "CHLORAPREP APPLICATOR 3ML" in str(calls[0]["messages"])


def test_ai_matcher_only_annotates_potential_rows_and_never_changes_classification():
    from kaizen.ai.matcher import AiAdjudicationMatcher

    class AlwaysSame:
        name = "fake"
        model = "fake-model"

        def adjudicate(self, a, b, context):
            return Suggestion(label="AI SUGGESTION", verdict="SAME_ITEM", confidence=0.99, rationale="looks identical", provider="fake", model="fake-model", prompt_version="test", timestamp="now")

        def describe(self):
            return {"provider": "fake", "model": "fake-model", "status": "enabled"}

    lad = MatchLadder(RelationshipStore.default(), Thresholds(), extra_matchers=[AiAdjudicationMatcher(AlwaysSame())])
    out = lad.match("MASK", "Measuring Tape")  # below the floor at every deterministic level
    assert out.level is MatchLevel.LLM
    assert out.weak is True and out.assignable is False  # an AI opinion never pairs items on its own
    assert "AI SUGGESTION" in out.reason and "looks identical" in out.reason
    assert out.score == 0.99


def test_provider_calls_are_recorded_in_run_metadata(tmp_path, monkeypatch):
    from kaizen.datasets.pdf_bom import BomRowSpec, BomSpec, render_bom_pdf
    from kaizen.datasets.pdf_label import LabelSpec, render_label_pdf
    from kaizen.pipeline import run_folder

    render_bom_pdf(BomSpec(parent_item="1295108NS", parent_description="KIT", rows=[BomRowSpec(item="0396447", description="ABSORBENT TOWEL")]), tmp_path / "sku-001" / "bom.pdf")
    render_label_pdf(LabelSpec(ref="1295108", product_name="Kit", contents=["1 Each - Towel, Absorbent"]), tmp_path / "sku-001" / "label.pdf")
    run = run_folder(tmp_path, RelationshipStore.default(), Thresholds())
    assert run.metadata.ai_provider == {"provider": "null", "model": None, "status": "disabled (no external calls)"}
    assert run.metadata.capabilities["Optional AI adjudication (L5)"].startswith("DISABLED")
