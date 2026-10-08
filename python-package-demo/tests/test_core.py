"""
Unit tests for python_package_demo.core.
Verifies API client and health check logic.
"""

from unittest.mock import MagicMock, patch
import requests
from python_package_demo.core import APIClient, HealthCheckResult, check_endpoint_health


def test_api_client_initialization():
    client = APIClient(base_url="https://api.example.com", timeout=5.0)
    assert client.base_url == "https://api.example.com"
    assert client.timeout == 5.0
    assert "User-Agent" in client.session.headers


@patch("requests.Session.request")
def test_api_client_get_json(mock_request):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok", "version": "1.0"}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response

    client = APIClient(base_url="https://api.example.com")
    data = client.get_json("/health")

    assert data == {"status": "ok", "version": "1.0"}
    mock_request.assert_called_once_with(
        method="GET",
        url="https://api.example.com/health",
        timeout=10.0,
    )


@patch("requests.get")
def test_check_endpoint_health_success(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.elapsed.total_seconds.return_value = 0.045
    mock_get.return_value = mock_response

    result = check_endpoint_health("https://example.com/health")
    assert isinstance(result, HealthCheckResult)
    assert result.status_code == 200
    assert result.is_healthy is True
    assert result.response_time_ms == 45.0


@patch("requests.get")
def test_check_endpoint_health_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("Connection refused")

    result = check_endpoint_health("https://unreachable.example.com")
    assert isinstance(result, HealthCheckResult)
    assert result.status_code == 0
    assert result.is_healthy is False
    assert result.response_time_ms == -1.0
    assert "Connection refused" in result.details["error"]
