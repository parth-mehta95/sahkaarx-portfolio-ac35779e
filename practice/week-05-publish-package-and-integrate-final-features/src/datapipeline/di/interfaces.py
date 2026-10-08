"""Abstract interfaces and protocols for Dependency Injection."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IStorageService(ABC):
    """Storage abstraction for pipeline definitions, run logs, and datasets."""

    @abstractmethod
    def save(self, collection: str, item_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Persist data under a specific collection and identifier."""
        pass

    @abstractmethod
    def get(self, collection: str, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data by collection and identifier."""
        pass

    @abstractmethod
    def list(self, collection: str) -> List[Dict[str, Any]]:
        """List all items within a collection."""
        pass

    @abstractmethod
    def delete(self, collection: str, item_id: str) -> bool:
        """Delete an item by collection and identifier."""
        pass


class IAuthService(ABC):
    """Authentication and authorization abstraction."""

    @abstractmethod
    def generate_token(self, client_id: str, role: str = "operator") -> str:
        """Generate a secure authentication token for a client."""
        pass

    @abstractmethod
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate an authentication token and return the claims/payload if valid."""
        pass


class IMetricsCollector(ABC):
    """Metrics instrumentation abstraction."""

    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a metric counter."""
        pass

    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        pass

    @abstractmethod
    def get_metrics_snapshot(self) -> Dict[str, Any]:
        """Export current metrics summary."""
        pass


class IDataTransformer(ABC):
    """Data processing and transformation abstraction."""

    @abstractmethod
    def transform(self, records: List[Dict[str, Any]], operations: List[str]) -> List[Dict[str, Any]]:
        """Execute a series of transform operations on incoming records."""
        pass


class INotificationService(ABC):
    """Alert and notification dispatcher abstraction."""

    @abstractmethod
    def send_notification(self, channel: str, message: str, level: str = "INFO") -> bool:
        """Dispatch a notification to specified channel."""
        pass
