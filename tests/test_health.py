import os
import sys
import pytest

# Ensure the soil-testing-portal directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app


@pytest.fixture
def client():
    """
    Pytest fixture that creates a Flask test client with testing mode enabled.
    """
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_health_check_success(client):
    """
    Test that GET /api/health returns HTTP 200 and a JSON response
    indicating the backend server is running.
    """
    response = client.get("/api/health")

    # Verify HTTP status code
    assert response.status_code == 200

    # Verify JSON response body
    data = response.get_json()
    assert data is not None
    assert data.get("status") == "healthy"
    assert "running" in data.get("message", "").lower()


def test_health_check_method_not_allowed(client):
    """
    Test that POST /api/health returns HTTP 405 Method Not Allowed.
    """
    response = client.post("/api/health")
    assert response.status_code == 405

