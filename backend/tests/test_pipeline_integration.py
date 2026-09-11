"""End-to-end pipeline integration tests.

Tests the full task lifecycle via the FastAPI API, demonstrating
two different task types being routed to different models.
This satisfies R3's "shown across at least two task types" requirement.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, registry, adapter_manager, lifecycle_manager

client = TestClient(app)


def _clear():
    """Reset state between tests."""
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in list(registry.list_all()):
        registry.delete(entry.model_id)
    lifecycle_manager._tasks.clear()


def _seed_two_models():
    """Register a reasoning model and a vision model."""
    _clear()
    # Reasoning/coding model
    client.post("/v1/models/", json={
        "model_id": "reasoning-model",
        "name": "Test Reasoning Model",
        "family": "test",
        "capabilities": ["TEXT", "REASONING", "CODING"],
        "context_length": 8192,
        "tool_calling": True,
        "runtime": "fixture",
    })
    # Vision model
    client.post("/v1/models/", json={
        "model_id": "vision-model",
        "name": "Test Vision Model",
        "family": "test",
        "capabilities": ["TEXT", "VISION", "DOCUMENT_UNDERSTANDING"],
        "context_length": 4096,
        "tool_calling": False,
        "runtime": "fixture",
    })


# ---------------------------------------------------------------------------
# Two task types → different model selection (R3 requirement)
# ---------------------------------------------------------------------------


class TestTwoTaskTypes:
    """Demonstrates routing across two different task types.

    This is the core acceptance gate for Sprint 1:
    "router decision is reproducible and explainable for at least
    two different task types."
    """

    def test_code_review_routes_to_reasoning_model(self):
        _seed_two_models()
        response = client.post("/v1/tasks/", json={
            "task_type": "code_review",
            "description": "Review this Python code for security vulnerabilities",
            "input_data": {"code": "def login(user, pwd): return user == 'admin'"},
        })
        assert response.status_code == 201
        data = response.json()
        assert data["current_state"] == "DELIVER"
        assert data["selected_model_id"] == "reasoning-model"
        assert data["routing_rationale"] is not None
        assert "CODING" in data["routing_rationale"]
        _clear()

    def test_document_analysis_routes_to_vision_model(self):
        _seed_two_models()
        response = client.post("/v1/tasks/", json={
            "task_type": "document_analysis",
            "description": "Analyze this scanned inspection report",
            "input_data": {"document_url": "sample_report.pdf"},
        })
        assert response.status_code == 201
        data = response.json()
        assert data["current_state"] == "DELIVER"
        assert data["selected_model_id"] == "vision-model"
        assert data["routing_rationale"] is not None
        assert "VISION" in data["routing_rationale"]
        _clear()

    def test_different_models_for_different_tasks(self):
        """Verify two task types produce different routing decisions."""
        _seed_two_models()

        # Task 1: code review
        r1 = client.post("/v1/tasks/", json={
            "task_type": "code_review",
            "description": "Review code",
        })
        # Task 2: document analysis
        r2 = client.post("/v1/tasks/", json={
            "task_type": "document_analysis",
            "description": "Analyze document",
        })

        d1 = r1.json()
        d2 = r2.json()

        # Different models selected
        assert d1["selected_model_id"] != d2["selected_model_id"]
        # Both have routing rationale
        assert d1["routing_rationale"]
        assert d2["routing_rationale"]
        # Both completed successfully
        assert d1["current_state"] == "DELIVER"
        assert d2["current_state"] == "DELIVER"
        _clear()


# ---------------------------------------------------------------------------
# Pipeline observability
# ---------------------------------------------------------------------------


class TestPipelineObservability:
    def test_routing_rationale_is_human_readable(self):
        _seed_two_models()
        response = client.post("/v1/tasks/", json={
            "task_type": "code_review",
            "description": "Check code quality",
        })
        data = response.json()
        rationale = data["routing_rationale"]
        # Must contain pipeline step references
        assert "Step 1" in rationale
        assert "capability" in rationale.lower()
        _clear()

    def test_state_history_is_complete(self):
        _seed_two_models()
        response = client.post("/v1/tasks/", json={
            "task_type": "reasoning",
            "description": "Explain AI sovereignty",
        })
        data = response.json()
        history = data["state_history"]
        states = [t["to_state"] for t in history]
        assert "CLASSIFY" in states
        assert "PLAN" in states
        assert "DELIVER" in states
        _clear()

    def test_task_retrievable_after_submission(self):
        _seed_two_models()
        response = client.post("/v1/tasks/", json={
            "task_type": "reasoning",
            "description": "Test retrieval",
        })
        task_id = response.json()["task_id"]
        get_response = client.get(f"/v1/tasks/{task_id}")
        assert get_response.status_code == 200
        assert get_response.json()["task_id"] == task_id
        _clear()

    def test_task_list_endpoint(self):
        _seed_two_models()
        client.post("/v1/tasks/", json={
            "task_type": "reasoning",
            "description": "Task A",
        })
        client.post("/v1/tasks/", json={
            "task_type": "code_review",
            "description": "Task B",
        })
        response = client.get("/v1/tasks/")
        assert response.status_code == 200
        assert len(response.json()) >= 2
        _clear()


# ---------------------------------------------------------------------------
# Routing reproducibility
# ---------------------------------------------------------------------------


class TestRoutingReproducibility:
    def test_same_task_same_route(self):
        """Same task type must always route to the same model."""
        _seed_two_models()
        results = []
        for _ in range(3):
            r = client.post("/v1/tasks/", json={
                "task_type": "code_review",
                "description": "Reproducibility test",
            })
            results.append(r.json()["selected_model_id"])
        assert len(set(results)) == 1  # all same
        _clear()
