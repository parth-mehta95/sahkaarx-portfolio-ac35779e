"""Secure Data Pipeline Package.

A production-ready data pipeline framework featuring dependency injection,
robust API endpoint validation, and continuous security controls.
"""

__version__ = "1.0.0"
__author__ = "Engineering & Platform Security Team"
__license__ = "MIT"

from datapipeline.di.container import Container, Scope, inject
from datapipeline.di.interfaces import (
    IStorageService,
    IAuthService,
    IMetricsCollector,
    IDataTransformer,
    INotificationService,
)
from datapipeline.services.pipeline_service import PipelineService
from datapipeline.services.auth_service import AuthService
from datapipeline.api.app import PipelineApp
from datapipeline.api.client import PipelineClient

__all__ = [
    "__version__",
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
