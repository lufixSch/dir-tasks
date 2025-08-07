FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable --link-mode "copy"


FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

# Copy the project into the image
COPY main.py /app/main.py

CMD ["/app/.venv/bin/python", "-u", "main.py", "/tasks_dir"]
