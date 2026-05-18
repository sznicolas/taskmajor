# ============================================================================
# STAGE 1: Builder
# ============================================================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

WORKDIR /build
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
RUN uv sync --no-install-project && uv python install 3.12
# Nettoyer le venv : supprimer __pycache__, .pyc, et les .dist-info inutiles
RUN find /build/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
    find /build/.venv -type f -name '*.pyc' -delete 2>/dev/null; \
    find /build/.venv -type f -name '*.pyo' -delete 2>/dev/null; \
    rm -rf /build/.venv/lib/python3.12/site-packages/*/tests 2>/dev/null; \
    rm -rf /build/.venv/lib/python3.12/site-packages/*/.github 2>/dev/null

# ============================================================================
# STAGE 2: Runtime
# ============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 1001 taskmajor && \
    useradd --system --gid 1001 --uid 1001 --create-home taskmajor && \
    mkdir /data && chown taskmajor /data

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"
COPY --from=builder /python /python
COPY --from=builder --chown=taskmajor:taskmajor /build/.venv /app/.venv
COPY --from=builder --chown=taskmajor:taskmajor /build/taskmajor /app/taskmajor

USER taskmajor

ENV PATH="/app/.venv/bin:$PATH"
ENV TASKMAJOR_DATA_DIR="/data"

CMD ["python", "-m", "taskmajor.bootstrap.server"]
