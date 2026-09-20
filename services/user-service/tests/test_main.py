import os
import sys
from unittest.mock import patch

# Ensure app package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

_mock_users = [
    {"id": 1, "name": "Akhil", "email": "akhil@example.com"},
    {"id": 2, "name": "Priya Sharma", "email": "priya@example.com"},
    {"id": 3, "name": "John Doe", "email": "john@example.com"},
]


class _MockCursor:
    def __init__(self):
        self._last_query = ""
        self._args = ()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def execute(self, query, args=()):
        self._last_query = str(query)
        self._args = args
        if "INSERT INTO users" in self._last_query:
            new_id = args[0]
            name = args[1]
            email = args[2]
            _mock_users.append({"id": new_id, "name": name, "email": email})

    def fetchone(self):
        q = self._last_query.strip()
        if "SELECT 1" in q:
            return (1,)
        if "SELECT COUNT" in q:
            return (len(_mock_users),)
        if "SELECT COALESCE(MAX(id)" in q:
            max_id = max([u["id"] for u in _mock_users], default=0)
            return (max_id,)
        if "WHERE id =" in q:
            user_id = self._args[0]
            for u in _mock_users:
                if u["id"] == user_id:
                    return (u["id"], u["name"], u["email"])
            return None
        return None

    def fetchall(self):
        q = self._last_query.strip()
        if "SELECT id, name, email FROM users" in q:
            return [(u["id"], u["name"], u["email"]) for u in _mock_users]
        return []


class _MockConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def cursor(self):
        return _MockCursor()

    def commit(self):
        pass

    def close(self):
        pass


def _get_test_db_connection():
    if os.getenv("TEST_USE_REAL_DB") == "true":
        import psycopg
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://travelhub_user:userpass@localhost:5432/user_db",
        )
        return psycopg.connect(db_url, connect_timeout=2)
    return _MockConnection()


# Apply patch BEFORE initializing TestClient
patch("app.main.get_db_connection", side_effect=_get_test_db_connection).start()

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "user-service"}


def test_ready():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "user-service"}


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "travelhub_service_up 1" in response.text


def test_get_users_collection():
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1


def test_get_user_by_id():
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert "name" in data
    assert "email" in data


def test_get_user_not_found():
    response = client.get("/users/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_create_user():
    payload = {"name": "Test User", "email": "test@example.com"}
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Test User"
    assert created["email"] == "test@example.com"
    assert "id" in created
