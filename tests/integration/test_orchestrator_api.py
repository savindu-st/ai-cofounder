"""Integration Tests for Orchestrator REST Endpoints.

Tests:
- POST /api/ventures/start
- GET /api/ventures/{venture_id}
- POST /api/ventures/{venture_id}/review
- GET /health
"""

from fastapi.testclient import TestClient
from services.orchestrator.app.main import app
from shared.db.session import get_db

# Dummy mock db session generator for testing without running postgres
async def override_get_db():
    class DummyDB:
        async def execute(self, query):
            class ScalarResult:
                def scalar(self):
                    return 1
            return ScalarResult()
    yield DummyDB()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_endpoint():
    """Validates the orchestrator health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orchestrator"


def test_start_and_get_venture_lifecycle():
    """Validates venture creation, pipeline triggering, and state hydration endpoints."""
    payload = {
        "startup_idea": "Autonomous AI platform for customer feedback analysis",
        "target_market": "Product Managers in B2B SaaS",
        "target_geography": "Global",
        "budget": 20000.0,
        "timeline_months": 4,
        "goals": "Achieve $10k MRR",
        "constraints": []
    }

    # 1. Start pipeline
    start_resp = client.post("/api/ventures/start", json=payload)
    assert start_resp.status_code == 201
    start_data = start_resp.json()
    assert "venture_id" in start_data
    venture_id = start_data["venture_id"]
    assert start_data["status"] == "INITIALIZED"

    # 2. Get state hydration
    get_resp = client.get(f"/api/ventures/{venture_id}")
    assert get_resp.status_code == 200
    state_data = get_resp.json()
    assert state_data["venture_id"] == venture_id
    assert state_data["founder_input"]["startup_idea"] == payload["startup_idea"]

    # 3. Test 404 for unknown venture
    not_found_resp = client.get("/api/ventures/non-existent-venture-xyz")
    assert not_found_resp.status_code == 404


def test_submit_human_review_endpoint():
    """Validates human review resume API behavior."""
    payload = {
        "startup_idea": "AI copilot for legal compliance documentation",
        "target_market": "Legal Tech",
        "target_geography": "US",
        "budget": 10000.0,
        "timeline_months": 3,
        "goals": "Generate prototype",
        "constraints": []
    }

    start_resp = client.post("/api/ventures/start", json=payload)
    venture_id = start_resp.json()["venture_id"]

    # Submit review approval
    review_payload = {
        "action": "PROCEED_ANYWAY",
        "notes": "Approved past initial risk warning."
    }
    review_resp = client.post(f"/api/ventures/{venture_id}/review", json=review_payload)
    assert review_resp.status_code == 200
    review_data = review_resp.json()
    assert review_data["action_taken"] == "PROCEED_ANYWAY"
    assert review_data["status"] == "RESUMED"
