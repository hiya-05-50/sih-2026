from fastapi.testclient import TestClient
from app.main import app, registry, adapter_manager

client = TestClient(app)

def _clear_registry():
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SAFIRE Backend"
    assert data["status"] == "running"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ready_no_models():
    _clear_registry()
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "reason": "No models registered"
    }

def test_ready_with_model():
    _clear_registry()
    client.post("/v1/models/", json={
        "model_id": "ready-test",
        "name": "Ready Test",
        "family": "test",
        "capabilities": ["TEXT"],
        "context_length": 4096,
        "tool_calling": False,
    })
    # Force adapter creation by hitting health
    client.get("/v1/models/ready-test/health")
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["models_registered"] >= 1
    assert body["models_healthy"] >= 1
    _clear_registry()
