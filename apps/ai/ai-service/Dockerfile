
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY apps/ai/ai-service/pyproject.toml \
    apps/ai/ai-service/uv.lock \
    apps/ai/ai-service/README.md ./

COPY apps/ai/ai-service/src ./src

RUN uv sync --frozen --no-dev --no-editable

ENV PROMPT_INJECTION_MODEL=/opt/models/prompt-injection-guard-small

ARG PROMPT_INJECTION_MODEL_ID=Horizon-Labs/prompt-injection-guard-small

RUN python -c "from huggingface_hub import HfApi, snapshot_download; model = HfApi().model_info('${PROMPT_INJECTION_MODEL_ID}'); print(f'Downloading model revision: {model.sha}'); snapshot_download(repo_id='${PROMPT_INJECTION_MODEL_ID}', revision=model.sha, local_dir='/opt/models/prompt-injection-guard-small')" \
    && chmod -R a+rX /opt/models

RUN python -m spacy download en_core_web_sm \
    && python -m spacy download fr_core_news_md

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

RUN groupadd --system app \
    && useradd --system --gid app --create-home app

USER app

EXPOSE 8002

CMD ["python", "-m", "ai_service.main"]
