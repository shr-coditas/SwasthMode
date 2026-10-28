FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml .python-version ./
# Generate a real lockfile with uv lock before adopting --locked builds.
# compose.debug.yaml sets UV_SYNC_EXTRA="--group debug" to add debugpy.
ARG UV_SYNC_EXTRA=""
RUN uv sync --no-dev $UV_SYNC_EXTRA
COPY . .
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
