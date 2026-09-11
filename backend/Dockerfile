FROM python:3.12-slim AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS runtime

# Runtime code and runtime Skill assets are both required.
COPY app ./app
COPY skills ./skills
COPY scripts ./scripts
COPY demo_knowledge ./demo_knowledge
COPY eval ./eval

# Keep migrations in the image so deployment jobs can run `alembic upgrade head`.
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

COPY run.py mcp_server.py billing_mcp_server.py ./

RUN groupadd --system paismart \
    && useradd --system --gid paismart --home-dir /app --no-create-home paismart \
    && mkdir -p /app/data \
    && chown -R paismart:paismart /app

USER paismart
EXPOSE 8000 8011

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["python", "run.py"]

FROM runtime AS test

USER root
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

COPY --chown=paismart:paismart tests ./tests
USER paismart
CMD ["pytest", "tests"]
