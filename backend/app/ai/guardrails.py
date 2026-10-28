import re
from fastapi import HTTPException


def check_input(text: str, *, feature: str = "meals") -> str | None:
    if not text.strip() or any(ord(c) < 32 and c not in "\n\t\r" for c in text):
        raise HTTPException(422, "Please send readable text")
    lowered = text.casefold()
    subject = "meal or medication event" if feature == "health_logs" else "medication event" if feature == "medications" else "meal"
    if re.search(r"\b(ignore (all |previous )?instructions|system prompt|execute sql|drop table)\b", lowered):
        return f"Please describe your {subject}. I can only help record reports in this view."
    prescribing = r"prescrib\w*" if feature == "meals" else r"prescrib(?:e|ing)\w*"
    if re.search(r"\b(diagnos\w*|" + prescribing + r"|change (my |the )?dose|double (my |the )?dose|should i (take|stop|skip))\b", lowered):
        return f"I can help record a {subject}, but I cannot diagnose conditions or advise on medication doses."
    return None


def check_output(text: str, *, qualitative: bool = False) -> bool:
    """Our deterministic output rules; these remain independent of NeMo."""
    if re.search(r"\b(you should|you must|please)\s+(take|skip|double|halve|increase|stop)\b", text, re.I):
        return False
    if qualitative and re.search(
        r"\d|\b(calories|kcal|grams|milligrams|macros|balanced|adequate|cure|diagnos\w*|dose|diabet\w*)\b",
        text, re.I,
    ):
        return False
    return True
