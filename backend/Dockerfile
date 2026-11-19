FROM python:3.12-slim AS os-base

RUN apt-get -o Acquire::Retries=3 update \
    && apt-get -o Acquire::Retries=3 install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

FROM os-base AS parser
COPY requirements-docling.txt /tmp/requirements-docling.txt
RUN python -m venv /opt/docling \
    && /opt/docling/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 torchvision==0.29.1 \
    && /opt/docling/bin/pip install -r /tmp/requirements-docling.txt transformers==4.57.6

FROM os-base AS base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base AS runtime

COPY --from=parser /opt/docling /opt/docling
ENV DOCLING_PYTHON=/opt/docling/bin/python \
    DOCLING_ARTIFACTS_PATH=/app/data/models/docling \
    HF_HOME=/tmp/huggingface

# Runtime code and runtime Skill assets are both required.
COPY app ./app
COPY skills ./skills
COPY scripts ./scripts
COPY demo_knowledge ./demo_knowledge
COPY vendor_knowledge ./vendor_knowledge
COPY eval ./eval

# Keep migrations in the image so deployment jobs can run `alembic upgrade head`.
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

COPY run.py mcp_server.py billing_mcp_server.py pyproject.toml ./

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
