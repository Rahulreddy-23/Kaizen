"""L4 semantic matching: pluggable embedder, POTENTIAL at best, reason names the similarity and the absence of a relationship."""

import math

from kaizen.matching.ladder import MatchLadder
from kaizen.matching.semantic import SemanticMatcher, cosine
from kaizen.models import MatchLevel, Thresholds
from kaizen.terminology.store import RelationshipStore


def fake_embed(texts):
    vocab = {"gauze": 0, "sponge": 1, "pad": 2, "mask": 3, "tape": 4, "measure": 5, "measuring": 6}
    out = []
    for t in texts:
        v = [0.0] * len(vocab)
        for tok in t.lower().replace(",", " ").split():
            if tok in vocab:
                v[vocab[tok]] = 1.0
        if "sponge" in t.lower() or "pad" in t.lower():
            v[0] += 2.0  # sponges/pads are gauze-like
        out.append(v)
    return out


def test_cosine_basic():
    assert math.isclose(cosine([1, 0], [1, 0]), 1.0) and math.isclose(cosine([1, 0], [0, 1]), 0.0)


def test_semantic_matcher_yields_potential_never_equivalent():
    lad = MatchLadder(RelationshipStore.default(), Thresholds(), extra_matchers=[SemanticMatcher(fake_embed, threshold=0.8)])
    out = lad.match("GAUZE SPONGE", "Absorbent Pad")
    assert out.level is MatchLevel.SEMANTIC
    assert 0.8 <= out.score <= 1.0
    assert "semantic similarity" in out.reason.lower() and "no approved terminology relationship" in out.reason.lower()
    assert out.weak is False and out.assignable is True


def test_semantic_below_threshold_is_no_match_and_deterministic_levels_come_first():
    lad = MatchLadder(RelationshipStore.default(), Thresholds(), extra_matchers=[SemanticMatcher(fake_embed, threshold=0.8)])
    assert lad.match("MASK", "Tape Measure").level is MatchLevel.NONE
    assert lad.match("TAPE MEASURE", "Measuring Tape").level is MatchLevel.RELATIONSHIP


def test_semantic_matcher_caches_embeddings():
    calls = []

    def counting(texts):
        calls.append(list(texts))
        return fake_embed(texts)

    m = SemanticMatcher(counting, threshold=0.5)
    lad = MatchLadder(RelationshipStore.default(), Thresholds(), extra_matchers=[m])
    lad.match("GAUZE SPONGE", "Absorbent Pad")
    lad.match("GAUZE SPONGE", "Absorbent Pad")
    assert sum(len(c) for c in calls) == 2
