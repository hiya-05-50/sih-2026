"""Integration tests verifying backend API contracts.

These tests use contract fixtures to validate that the backend endpoints
return the responses that both backend and frontend agree upon.
Covers Sprint 0 baseline contracts and Sprint 1 model/routing contracts.
"""


def test_root_contract(client, root_contract):
    """GET / returns the expected contract response."""
    response = client.get(root_contract["path"])
    assert response.status_code == root_contract["expected_status"]
    assert response.json() == root_contract["expected_body"]


def test_health_contract(client, health_contract):
    """GET /health returns the expected contract response."""
    response = client.get(health_contract["path"])
    assert response.status_code == health_contract["expected_status"]
    assert response.json() == health_contract["expected_body"]


def test_ready_contract(client, ready_contract):
    """GET /ready returns the expected contract response."""
    response = client.get(ready_contract["path"])
    assert response.status_code == ready_contract["expected_status"]
    assert response.json() == ready_contract["expected_body"]


# Sprint 1 contract tests -----------------------------------------------------


def test_register_model_contract(client, register_model_contract):
    """POST /v1/models/ registers a model and returns 201."""
    response = client.post(
        register_model_contract["path"],
        json=register_model_contract["payload"],
    )
    assert response.status_code == register_model_contract["expected_status"]
    data = response.json()
    assert data["model_id"] == "contract-model"
    assert data["name"] == "Contract Model"


def test_list_models_contract(client, list_models_contract):
    """GET /v1/models/ returns a list."""
    response = client.get(list_models_contract["path"])
    assert response.status_code == list_models_contract["expected_status"]
    assert isinstance(response.json(), list)


def test_route_no_match_contract(client, route_no_match_contract):
    """POST /v1/route with no matching model returns 404."""
    response = client.post(
        route_no_match_contract["path"],
        json=route_no_match_contract["payload"],
    )
    assert response.status_code == route_no_match_contract["expected_status"]
