"""Domain schemas, validation logic, and data transfer models."""

from dataclasses import dataclass, field, asdict
from enum import Enum
import re
import time
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Raised when request payload or configuration fails schema validation."""
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or [message]


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class PipelineConfig:
    pipeline_id: str
    name: str
    description: str = ""
    transform_operations: List[str] = field(default_factory=list)
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300

    def validate(self) -> None:
        errors = []
        if not self.pipeline_id or not re.match(r"^[a-zA-Z0-9_\-]+$", self.pipeline_id):
            errors.append("pipeline_id must be non-empty and alphanumeric (allowing dashes and underscores)")
        if not self.name or len(self.name.strip()) < 3:
            errors.append("name must be at least 3 characters long")
        if self.max_retries < 0 or self.max_retries > 10:
            errors.append("max_retries must be between 0 and 10")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 3600:
            errors.append("timeout_seconds must be between 1 and 3600")

        valid_ops = {"strip_whitespace", "lowercase_keys", "hash_pii", "add_timestamp"}
        for op in self.transform_operations:
            if op not in valid_ops:
                errors.append(f"Invalid transform operation '{op}'. Supported: {sorted(valid_ops)}")

        if errors:
            raise ValidationError("Pipeline configuration validation failed", errors)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PipelineConfig":
        if not isinstance(data, dict):
            raise ValidationError("Payload must be a JSON dictionary")
        inst = cls(
            pipeline_id=str(data.get("pipeline_id", "")).strip(),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")),
            transform_operations=list(data.get("transform_operations", [])),
            enabled=bool(data.get("enabled", True)),
            max_retries=int(data.get("max_retries", 3)),
            timeout_seconds=int(data.get("timeout_seconds", 300)),
        )
        inst.validate()
        return inst


@dataclass
class DatasetPayload:
    dataset_id: str
    records: List[Dict[str, Any]]
    schema_version: str = "1.0"

    def validate(self) -> None:
        errors = []
        if not self.dataset_id or not re.match(r"^[a-zA-Z0-9_\-]+$", self.dataset_id):
            errors.append("dataset_id must be non-empty and alphanumeric")
        if not isinstance(self.records, list):
            errors.append("records must be a list")
        elif len(self.records) == 0:
            errors.append("records list cannot be empty")
        else:
            for idx, r in enumerate(self.records):
                if not isinstance(r, dict):
                    errors.append(f"records[{idx}] must be a dictionary")
                    break

        if errors:
            raise ValidationError("Dataset payload validation failed", errors)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetPayload":
        if not isinstance(data, dict):
            raise ValidationError("Payload must be a JSON dictionary")
        inst = cls(
            dataset_id=str(data.get("dataset_id", "")).strip(),
            records=list(data.get("records", [])),
            schema_version=str(data.get("schema_version", "1.0")),
        )
        inst.validate()
        return inst


@dataclass
class APIResponse:
    success: bool
    data: Optional[Any] = None
    errors: Optional[List[str]] = None
    status_code: int = 200
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
