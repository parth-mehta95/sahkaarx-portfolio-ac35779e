"""Authentication and access control service."""

from typing import Any, Dict, Optional
from datapipeline.di.interfaces import IAuthService, IMetricsCollector


class AuthService:
    """Service handling credential verification, token issuance, and authorization checks."""

    # Pre-provisioned API credentials (in production, loaded from secrets manager or DB)
    CLIENT_CREDENTIALS = {
        "admin-client": "secret-admin-token-key-prod-99",
        "ingest-worker": "worker-token-key-secure-88",
        "readonly-viewer": "viewer-token-key-audit-77",
    }

    ROLE_PERMISSIONS = {
        "admin": ["read", "write", "execute", "admin"],
        "operator": ["read", "write", "execute"],
        "viewer": ["read"],
    }

    def __init__(self, auth_provider: IAuthService, metrics: IMetricsCollector):
        self.auth_provider = auth_provider
        self.metrics = metrics

    def authenticate(self, client_id: str, client_secret: str) -> Optional[str]:
        """Verify client credentials and return signed authorization token."""
        expected = self.CLIENT_CREDENTIALS.get(client_id)
        if expected is None or expected != client_secret:
            self.metrics.increment_counter("auth_failures_total", 1, {"client_id": client_id})
            return None

        role = "admin" if "admin" in client_id else "operator"
        token = self.auth_provider.generate_token(client_id, role=role)
        self.metrics.increment_counter("auth_success_total", 1, {"client_id": client_id})
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify bearer token validity and claims."""
        return self.auth_provider.validate_token(token)
