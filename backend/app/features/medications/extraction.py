import json

from app.ai.client import structured
from app.features.medications.prompts import EXTRACTION
from app.features.medications.schemas import MedicationExtraction


async def extract(text: str) -> MedicationExtraction:
    return await structured(EXTRACTION, json.dumps({"current_report": text}), MedicationExtraction)
