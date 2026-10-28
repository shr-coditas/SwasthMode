import logging
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.core.config import settings
from app.features.account.router import router as account_router
from app.features.clinician.router import router as clinician_router
from app.features.briefs.router import router as briefs_router
from app.features.meals.router import router as meals_router
from app.features.medications.router import router as medications_router
from app.features.health_logs.router import router as health_logs_router
from app.speech.router import router as speech_router

logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
# SDK HTTP logs can include request URLs; keep provider libraries quiet by default.
for name in ("httpx", "httpcore", "openai", "cartesia", "sqlalchemy.engine"):
    logging.getLogger(name).setLevel(logging.WARNING)

app = FastAPI(title="SwasthMode", version="0.1.0", description="Synthetic-data wellness POC. Meals, medication events and daily briefs.")
app.add_middleware(CORSMiddleware, allow_origins=[settings().frontend_origin],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"], expose_headers=["X-Request-ID"])


@app.middleware("http")
async def private_responses(request: Request, call_next):
    request_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError):
    # Do not echo raw conversation text or token input back in validation traces.
    return JSONResponse(status_code=422, content={"detail": "Invalid request fields or size"})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    status = 409 if isinstance(error, IntegrityError) else 503
    return JSONResponse(status_code=status, content={"detail":
        "A concurrent request conflicted. Reload before retrying" if status == 409 else
        "Database operation failed. Retry the same request ID; no success is being claimed"})


@app.get("/health", tags=["system"])
def health():
    return {"application": "SwasthMode", "status": "process_running", "dependencies_checked": False}


app.include_router(account_router)
app.include_router(clinician_router)
app.include_router(meals_router)
app.include_router(medications_router)
app.include_router(briefs_router)
app.include_router(health_logs_router)
app.include_router(speech_router)
