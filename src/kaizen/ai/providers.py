"""Optional AI adjudication providers. The engine is complete without them (NullProvider, the default).

An AI output is always a labelled SUGGESTION with provider, model, prompt version, timestamp and rationale — it
never changes a classification, a reviewer decision or a relationship on its own."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

PROMPT_VERSION = "adjudicate-v1"
_PROMPT = (
    "You compare two component descriptions from medical-device engineering documents (a BOM line and a label "
    "line, drawing callout or PCO row). Answer with JSON only: {{\"verdict\": \"SAME_ITEM\" | \"DIFFERENT_ITEM\" | "
    "\"UNSURE\", \"confidence\": 0.0-1.0, \"rationale\": \"one sentence\"}}.\nA: {a}\nB: {b}\nContext: {ctx}"
)


@dataclass(frozen=True)
class Suggestion:
    label: str
    verdict: str  # SAME_ITEM | DIFFERENT_ITEM | UNSURE
    confidence: float
    rationale: str
    provider: str
    model: str | None
    prompt_version: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AdjudicationProvider(Protocol):
    name: str

    def adjudicate(self, a: str, b: str, context: dict[str, Any]) -> Suggestion | None: ...

    def describe(self) -> dict[str, Any]: ...


class NullProvider:
    name = "null"

    def __init__(self, reason: str = "AI adjudication disabled by default"):
        self.reason = reason

    def adjudicate(self, a: str, b: str, context: dict[str, Any]) -> Suggestion | None:
        return None

    def describe(self) -> dict[str, Any]:
        return {"provider": "null", "model": None, "status": "disabled (no external calls)"}


class AnthropicProvider:
    """Uses the Anthropic Messages API when explicitly enabled (KAIZEN_AI_PROVIDER=anthropic and ANTHROPIC_API_KEY).
    Only the two descriptions and minimal context are sent — never whole documents."""

    name = "anthropic"

    def __init__(self, client: Any = None, model: str | None = None):
        self.model = model or os.environ.get("KAIZEN_AI_MODEL", "claude-sonnet-5")
        if client is None:
            import anthropic  # optional dependency

            client = anthropic.Anthropic()
        self.client = client
        self.calls = 0

    def adjudicate(self, a: str, b: str, context: dict[str, Any]) -> Suggestion | None:
        prompt = _PROMPT.format(a=a, b=b, ctx=json.dumps({k: v for k, v in context.items() if k in ("sku", "check", "item_number")}))
        msg = self.client.messages.create(model=self.model, max_tokens=200, messages=[{"role": "user", "content": prompt}])
        self.calls += 1
        text = "".join(getattr(block, "text", "") for block in msg.content)
        try:
            data = json.loads(text[text.index("{") : text.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            data = {"verdict": "UNSURE", "confidence": 0.0, "rationale": f"unparseable model output: {text[:120]}"}
        verdict = str(data.get("verdict", "UNSURE")).upper()
        if verdict not in ("SAME_ITEM", "DIFFERENT_ITEM", "UNSURE"):
            verdict = "UNSURE"
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        return Suggestion("AI SUGGESTION", verdict, confidence, str(data.get("rationale", "")), self.name, getattr(msg, "model", self.model), PROMPT_VERSION, datetime.now(timezone.utc).isoformat(timespec="seconds"))

    def describe(self) -> dict[str, Any]:
        return {"provider": "anthropic", "model": self.model, "status": "enabled (explicit opt-in; sends only description pairs)", "prompt_version": PROMPT_VERSION}


def get_provider() -> AdjudicationProvider:
    """Provider selection is explicit and fails closed: anything unset or misconfigured is the NullProvider."""
    choice = (os.environ.get("KAIZEN_AI_PROVIDER") or "null").lower()
    if choice == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return NullProvider("KAIZEN_AI_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set; AI disabled")
        try:
            return AnthropicProvider()
        except Exception as e:  # missing optional dependency, etc.
            return NullProvider(f"anthropic provider unavailable ({e}); AI disabled")
    if choice == "azure-openai":
        return NullProvider("azure-openai provider is PLANNED (not implemented); AI disabled")
    return NullProvider()
