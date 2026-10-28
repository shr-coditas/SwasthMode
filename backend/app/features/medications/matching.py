from difflib import SequenceMatcher
import re

from app.features.medications.schemas import PrescriptionView


def normalized(value: str) -> str:
    return re.sub(r"\s+", "", value.casefold())


def match(name: str, prescriptions: list[PrescriptionView]) -> tuple[PrescriptionView | None, bool]:
    exact = [item for item in prescriptions if normalized(item.name) == normalized(name)]
    if len(exact) == 1:
        return exact[0], False
    if exact:
        return None, True
    candidates = [item for item in prescriptions
                  if SequenceMatcher(None, normalized(name), normalized(item.name)).ratio() >= .7]
    return (candidates[0], True) if len(candidates) == 1 else (None, True)
