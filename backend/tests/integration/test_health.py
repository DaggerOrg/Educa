"""Smoke test for the running FastAPI application and real database setup."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://educa:educa@localhost:55432/educa")
sys.path.insert(0, str(Path(__file__).parents[2]))

from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}