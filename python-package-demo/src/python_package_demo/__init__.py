"""
python-package-demo
~~~~~~~~~~~~~~~~~~~

A reusable Python package foundation with locked dependencies to ensure
consistent, reproducible deployments across all development and production environments.
"""

from .core import APIClient, HealthCheckResult, check_endpoint_health

__version__ = "0.1.0"
__all__ = ["APIClient", "HealthCheckResult", "check_endpoint_health", "__version__"]
