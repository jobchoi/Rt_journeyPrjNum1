"""Shared pytest setup with an isolated SQLite database and upload directory."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB = Path("database/pytest_mvp.db")
TEST_UPLOADS = Path("storage/pytest-uploads")
TEST_DB.unlink(missing_ok=True)
TEST_UPLOADS.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["UPLOAD_DIR"] = str(TEST_UPLOADS)
os.environ["ALLOW_ROLE_REGISTRATION"] = "true"
os.environ["JWT_SECRET_KEY"] = "pytest-secret"

from src.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    TEST_DB.unlink(missing_ok=True)
    for path in TEST_UPLOADS.glob("*"):
        path.unlink()
    TEST_UPLOADS.rmdir()
