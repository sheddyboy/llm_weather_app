"""Render a stored weather record to json, xml, csv, or markdown.

The exporter operates on the API's :class:`~app.schemas.WeatherRecordRead`
schema rather than the ORM model, so every format mirrors the same shape clients
already see elsewhere in the API and the service stays decoupled from
persistence. All non-JSON formats are built from ``model_dump(mode="json")`` so
they share one consistently serialized view of the record (ISO dates, stringified
decimals). PDF is intentionally out of scope here; it is added in batch 12.
"""

import csv
import io
from enum import StrEnum
from xml.etree import ElementTree as ET

from app.schemas import WeatherRecordRead


class ExportFormat(StrEnum):
    """Supported export formats (PDF lands in batch 12)."""

    JSON = "json"
    XML = "xml"
    CSV = "csv"
    MARKDOWN = "markdown"


# Per-format (media type, download filename extension).
_FORMAT_META: dict[ExportFormat, tuple[str, str]] = {
    ExportFormat.JSON: ("application/json", "json"),
    ExportFormat.XML: ("application/xml", "xml"),
    ExportFormat.CSV: ("text/csv", "csv"),
    ExportFormat.MARKDOWN: ("text/markdown", "md"),
}

# A flat, self-describing CSV: each daily reading carries the record/location
# context so a single row stands alone without a separate header block.
_CSV_COLUMNS = [
    "record_id",
    "location",
    "latitude",
    "longitude",
    "start_date",
    "end_date",
    "date",
    "temp_min",
    "temp_max",
    "conditions",
    "aqi",
]


def render(record: WeatherRecordRead, fmt: ExportFormat) -> tuple[str, str, str]:
    """Render ``record`` in ``fmt``; return ``(content, media_type, extension)``."""
    content = _RENDERERS[fmt](record)
    media_type, extension = _FORMAT_META[fmt]
    return content, media_type, extension


def _to_json(record: WeatherRecordRead) -> str:
    """Canonical, indented JSON straight from the schema."""
    return record.model_dump_json(indent=2)


def _to_csv(record: WeatherRecordRead) -> str:
    """One row per daily reading, each carrying its record/location context."""
    data = record.model_dump(mode="json")
    location = data["location"]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_CSV_COLUMNS)
    for reading in data["readings"]:
        writer.writerow(
            [
                data["id"],
                location["resolved_name"],
                location["latitude"],
                location["longitude"],
                data["start_date"],
                data["end_date"],
                reading["date"],
                reading["temp_min"],
                reading["temp_max"],
                reading["conditions"],
                "" if reading["aqi"] is None else reading["aqi"],
            ]
        )
    return buffer.getvalue()


def _to_xml(record: WeatherRecordRead) -> str:
    """A ``<record>`` tree with nested ``<location>`` and ``<readings>``."""
    data = record.model_dump(mode="json")
    root = ET.Element("record", id=data["id"])
    for key in ("start_date", "end_date", "created_at", "updated_at"):
        ET.SubElement(root, key).text = data[key]

    location = data["location"]
    loc_el = ET.SubElement(root, "location", id=location["id"])
    for key in (
        "query_text",
        "resolved_name",
        "latitude",
        "longitude",
        "country",
        "created_at",
    ):
        value = location[key]
        if value is not None:
            ET.SubElement(loc_el, key).text = str(value)

    readings_el = ET.SubElement(root, "readings")
    for reading in data["readings"]:
        r_el = ET.SubElement(readings_el, "reading", id=reading["id"])
        for key in ("date", "temp_min", "temp_max", "conditions", "aqi"):
            value = reading[key]
            if value is not None:
                ET.SubElement(r_el, key).text = str(value)

    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _to_markdown(record: WeatherRecordRead) -> str:
    """A titled summary plus a markdown table of the daily readings."""
    data = record.model_dump(mode="json")
    location = data["location"]
    lines = [
        f"# Weather Record: {location['resolved_name']}",
        "",
        f"- **Record ID:** {data['id']}",
        f"- **Location query:** {location['query_text']}",
        f"- **Coordinates:** {location['latitude']}, {location['longitude']}",
        f"- **Date range:** {data['start_date']} to {data['end_date']}",
        "",
        "## Daily readings",
        "",
        "| Date | Min (°C) | Max (°C) | Conditions | AQI |",
        "| --- | --- | --- | --- | --- |",
    ]
    for reading in data["readings"]:
        aqi = "" if reading["aqi"] is None else reading["aqi"]
        lines.append(
            f"| {reading['date']} | {reading['temp_min']} | {reading['temp_max']} "
            f"| {reading['conditions']} | {aqi} |"
        )
    if not data["readings"]:
        lines.append("| _No readings_ | | | | |")
    return "\n".join(lines) + "\n"


_RENDERERS = {
    ExportFormat.JSON: _to_json,
    ExportFormat.XML: _to_xml,
    ExportFormat.CSV: _to_csv,
    ExportFormat.MARKDOWN: _to_markdown,
}
