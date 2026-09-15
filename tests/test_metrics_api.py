import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_metrics.db")

from app.db.base import Base
from app.db.session import engine
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


def test_required_fields_and_invalid_payloads():
    missing_fields_cases = [
        {},
        {"app_id": "app-1", "environment": "production", "metric": "cpu_usage", "timestamp": "2026-09-15T16:00:00Z"},
        {"app_id": "app-1", "environment": "production", "metric": "cpu_usage", "value": 50},
        {"app_id": "app-1", "metric": "cpu_usage", "value": 50, "timestamp": "2026-09-15T16:00:00Z"},
    ]
    for payload in missing_fields_cases:
        response = client.post("/v1/apps/metrics", json=payload)
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False

    invalid_env_response = client.post(
        "/v1/apps/metrics",
        json={
            "app_id": "app-1",
            "environment": "qa",
            "metric": "cpu_usage",
            "value": 50,
            "timestamp": "2026-09-15T16:00:00Z",
        },
    )
    assert invalid_env_response.status_code == 422

    invalid_metric_response = client.post(
        "/v1/apps/metrics",
        json={
            "app_id": "app-1",
            "environment": "production",
            "metric": "latency",
            "value": 50,
            "timestamp": "2026-09-15T16:00:00Z",
        },
    )
    assert invalid_metric_response.status_code == 422

    invalid_percentage_response = client.post(
        "/v1/apps/metrics",
        json={
            "app_id": "app-1",
            "environment": "production",
            "metric": "memory_usage",
            "value": 120,
            "timestamp": "2026-09-15T16:00:00Z",
        },
    )
    assert invalid_percentage_response.status_code == 422

    invalid_counter_response = client.post(
        "/v1/apps/metrics",
        json={
            "app_id": "app-1",
            "environment": "production",
            "metric": "request_count",
            "value": -1,
            "timestamp": "2026-09-15T16:00:00Z",
        },
    )
    assert invalid_counter_response.status_code == 422


def test_ingest_and_fetch_metrics():
    payload = {
        "app_id": "app-123",
        "environment": "production",
        "metric": "cpu_usage",
        "value": 72.5,
        "timestamp": "2026-09-15T16:30:00Z",
    }

    ingest_response = client.post("/v1/apps/metrics", json=payload)
    assert ingest_response.status_code == 201, ingest_response.text
    body = ingest_response.json()
    assert body["success"] is True
    assert body["data"]["app_id"] == "app-123"

    fetch_response = client.get(
        "/v1/apps/app-123/metrics",
        params={
            "metric": "cpu_usage",
            "environment": "production",
            "from": "2026-09-15T00:00:00Z",
            "to": "2026-09-16T00:00:00Z",
        },
    )
    assert fetch_response.status_code == 200, fetch_response.text
    fetch_body = fetch_response.json()
    assert fetch_body["success"] is True
    assert fetch_body["data"]["count"] >= 1


def test_metric_aggregate_and_validation():
    percentage_payloads = [
        {
            "app_id": "app-456",
            "environment": "staging",
            "metric": "memory_usage",
            "value": 40,
            "timestamp": "2026-09-15T10:00:00Z",
        },
        {
            "app_id": "app-456",
            "environment": "staging",
            "metric": "memory_usage",
            "value": 60,
            "timestamp": "2026-09-15T11:00:00Z",
        },
    ]
    for payload in percentage_payloads:
        response = client.post("/v1/apps/metrics", json=payload)
        assert response.status_code == 201, response.text

    aggregate_response = client.get(
        "/v1/apps/app-456/aggregate",
        params={
            "metric": "memory_usage",
            "environment": "staging",
            "from": "2026-09-15T00:00:00Z",
            "to": "2026-09-16T00:00:00Z",
        },
    )
    assert aggregate_response.status_code == 200, aggregate_response.text
    data = aggregate_response.json()
    assert data["success"] is True
    aggregate = data["data"]
    assert aggregate["count"] == 2
    assert aggregate["average"] == 50.0
    assert aggregate["minimum"] == 40.0
    assert aggregate["maximum"] == 60.0
    assert aggregate["total"] is None

    count_payloads = [
        {
            "app_id": "app-789",
            "environment": "production",
            "metric": "request_count",
            "value": 5,
            "timestamp": "2026-09-15T12:00:00Z",
        },
        {
            "app_id": "app-789",
            "environment": "production",
            "metric": "request_count",
            "value": 7,
            "timestamp": "2026-09-15T13:00:00Z",
        },
        {
            "app_id": "app-789",
            "environment": "production",
            "metric": "request_count",
            "value": 6,
            "timestamp": "2026-09-15T14:00:00Z",
        },
    ]
    for payload in count_payloads:
        response = client.post("/v1/apps/metrics", json=payload)
        assert response.status_code == 201, response.text

    count_aggregate_response = client.get(
        "/v1/apps/app-789/aggregate",
        params={
            "metric": "request_count",
            "environment": "production",
            "from": "2026-09-15T00:00:00Z",
            "to": "2026-09-16T00:00:00Z",
        },
    )
    assert count_aggregate_response.status_code == 200, count_aggregate_response.text
    count_data = count_aggregate_response.json()
    assert count_data["success"] is True
    count_aggregate = count_data["data"]
    assert count_aggregate["count"] == 3
    assert count_aggregate["average"] == 6.0
    assert count_aggregate["minimum"] == 5.0
    assert count_aggregate["maximum"] == 7.0
    assert count_aggregate["total"] == 18.0

    no_data_response = client.get(
        "/v1/apps/no-such-app/aggregate",
        params={
            "metric": "cpu_usage",
            "environment": "production",
            "from": "2026-09-15T00:00:00Z",
            "to": "2026-09-16T00:00:00Z",
        },
    )
    assert no_data_response.status_code == 404
    assert no_data_response.json()["success"] is False

    invalid_time_range_response = client.get(
        "/v1/apps/app-123/aggregate",
        params={
            "metric": "cpu_usage",
            "environment": "production",
            "from": "2026-09-16T00:00:00Z",
            "to": "2026-09-15T00:00:00Z",
        },
    )
    assert invalid_time_range_response.status_code == 422
    assert invalid_time_range_response.json()["success"] is False
