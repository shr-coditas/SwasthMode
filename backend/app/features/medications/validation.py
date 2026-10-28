from datetime import UTC, datetime
import re
from zoneinfo import ZoneInfo

from app.features.medications.schemas import MedicationExtraction


class Clarification(ValueError):
    pass


def local_time(value: str, timezone: str, reported_at: datetime) -> datetime:
    if value.casefold() == "now":
        return reported_at
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", value):
        raise Clarification("Use 'now' or a local time written YYYY-MM-DD HH:MM.")
    try:
        local = datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        raise Clarification("That calendar date or clock time is invalid. Send a new report.") from None
    zone = ZoneInfo(timezone)
    first = local.replace(tzinfo=zone, fold=0)
    second = local.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset() or first.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local:
        raise Clarification("That local time is ambiguous or unavailable because of a clock change. Report an unambiguous time.")
    instant = first.astimezone(UTC)
    if instant > reported_at:
        raise Clarification("A recorded event needs a time that has already occurred. Send a new report.")
    return instant


def validate_report(extraction: MedicationExtraction, text: str, timezone: str,
                    reported_at: datetime) -> datetime:
    help_text = ("Send one complete report, for example: I took [medicine name] [reported strength, if known] "
                 "now; or end with at YYYY-MM-DD HH:MM in your local timezone. Include only what you reported taking.")
    if extraction.intent != "record" or not extraction.name or not extraction.time_text:
        raise Clarification(help_text)
    report = text.strip()
    if extraction.taken_evidence != report:
        raise Clarification("The extracted evidence did not cover your full report. " + help_text)
    statement = re.fullmatch(r"I (?:took|have taken) (.+?) (?:at )?(now|\d{4}-\d{2}-\d{2} \d{2}:\d{2})[.!]?", report, re.I)
    if not statement or re.search(r"\b(no|not|never|without|didn't|haven't|did not|might|maybe|if|unless|and|or|but|instead)\b", report, re.I):
        raise Clarification(help_text)
    for field in (extraction.name, extraction.strength, extraction.quantity, extraction.frequency, extraction.time_text):
        if field and (field.evidence not in report or field.value not in field.evidence):
            raise Clarification("A reported field could not be traced to your words. " + help_text)
    if extraction.time_text.value != statement[2]:
        raise Clarification("The extracted time did not match your report. " + help_text)
    if extraction.strength and not re.fullmatch(
        r"\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu|units|%)", extraction.strength.value, re.I
    ):
        raise Clarification("The reported strength needs an explicit number and unit. " + help_text)
    if extraction.quantity and not re.fullmatch(
        r"\d+(?:\.\d+)?\s*(?:tablets?|capsules?|puffs?|drops?|ml|units?)", extraction.quantity.value, re.I
    ):
        raise Clarification("The reported quantity needs an explicit number and unit. " + help_text)
    if extraction.frequency and not re.fullmatch(
        r"(?:(?:once|twice|\d+ times) (?:daily|weekly)|(?:once|twice|\d+ times) (?:a|per) (?:day|week))",
        extraction.frequency.value, re.I,
    ):
        raise Clarification("That reported frequency is outside this slice's supported wording. Omit it if you did not mean to report frequency, or send a new complete report.")
    remaining = statement[1]
    fields = [field for field in (extraction.name, extraction.strength, extraction.quantity, extraction.frequency) if field]
    for field in sorted(fields, key=lambda item: len(item.value), reverse=True):
        if field.value not in remaining:
            raise Clarification("The reported fields overlap or cannot be traced separately. " + help_text)
        remaining = remaining.replace(field.value, "", 1)
    if remaining.strip():
        raise Clarification("Some words in the report were not captured as reported fields. " + help_text)
    return local_time(extraction.time_text.value, timezone, reported_at)
