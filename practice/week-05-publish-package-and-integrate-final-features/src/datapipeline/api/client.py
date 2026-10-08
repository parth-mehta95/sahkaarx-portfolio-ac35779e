"""SDK Client for interacting with Secure Data Pipeline REST API."""

from typing import Any, Dict, List, Optional
from datapipeline.api.app import PipelineApp


class PipelineClient:
    """Client for executing requests against the Pipeline API."""

    def __init__(self, app: Optional[PipelineApp] = None, base_url: str = "http://localhost:8000"):
        self.app = app or PipelineApp()
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def authenticate(self, client_id: str, client_secret: str) -> str:
        """Authenticate and cache the returned Bearer token."""
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/auth/token",
            headers={"Content-Type": "application/json"},
            body={"client_id": client_id, "client_secret": client_secret},
        )
        if status != 200 or not body.get("success"):
            raise ValueError(f"Authentication failed: {body.get('errors')}")
        self.token = body["data"]["access_token"]
        return self.token

    def health(self) -> Dict[str, Any]:
        """Check server health."""
        status, _, body = self.app.handle_request("GET", "/api/v1/health")
        return body

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List registered pipelines."""
        status, _, body = self.app.handle_request("GET", "/api/v1/pipelines", headers=self._headers())
        if status != 200:
            raise RuntimeError(f"Error {status}: {body.get('errors')}")
        return body.get("data", [])

    def create_pipeline(self, pipeline_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline."""
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/pipelines",
            headers=self._headers(),
            body=pipeline_config,
        )
        if status != 201:
            raise ValueError(f"Error {status}: {body.get('errors')}")
        return body.get("data", {})

    def get_pipeline(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline details."""
        status, _, body = self.app.handle_request(
            "GET",
            f"/api/v1/pipelines/{pipeline_id}",
            headers=self._headers(),
        )
        if status != 200:
            raise KeyError(f"Error {status}: {body.get('errors')}")
        return body.get("data", {})

    def run_pipeline(self, pipeline_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a pipeline with records."""
        status, _, body = self.app.handle_request(
            "POST",
            f"/api/v1/pipelines/{pipeline_id}/run",
            headers=self._headers(),
            body={"records": records},
        )
        if status != 200:
            raise RuntimeError(f"Error {status}: {body.get('errors')}")
        return body.get("data", {})

    def validate_dataset(self, dataset_id: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate and store dataset records."""
        status, _, body = self.app.handle_request(
            "POST",
            "/api/v1/datasets/validate",
            headers=self._headers(),
            body={"dataset_id": dataset_id, "records": records},
        )
        if status != 200:
            raise ValueError(f"Validation failed ({status}): {body.get('errors')}")
        return body.get("data", {})

    def get_metrics(self) -> Dict[str, Any]:
        """Fetch metrics summary."""
        status, _, body = self.app.handle_request("GET", "/api/v1/metrics", headers=self._headers())
        return body.get("data", {})
