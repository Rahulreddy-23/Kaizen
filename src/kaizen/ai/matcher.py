"""L5: AI adjudication as a ladder matcher. Runs only after every deterministic level failed, and only ever
returns a WEAK (non-assignable) outcome: the suggestion reaches the reviewer as a note, never as a pairing."""

from kaizen.ai.providers import AdjudicationProvider
from kaizen.matching.ladder import MatchContext, MatchOutcome
from kaizen.matching.normalize import NormalizedText
from kaizen.models import MatchLevel


class AiAdjudicationMatcher:
    name = "L5_ai_suggestion"

    def __init__(self, provider: AdjudicationProvider):
        self.provider = provider
        self.calls = 0

    def try_match(self, a: NormalizedText, b: NormalizedText, ctx: MatchContext) -> MatchOutcome | None:
        s = self.provider.adjudicate(a.raw, b.raw, {"sku": ctx.sku, "item_number": ctx.item_number})
        self.calls += 1
        if s is None or s.verdict != "SAME_ITEM":
            return None
        reason = f'{s.label}: "{a.raw}" ↔ "{b.raw}" — {s.provider}/{s.model} says {s.verdict} (confidence {s.confidence:.2f}): {s.rationale}. Not paired automatically; reviewer decides.'
        return MatchOutcome(MatchLevel.LLM, s.confidence, reason, weak=True)
