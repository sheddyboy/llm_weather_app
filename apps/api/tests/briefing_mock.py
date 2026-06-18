"""A fake structured chat runnable for the briefing service tests.

The briefing service builds ``ChatOpenAI(...).with_structured_output(...)`` and
calls ``ainvoke`` on it, expecting a :class:`BriefingResponse` back. These fakes
stand in for that runnable so tests never hit OpenAI: :class:`FakeBriefingLLM`
returns a canned briefing and counts its calls (so cache hits can be asserted),
and :class:`FailingBriefingLLM` raises to exercise the error path.
"""

from app.schemas.briefing import BriefingResponse


class FakeBriefingLLM:
    """Returns a canned ``BriefingResponse`` and records how often it's invoked."""

    def __init__(self, response: BriefingResponse | None = None) -> None:
        self.response = response or BriefingResponse(
            summary="Mild with sunny spells across the range.",
            clothing_suggestion="A light jacket should be plenty.",
            aqi_note="Air quality is good (AQI 1).",
        )
        self.calls: list[object] = []

    async def ainvoke(self, messages, **kwargs) -> BriefingResponse:
        self.calls.append(messages)
        return self.response


class FailingBriefingLLM:
    """Raises on invoke to simulate the OpenAI call failing."""

    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages, **kwargs) -> BriefingResponse:
        self.calls += 1
        raise RuntimeError("simulated OpenAI failure")
