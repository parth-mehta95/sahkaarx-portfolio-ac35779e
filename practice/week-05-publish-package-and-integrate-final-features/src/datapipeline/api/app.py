"""REST API application with Dependency Injection and route dispatching."""

import json
import re
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from datapipeline import __version__
from datapipeline.di.container import Container, Scope, get_default_container, set_default_container
from datapipeline.di.interfaces import (
    IAuthService,
    IDataTransformer,
    IMetricsCollector,
    INotificationService,
    IStorageService,
)
from datapipeline.di.providers import (
    ConsoleNotificationService,
    HmacAuthService,
    InMemoryMetricsCollector,
    InMemoryStorageService,
    StandardDataTransformer,
)
from datapipeline.models import APIResponse, DatasetPayload, PipelineConfig, ValidationError
from datapipeline.services.auth_service import AuthService
from datapipeline.services.pipeline_service import PipelineService


def build_default_container() -> Container:
    """Build and wire the default production Dependency Injection container."""
    container = Container()

    # Core service provider singletons
    container.register_singleton(IStorageService, InMemoryStorageService)
    container.register_singleton(IAuthService, HmacAuthService)
    container.register_singleton(IMetricsCollector, InMemoryMetricsCollector)
    container.register_singleton(IDataTransformer, StandardDataTransformer)
    container.register_singleton(INotificationService, ConsoleNotificationService)

    # Domain services
    container.register_singleton(PipelineService)
    container.register_singleton(AuthService)

    return container


