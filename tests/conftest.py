import os

# Must be set before the app is imported.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256-0123456789"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:   # runs lifespan: creates tables + seeds
        yield c


@pytest.fixture()
def auth(client):
    """Registers a fresh user; returns (headers, user)."""
    import uuid
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/auth/register", json={"full_name": "Test User", "email": email, "password": "supersecret1"})
    assert r.status_code == 201, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]
