import uvicorn
import logging
import subprocess
import sys
from pathlib import Path

from app.core.config import get_settings


def run_database_migrations() -> None:
    """Apply schema migrations once before Uvicorn starts when enabled."""
    settings = get_settings()
    if not settings.database_auto_migrate:
        return
    backend_dir = Path(__file__).resolve().parent
    logging.getLogger(__name__).info("Applying database migrations (alembic upgrade head)")
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(f"Database migration failed with exit code {completed.returncode}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    run_database_migrations()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=settings.app_env == "dev")
