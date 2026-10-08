"""Pytest fixtures and test environment configuration."""

import os
import sys
import pytest

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datapipeline.api.app import PipelineApp, build_default_container
from datapipeline.api.client import PipelineClient
from datapipeline.di.container import Container
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
from datapipeline.services.auth_service import AuthService
from datapipeline.services.pipeline_service import PipelineService


@pytest.fixture
def container():
    """Isolated test container fixture."""
    c = Container()
    c.register_singleton(IStorageService, InMemoryStorageService)
    c.register_singleton(IAuthService, HmacAuthService)
    c.register_singleton(IMetricsCollector, InMemoryMetricsCollector)
    c.register_singleton(IDataTransformer, StandardDataTransformer)
    c.register_singleton(INotificationService, ConsoleNotificationService)
    c.register_singleton(PipelineService)
    c.register_singleton(AuthService)
    return c


@pytest.fixture
def app(container):
    """PipelineApp instance wired with the test container."""
    return PipelineApp(container)


@pytest.fixture
def client(app):
    """PipelineClient instance configured with test app."""
    return PipelineClient(app)


@pytest.fixture
def auth_token(app):
    """Valid authorization token fixture."""
    status, _, body = app.handle_request(
        "POST",
        "/api/v1/auth/token",
        body={"client_id": "admin-client", "client_secret": "secret-admin-token-key-prod-99"},
    )
    assert status == 200
    return body["data"]["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers dictionary containing Bearer token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
