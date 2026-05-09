FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies separately to leverage Docker cache
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Final image
FROM python:3.12-slim

WORKDIR /app

# Copy the virtualenv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Set the path to use the virtualenv
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application code
COPY . .

# Expose the port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["fastapi", "run", "app/main.py", "--port", "8000", "--host", "0.0.0.0"]
