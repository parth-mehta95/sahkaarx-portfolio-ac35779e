"""
Core functionality for python-package-demo.
Demonstrates structured, typed HTTP client interactions using pinned dependencies.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import requests


@dataclass
class HealthCheckResult:
    """Represents the outcome of an HTTP health check."""
    status_code: int
    is_healthy: bool
    response_time_ms: float
    url: str
    details: Optional[Dict[str, Any]] = None


class APIClient:
    """A resilient, configurable HTTP client leveraging pinned dependencies."""

    def __init__(self, base_url: str = "", timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "python-package-demo/0.1.0",
            "Accept": "application/json",
        })

    def request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Sends an HTTP request with configured defaults."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}" if self.base_url else endpoint
        kwargs.setdefault("timeout", self.timeout)
        response = self.session.request(method=method, url=url, **kwargs)
        return response

    def get_json(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Performs a GET request and returns JSON data."""
        response = self.request("GET", endpoint, **kwargs)
        response.raise_for_status()
        return response.json()


def check_endpoint_health(url: str, timeout: float = 5.0) -> HealthCheckResult:
    """
    Checks if a target URL responds with a 2xx status code within the timeout.
    """
    try:
        response = requests.get(url, timeout=timeout)
        elapsed_ms = response.elapsed.total_seconds() * 1000.0
        return HealthCheckResult(
            status_code=response.status_code,
            is_healthy=response.ok,
            response_time_ms=round(elapsed_ms, 2),
            url=url,
        )
    except requests.RequestException as exc:
        return HealthCheckResult(
            status_code=0,
            is_healthy=False,
            response_time_ms=-1.0,
            url=url,
            details={"error": str(exc)},
        )
