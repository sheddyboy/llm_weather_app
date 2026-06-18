"""Render a stored weather record to json, xml, csv, markdown, or pdf.

The exporter operates on the API's :class:`~app.schemas.WeatherRecordRead`
schema rather than the ORM model, so every format mirrors the same shape clients
already see elsewhere in the API and the service stays decoupled from
persistence. All non-JSON formats are built from ``model_dump(mode="json")`` so
they share one consistently serialized view of the record (ISO dates, stringified
decimals). PDF is the one binary format, so :func:`render` returns ``str | bytes``
and the PDF renderer hands back the document bytes.
"""

import csv
import io
from enum import StrEnum
from xml.etree import ElementTree as ET

from fpdf import FPDF

from app.schemas import WeatherRecordRead


class ExportFormat(StrEnum):
    """Supported export formats."""

    JSON = "json"
    XML = "xml"
    CSV = "csv"
    MARKDOWN = "markdown"
    PDF = "pdf"


# Per-format (media type, download filename extension).
_FORMAT_META: dict[ExportFormat, tuple[str, str]] = {
    ExportFormat.JSON: ("application/json", "json"),
    ExportFormat.XML: ("application/xml", "xml"),
    ExportFormat.CSV: ("text/csv", "csv"),
    ExportFormat.MARKDOWN: ("text/markdown", "md"),
    ExportFormat.PDF: ("application/pdf", "pdf"),
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


def render(
    record: WeatherRecordRead, fmt: ExportFormat
) -> tuple[str | bytes, str, str]:
    """Render ``record`` in ``fmt``; return ``(content, media_type, extension)``.

    ``content`` is text for every format except PDF, which returns bytes; both are
    accepted directly by :class:`fastapi.Response`.
    """
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


# PDF table layout: (header, reading key, column width in mm). Widths sum to the
# usable page width (A4 portrait minus default margins = 190mm).
_PDF_COLUMNS = [
    ("Date", "date", 40.0),
    ("Min (C)", "temp_min", 30.0),
    ("Max (C)", "temp_max", 30.0),
    ("Conditions", "conditions", 60.0),
    ("AQI", "aqi", 30.0),
]


def _to_pdf(record: WeatherRecordRead) -> bytes:
    """A printable one-page summary: heading, record metadata, readings table.

    Uses the built-in Helvetica core font (latin-1), which covers the degree sign
    used in the temperature columns, so no font files need shipping in the image.
    """
    data = record.model_dump(mode="json")
    location = data["location"]

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"Weather Record: {location['resolved_name']}", new_x="LMARGIN",
             new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    for label, value in (
        ("Record ID", data["id"]),
        ("Location query", location["query_text"]),
        ("Coordinates", f"{location['latitude']}, {location['longitude']}"),
        ("Date range", f"{data['start_date']} to {data['end_date']}"),
    ):
        pdf.cell(0, 7, f"{label}: {value}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Daily readings", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    for header, _key, width in _PDF_COLUMNS:
        pdf.cell(width, 8, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    if not data["readings"]:
        total_width = sum(width for _h, _k, width in _PDF_COLUMNS)
        pdf.cell(total_width, 8, "No readings", border=1, align="C")
        pdf.ln()
    for reading in data["readings"]:
        for _header, key, width in _PDF_COLUMNS:
            value = reading[key]
            text = "" if value is None else str(value)
            pdf.cell(width, 8, text, border=1)
        pdf.ln()

    return bytes(pdf.output())


_RENDERERS = {
    ExportFormat.JSON: _to_json,
    ExportFormat.XML: _to_xml,
    ExportFormat.CSV: _to_csv,
    ExportFormat.MARKDOWN: _to_markdown,
    ExportFormat.PDF: _to_pdf,
}
