FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime code and runtime Skill assets are both required.
COPY app ./app
COPY skills ./skills

# Keep migrations in the image so deployment jobs can run `alembic upgrade head`.
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

COPY run.py mcp_server.py ./

RUN mkdir -p /app/data
EXPOSE 8000 8011

CMD ["python", "run.py"]
