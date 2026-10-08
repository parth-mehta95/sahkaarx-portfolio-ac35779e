"""Tests validating package metadata, version integrity, and SDK client operations."""

import pytest
import datapipeline


def test_package_version_and_metadata():
    assert datapipeline.__version__ == "1.0.0"
    assert datapipeline.__author__ != ""
    assert datapipeline.__license__ == "MIT"


def test_public_api_symbols_exported():
    expected_symbols = [
        "Container",
        "Scope",
        "inject",
        "IStorageService",
        "IAuthService",
        "IMetricsCollector",
        "IDataTransformer",
        "INotificationService",
        "PipelineService",
        "AuthService",
        "PipelineApp",
        "PipelineClient",
    ]
    for symbol in expected_symbols:
        assert hasattr(datapipeline, symbol), f"datapipeline missing export '{symbol}'"


def test_sdk_client_end_to_end_flow(client):
    # 1. Health
    health = client.health()
    assert health["success"] is True

    # 2. Authenticate
    token = client.authenticate("admin-client", "secret-admin-token-key-prod-99")
    assert token is not None

    # 3. Create pipeline
    config = {
        "pipeline_id": "client-sdk-pipe",
        "name": "SDK Pipeline",
        "transform_operations": ["strip_whitespace"],
    }
    created = client.create_pipeline(config)
    assert created["pipeline_id"] == "client-sdk-pipe"

    # 4. Get pipeline
    fetched = client.get_pipeline("client-sdk-pipe")
    assert fetched["name"] == "SDK Pipeline"

    # 5. Run pipeline
    records = [{"item": " widget   "}]
    run_res = client.run_pipeline("client-sdk-pipe", records)
    assert run_res["status"] == "success"
    assert run_res["output"][0]["item"] == "widget"

    # 6. Validate dataset
    ds = client.validate_dataset("dataset-sdk-01", [{"col": 1}, {"col": 2}])
    assert ds["record_count"] == 2

    # 7. Metrics
    metrics = client.get_metrics()
    assert "counters" in metrics
