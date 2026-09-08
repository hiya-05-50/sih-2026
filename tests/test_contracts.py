"""Integration tests verifying backend API contracts.

These tests use contract fixtures to validate that the backend endpoints
return the responses that both backend and frontend agree upon.
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
