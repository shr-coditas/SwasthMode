from app.ai.client import structured
from app.features.briefs.prompts import PROMPT
from app.features.briefs.schemas import BriefContext, Narrative


async def generate(context: BriefContext) -> Narrative:
    return await structured(PROMPT, context.model_dump_json(), Narrative)
