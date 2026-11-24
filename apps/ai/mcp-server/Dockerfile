FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY apps/ai/mcp-server/pyproject.toml apps/ai/mcp-server/uv.lock apps/ai/mcp-server/README.md  ./
COPY apps/ai/mcp-server/src ./src

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PAPTH"

EXPOSE 8001

CMD ["mcp-server"]

