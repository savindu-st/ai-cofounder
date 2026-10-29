"""Integration tests for roadmap document download endpoints."""

import pytest
from fastapi.testclient import TestClient

from services.marketing_output.app.interface import run_roadmap_synthesis
from services.marketing_output.tests.factories import build_sample_state
from services.orchestrator.app.main import app
from services.orchestrator.app.orchestration.coordinator import coordinator
from shared.enums.workflow_status import WorkflowStage

client = TestClient(app)


@pytest.fixture
def completed_export_state():
    state = build_sample_state()
    state.current_stage = WorkflowStage.COMPLETED
    state.final_roadmap = run_roadmap_synthesis(state)
    return state


def _patch_state(monkeypatch, state):
    async def fake_get_state(venture_id):
        return state if venture_id == "ven-export-test" else None

    monkeypatch.setattr(coordinator, "get_state", fake_get_state)


def test_export_endpoints_stream_valid_documents(monkeypatch, completed_export_state):
    _patch_state(monkeypatch, completed_export_state)

    pdf_response = client.get("/api/ventures/ven-export-test/export/pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"].startswith("application/pdf")
    assert "attachment" in pdf_response.headers["content-disposition"]
    assert pdf_response.content.startswith(b"%PDF")

    docx_response = client.get("/api/ventures/ven-export-test/export/docx")
    assert docx_response.status_code == 200
    assert docx_response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert docx_response.content.startswith(b"PK")

    html_response = client.get("/api/ventures/ven-export-test/export/html")
    assert html_response.status_code == 200
    assert html_response.headers["content-type"].startswith("text/html")
    assert "Business Model Canvas" in html_response.text


def test_export_endpoints_return_404_and_409(monkeypatch, completed_export_state):
    _patch_state(monkeypatch, completed_export_state)
    assert client.get("/api/ventures/missing/export/pdf").status_code == 404

    incomplete = completed_export_state.model_copy(deep=True)
    incomplete.final_roadmap = None
    _patch_state(monkeypatch, incomplete)
    response = client.get("/api/ventures/ven-export-test/export/pdf")
    assert response.status_code == 409
