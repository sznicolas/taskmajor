# ============================================================================
# STAGE 1: Build TaskWarrior
# ============================================================================
FROM debian:bookworm-slim AS taskbuilder

# WORKDIR /tmp
WORKDIR /root/code/
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
            build-essential \
            cmake \
            curl \
            git \
            libgnutls28-dev \
            uuid-dev

# Setup language environment
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8

# Add source directory
# ADD .. /root/code/

# Setup Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > rustup.sh && \
    sh rustup.sh -y --profile minimal --default-toolchain stable --component rust-docs &&\
    git clone https://github.com/GothenburgBitFactory/taskwarrior.git &&\
    cd taskwarrior && \
    git clean -dfx && \
    git submodule init && \
    git submodule update && \
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build -j 8 && \
    rm -rf /root/.cargo /root/.rustup /tmp/taskwarrior/.git

# ============================================================================
# STAGE 2: Build Python dependencies
# ============================================================================

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS appbuilder
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
RUN uv sync --no-install-project && uv python install 3.12


# ============================================================================
# STAGE 3: Runtime
# ============================================================================
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system --gid 1001 tmajor && \
    useradd --system --gid 1001 --uid 1001 --create-home tmajor && \
    mkdir /data ; chown tmajor /data

USER tmajor
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=appbuilder /python /python

COPY --from=taskbuilder /root/code/taskwarrior/build/src/task /usr/local/bin/task
COPY --from=appbuilder --chown=tmajor:tmajor /app/.venv /app/.venv
COPY --from=appbuilder --chown=tmajor:tmajor /app/taskmajor /app/taskmajor
#COPY --from=appbuilder --chown=tmajor:tmajor /app/app/config /app/config

CMD ["python", "-m", "taskmajor.bootstrap.server"]