class PipelineApp:
    """Production REST API Application with dependency injection routing."""

    def __init__(self, container: Optional[Container] = None):
        self.container = container or build_default_container()
        self.start_time = time.time()
        self.routes: List[Tuple[str, str, Callable]] = []
        self._register_routes()

    def _register_routes(self) -> None:
        """Register all validated API endpoints."""
        self.add_route("GET", r"^/api/v1/health$", self.handle_health)
        self.add_route("POST", r"^/api/v1/auth/token$", self.handle_auth_token)
        self.add_route("GET", r"^/api/v1/pipelines$", self.handle_list_pipelines)
        self.add_route("POST", r"^/api/v1/pipelines$", self.handle_create_pipeline)
        self.add_route("GET", r"^/api/v1/pipelines/(?P<id>[a-zA-Z0-9_\-]+)$", self.handle_get_pipeline)
        self.add_route("POST", r"^/api/v1/pipelines/(?P<id>[a-zA-Z0-9_\-]+)/run$", self.handle_run_pipeline)
        self.add_route("GET", r"^/api/v1/datasets$", self.handle_list_datasets)
        self.add_route("POST", r"^/api/v1/datasets/validate$", self.handle_validate_dataset)
        self.add_route("GET", r"^/api/v1/metrics$", self.handle_get_metrics)

    def add_route(self, method: str, pattern: str, handler: Callable) -> None:
        self.routes.append((method.upper(), pattern, handler))

    def _authenticate_request(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Validate Bearer authorization header using injected AuthService."""
        auth_header = headers.get("Authorization") or headers.get("authorization") or ""
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:].strip()
        auth_service: AuthService = self.container.resolve(AuthService)
        return auth_service.verify_token(token)

    def handle_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Dict[str, Any]]] = None,
    ) -> Tuple[int, Dict[str, str], Dict[str, Any]]:
        """Core dispatcher for processing API requests and returning (status, headers, body)."""
        headers = headers or {}
        method = method.upper()

        parsed_body = {}
        if body:
            if isinstance(body, dict):
                parsed_body = body
            elif isinstance(body, (str, bytes)):
                try:
                    parsed_body = json.loads(body)
                except Exception:
                    resp = APIResponse(
                        success=False,
                        errors=["Malformed JSON in request body"],
                        status_code=400,
                    )
                    return 400, {"Content-Type": "application/json"}, resp.to_dict()

        for route_method, pattern, handler in self.routes:
            if route_method == method:
                match = re.match(pattern, path)
                if match:
                    kwargs = match.groupdict()
                    try:
                        status, payload = handler(headers, parsed_body, **kwargs)
                        return status, {"Content-Type": "application/json"}, payload
                    except ValidationError as ve:
                        resp = APIResponse(success=False, errors=ve.errors, status_code=400)
                        return 400, {"Content-Type": "application/json"}, resp.to_dict()
                    except Exception as ex:
                        resp = APIResponse(success=False, errors=[str(ex)], status_code=500)
                        return 500, {"Content-Type": "application/json"}, resp.to_dict()

        resp = APIResponse(success=False, errors=[f"Endpoint not found: {method} {path}"], status_code=404)
        return 404, {"Content-Type": "application/json"}, resp.to_dict()

    # --- API Handlers ---

    def handle_health(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """GET /api/v1/health - System and container health check."""
        metrics: IMetricsCollector = self.container.resolve(IMetricsCollector)
        metrics.increment_counter("health_checks_total", 1)
        uptime = round(time.time() - self.start_time, 2)
        resp = APIResponse(
            success=True,
            data={
                "status": "healthy",
                "version": __version__,
                "uptime_seconds": uptime,
                "container_services": [
                    "IStorageService",
                    "IAuthService",
                    "IMetricsCollector",
                    "IDataTransformer",
                    "INotificationService",
                ],
            },
            status_code=200,
        )
        return 200, resp.to_dict()

    def handle_auth_token(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /api/v1/auth/token - Obtain Bearer token with client credentials."""
        client_id = body.get("client_id")
        client_secret = body.get("client_secret")

        if not client_id or not client_secret:
            resp = APIResponse(
                success=False,
                errors=["Both 'client_id' and 'client_secret' are required"],
                status_code=400,
            )
            return 400, resp.to_dict()

        auth_service: AuthService = self.container.resolve(AuthService)
        token = auth_service.authenticate(client_id, client_secret)
        if not token:
            resp = APIResponse(
                success=False,
                errors=["Invalid client credentials"],
                status_code=401,
            )
            return 401, resp.to_dict()

        resp = APIResponse(
            success=True,
            data={
                "access_token": token,
                "token_type": "Bearer",
                "expires_in": 86400,
            },
            status_code=200,
        )
        return 200, resp.to_dict()

    def handle_list_pipelines(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """GET /api/v1/pipelines - List all registered pipelines (authenticated)."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        svc: PipelineService = self.container.resolve(PipelineService)
        pipelines = svc.list_pipelines()
        return 200, APIResponse(success=True, data=pipelines, status_code=200).to_dict()

    def handle_create_pipeline(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /api/v1/pipelines - Register a new pipeline definition (authenticated)."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        svc: PipelineService = self.container.resolve(PipelineService)
        created = svc.register_pipeline(body)
        return 201, APIResponse(success=True, data=created, status_code=201).to_dict()

    def handle_get_pipeline(self, headers: Dict[str, str], body: Dict[str, Any], id: str) -> Tuple[int, Dict[str, Any]]:
        """GET /api/v1/pipelines/{id} - Retrieve pipeline by ID."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        svc: PipelineService = self.container.resolve(PipelineService)
        item = svc.get_pipeline(id)
        if not item:
            return 404, APIResponse(success=False, errors=[f"Pipeline '{id}' not found"], status_code=404).to_dict()
        return 200, APIResponse(success=True, data=item, status_code=200).to_dict()

    def handle_run_pipeline(self, headers: Dict[str, str], body: Dict[str, Any], id: str) -> Tuple[int, Dict[str, Any]]:
        """POST /api/v1/pipelines/{id}/run - Execute a pipeline."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        input_records = body.get("records", [])
        if not isinstance(input_records, list):
            return 400, APIResponse(success=False, errors=["'records' must be a list of objects"], status_code=400).to_dict()

        svc: PipelineService = self.container.resolve(PipelineService)
        try:
            result = svc.run_pipeline(id, input_records)
            return 200, APIResponse(success=True, data=result, status_code=200).to_dict()
        except ValidationError as ve:
            return 400, APIResponse(success=False, errors=ve.errors, status_code=400).to_dict()

    def handle_list_datasets(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """GET /api/v1/datasets - List stored datasets."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        storage: IStorageService = self.container.resolve(IStorageService)
        datasets = storage.list("datasets")
        return 200, APIResponse(success=True, data=datasets, status_code=200).to_dict()

    def handle_validate_dataset(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """POST /api/v1/datasets/validate - Validate schema of dataset payload."""
        claims = self._authenticate_request(headers)
        if not claims:
            return 401, APIResponse(success=False, errors=["Unauthorized: Valid Bearer token required"], status_code=401).to_dict()

        try:
            dataset = DatasetPayload.from_dict(body)
            # Store validated dataset
            storage: IStorageService = self.container.resolve(IStorageService)
            saved = storage.save("datasets", dataset.dataset_id, dataset.to_dict())
            return 200, APIResponse(
                success=True,
                data={"dataset_id": dataset.dataset_id, "record_count": len(dataset.records), "status": "validated"},
                status_code=200,
            ).to_dict()
        except ValidationError as ve:
            return 422, APIResponse(success=False, errors=ve.errors, status_code=422).to_dict()

    def handle_get_metrics(self, headers: Dict[str, str], body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """GET /api/v1/metrics - Export metrics snapshot."""
        metrics: IMetricsCollector = self.container.resolve(IMetricsCollector)
        snapshot = metrics.get_metrics_snapshot()
        return 200, APIResponse(success=True, data=snapshot, status_code=200).to_dict()


def main():
    """CLI entrypoint for running local test server."""
    print(f"Secure Data Pipeline Server v{__version__} initialized.")
    app = PipelineApp()
    status, _, data = app.handle_request("GET", "/api/v1/health")
    print(f"Initial Health Status: {status} -> {data}")
    sys.exit(0)


if __name__ == "__main__":
    main()
