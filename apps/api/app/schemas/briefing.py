"""Response schema for the LLM briefing endpoint (`/records/{id}/briefing`).

This is the structured shape the OpenAI call is constrained to via LangChain's
``with_structured_output`` (ARCHITECTURE §6): the model fills these fields rather
than returning free-form prose, so the response is a stable contract. The field
descriptions double as the model's instructions for what each field should hold.
"""

from pydantic import BaseModel, Field


class BriefingResponse(BaseModel):
    """A short, human-friendly briefing generated from a record's weather data."""

    summary: str = Field(
        description=(
            "A concise narrative summary of the weather over the record's date "
            "range for the location: overall trend, notable highs/lows, and "
            "conditions. Two or three sentences."
        )
    )
    clothing_suggestion: str = Field(
        description=(
            "A practical clothing/packing suggestion appropriate for the "
            "temperatures and conditions across the range. One or two sentences."
        )
    )
    aqi_note: str = Field(
        description=(
            "A brief note on air quality based on the readings' AQI values "
            "(1=good to 5=very poor); say if air quality data is unavailable."
        )
    )
