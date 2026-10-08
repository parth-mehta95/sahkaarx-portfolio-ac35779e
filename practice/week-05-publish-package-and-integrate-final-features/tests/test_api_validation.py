"""Comprehensive validation test suite for all REST API endpoints."""

import json
import pytest
from datapipeline import __version__


class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    def test_health_check_returns_200(self, app):
        status, headers, body = app.handle_request("GET", "/api/v1/health")
        assert status == 200
        assert headers["Content-Type"] == "application/json"
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"
        assert body["data"]["version"] == __version__
        assert "uptime_seconds" in body["data"]
        assert len(body["data"]["container_services"]) == 5


class TestAuthenticationEndpoints:
    """Tests for POST /api/v1/auth/token."""

    def test_auth_success_with_valid_credentials(self, app):
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client", "client_secret": "secret-admin-token-key-prod-99"},
        )
        assert status == 200
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert body["data"]["token_type"] == "Bearer"
        assert body["data"]["expires_in"] == 86400

    def test_auth_fails_with_invalid_secret(self, app):
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client", "client_secret": "wrong-secret"},
        )
        assert status == 401
        assert body["success"] is False
        assert "Invalid client credentials" in body["errors"][0]

    def test_auth_fails_with_missing_fields(self, app):
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/auth/token",
            body={"client_id": "admin-client"},
        )
        assert status == 400
        assert body["success"] is False
        assert "Both 'client_id' and 'client_secret' are required" in body["errors"][0]


class TestPipelineEndpoints:
    """Tests for Pipeline Management endpoints."""

    def test_list_pipelines_unauthorized_without_token(self, app):
        status, _, body = app.handle_request("GET", "/api/v1/pipelines")
        assert status == 401
        assert body["success"] is False
        assert "Unauthorized" in body["errors"][0]

    def test_create_and_list_pipelines_success(self, app, auth_headers):
        payload = {
            "pipeline_id": "sales-ingest-v1",
            "name": "Sales Ingestion Pipeline",
            "description": "Transforms and sanitizes daily sales data",
            "transform_operations": ["strip_whitespace", "lowercase_keys", "hash_pii"],
            "max_retries": 3,
            "timeout_seconds": 600,
        }
        status, _, body = app.handle_request("POST", "/api/v1/pipelines", headers=auth_headers, body=payload)
        assert status == 201
        assert body["success"] is True
        assert body["data"]["pipeline_id"] == "sales-ingest-v1"

        # List pipelines
        status, _, list_body = app.handle_request("GET", "/api/v1/pipelines", headers=auth_headers)
        assert status == 200
        assert len(list_body["data"]) >= 1
        ids = [p["pipeline_id"] for p in list_body["data"]]
        assert "sales-ingest-v1" in ids

    def test_create_pipeline_validation_errors(self, app, auth_headers):
        # Invalid pipeline_id (special chars)
        bad_payload = {
            "pipeline_id": "bad/id/$$",
            "name": "Valid Name",
        }
        status, _, body = app.handle_request("POST", "/api/v1/pipelines", headers=auth_headers, body=bad_payload)
        assert status == 400
        assert body["success"] is False

        # Name too short
        bad_payload = {
            "pipeline_id": "pipe-02",
            "name": "x",
        }
        status, _, body = app.handle_request("POST", "/api/v1/pipelines", headers=auth_headers, body=bad_payload)
        assert status == 400

        # Unsupported transform operation
        bad_payload = {
            "pipeline_id": "pipe-03",
            "name": "Pipe 3",
            "transform_operations": ["unsupported_operation_xyz"],
        }
        status, _, body = app.handle_request("POST", "/api/v1/pipelines", headers=auth_headers, body=bad_payload)
        assert status == 400

    def test_get_pipeline_by_id(self, app, auth_headers):
        # Create pipeline first
        app.handle_request(
            "POST",
            "/api/v1/pipelines",
            headers=auth_headers,
            body={"pipeline_id": "fetch-test-pipe", "name": "Fetch Test"},
        )

        # Successful fetch
        status, _, body = app.handle_request("GET", "/api/v1/pipelines/fetch-test-pipe", headers=auth_headers)
        assert status == 200
        assert body["data"]["pipeline_id"] == "fetch-test-pipe"

        # 404 for non-existent pipeline
        status, _, body = app.handle_request("GET", "/api/v1/pipelines/non-existent-pipe", headers=auth_headers)
        assert status == 404
        assert body["success"] is False

    def test_run_pipeline_execution_and_transforms(self, app, auth_headers):
        # Register pipeline with pii hashing and strip whitespace
        app.handle_request(
            "POST",
            "/api/v1/pipelines",
            headers=auth_headers,
            body={
                "pipeline_id": "exec-pipe-01",
                "name": "Execution Pipeline",
                "transform_operations": ["strip_whitespace", "hash_pii"],
            },
        )

        input_data = {
            "records": [
                {"name": "   Jane Doe   ", "email": "jane@company.com", "department": "Security"},
                {"name": " John Smith ", "email": "john@company.com", "department": "Finance"},
            ]
        }

        status, _, body = app.handle_request(
            "POST",
            "/api/v1/pipelines/exec-pipe-01/run",
            headers=auth_headers,
            body=input_data,
        )
        assert status == 200
        assert body["success"] is True
        output = body["data"]["output"]
        assert len(output) == 2
        # Check whitespace stripped
        assert output[0]["name"] == "Jane Doe"
        # Check PII hashed
        assert "email" not in output[0]
        assert "email_hash" in output[0]
        assert len(output[0]["email_hash"]) == 64  # SHA256 length


class TestDatasetEndpoints:
    """Tests for Dataset Validation endpoints."""

    def test_validate_dataset_success(self, app, auth_headers):
        dataset_body = {
            "dataset_id": "customer-events-2026",
            "schema_version": "1.0",
            "records": [
                {"event": "login", "timestamp": 1728390000},
                {"event": "logout", "timestamp": 1728393600},
            ],
        }
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/datasets/validate",
            headers=auth_headers,
            body=dataset_body,
        )
        assert status == 200
        assert body["success"] is True
        assert body["data"]["record_count"] == 2

    def test_validate_dataset_unprocessable_entity(self, app, auth_headers):
        # Missing records / empty records list
        invalid_body = {
            "dataset_id": "empty-dataset",
            "records": [],
        }
        status, _, body = app.handle_request(
            "POST",
            "/api/v1/datasets/validate",
            headers=auth_headers,
            body=invalid_body,
        )
        assert status == 422
        assert body["success"] is False


class TestMetricsAndSystemEndpoints:
    """Tests for Metrics and Global Error Handling."""

    def test_metrics_endpoint(self, app):
        status, _, body = app.handle_request("GET", "/api/v1/metrics")
        assert status == 200
        assert "counters" in body["data"]
        assert "gauges" in body["data"]

    def test_malformed_json_body(self, app):
        status, _, body = app.handle_request("POST", "/api/v1/auth/token", body="not-json{")
        assert status == 400
        assert "Malformed JSON" in body["errors"][0]

    def test_route_not_found(self, app):
        status, _, body = app.handle_request("GET", "/api/v1/non-existent-endpoint")
        assert status == 404
        assert body["success"] is False
