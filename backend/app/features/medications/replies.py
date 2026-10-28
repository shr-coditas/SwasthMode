from zoneinfo import ZoneInfo

from app.features.medications.schemas import EventView, Proposal


EXPIRED = "That medication confirmation expired. No event was saved from this reply. Please send a new complete report."
STALE = "That question is no longer current. This reply cannot confirm another medication or question. Please send a new complete report."


def readback(proposal: Proposal) -> str:
    clock = proposal.occurred_at.astimezone(ZoneInfo(proposal.timezone)).strftime("%Y-%m-%d %H:%M %Z")
    if proposal.operation == "correct_time":
        return (f"Correct only the recorded time for event {proposal.event_id}, "
                f"{proposal.prescription.name}, to {clock}? Medicine details and prescription stay unchanged.")
    report = proposal.reported
    fields = [f"medicine: {report.name.value}"]
    for label in ("strength", "quantity", "frequency"):
        field = getattr(report, label)
        fields.append(f"{label}: {field.value if field else 'not reported'}")
    prescription = proposal.prescription
    match_text = "Possible prescription match" if proposal.uncertain_match else "Prescription match"
    return (f"You reported {', '.join(fields)}, at {clock}. "
            f"{match_text}: {prescription.name}, {prescription.strength}, {prescription.frequency}. "
            "These prescription fields are reference information, not your reported dose. "
            "Confirm this exact readback to record the event, or cancel and send a new report.")


def saved_reply(event: EventView, corrected: bool) -> str:
    clock = event.occurred_at.astimezone(ZoneInfo(event.timezone)).strftime("%Y-%m-%d %H:%M %Z")
    return (f"Corrected the recorded event time for {event.prescription_snapshot.name} to {clock}."
            if corrected else f"Recorded your reported medication event for {event.prescription_snapshot.name} at {clock}.")
