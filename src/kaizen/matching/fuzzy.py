"""Token similarity with a numeric guard. Produces POTENTIAL matches only — never certainty."""

from dataclasses import dataclass

from rapidfuzz import fuzz

from kaizen.matching.normalize import NormalizedText

STOPWORDS = {"THE", "OF", "AND", "A", "AN", "FOR", "WITH", "PER"}


@dataclass(frozen=True)
class FuzzyScore:
    score: float
    numeric_conflict: bool
    method: str
    detail: str


def content_tokens(n: NormalizedText) -> list[str]:
    return [t for t in n.tokens if t not in STOPWORDS]


def similarity(a: NormalizedText, b: NormalizedText) -> FuzzyScore:
    ta, tb = content_tokens(a), content_tokens(b)
    if not ta or not tb:
        return FuzzyScore(0.0, False, "empty", "one side has no content tokens")
    sa, sb = " ".join(ta), " ".join(tb)
    sort = fuzz.token_sort_ratio(sa, sb) / 100
    tset = fuzz.token_set_ratio(sa, sb) / 100
    if min(len(ta), len(tb)) >= 2:
        score, method = tset, "token_set_ratio"
    else:
        score, method = sort, "token_sort_ratio"  # a single generic token must not match on subset alone
    # numbers conflict unless one side's numbers are all present on the other (terse BOM ⊂ verbose label is
    # fine; '22G x 1.5in' vs '22G x 1in' is not)
    conflict = bool(a.numbers and b.numbers and not (a.numbers <= b.numbers or b.numbers <= a.numbers))
    detail = f"{method}={score:.2f} (token_sort={sort:.2f}, token_set={tset:.2f})"
    if conflict:
        detail += f"; numeric tokens disagree: {sorted(set(a.numeric_tokens))} vs {sorted(set(b.numeric_tokens))}"
    return FuzzyScore(round(score, 4), conflict, method, detail)
