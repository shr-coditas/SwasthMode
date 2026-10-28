"""Provider errors for operator logs: kept as raised, with secrets masked and length capped."""
import re

# API keys (sk-/pk-/rk-...), bearer values and JWTs. Providers usually mask keys already.
SECRET = re.compile(r"\b(?:sk|pk|rk)[-_][\w*-]{8,}|Bearer\s+\S+|\beyJ[\w-]+\.[\w-]+\.[\w-]+", re.IGNORECASE)


def describe(error: BaseException) -> str:
    text = SECRET.sub("<redacted>", str(error)).replace("\n", " ")
    return f"{type(error).__module__}.{type(error).__name__}: {text[:600]}"
