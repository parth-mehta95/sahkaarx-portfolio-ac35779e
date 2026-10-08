"""Pipeline management business service with injected dependencies."""

import time
from typing import Any, Dict, List, Optional

from datapipeline.di.interfaces import (
    IDataTransformer,
    IMetricsCollector,
    INotificationService,
    IStorageService,
)
from datapipeline.models import DatasetPayload, PipelineConfig, ValidationError


class PipelineService:
    """Core domain service for orchestrating pipelines and transforming datasets."""

    def __init__(
        self,
        storage: IStorageService,
        transformer: IDataTransformer,
        metrics: IMetricsCollector,
        notifications: INotificationService,
    ):
        self.storage = storage
        self.transformer = transformer
        self.metrics = metrics
        self.notifications = notifications

    def register_pipeline(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and persist a new pipeline configuration."""
        config = PipelineConfig.from_dict(config_data)
        saved = self.storage.save("pipelines", config.pipeline_id, config.to_dict())
        self.metrics.increment_counter("pipelines_registered_total", 1)
        self.notifications.send_notification("audit", f"Pipeline registered: {config.pipeline_id}")
        return saved

    def get_pipeline(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Fetch pipeline configuration by ID."""
        return self.storage.get("pipelines", pipeline_id)

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """List all active pipelines."""
        return self.storage.list("pipelines")

    def run_pipeline(
        self,
        pipeline_id: str,
        input_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Execute a pipeline with configured transformation operations."""
        pipeline_raw = self.get_pipeline(pipeline_id)
        if not pipeline_raw:
            raise ValidationError(f"Pipeline '{pipeline_id}' not found")

        config = PipelineConfig.from_dict(pipeline_raw)
        if not config.enabled:
            raise ValidationError(f"Pipeline '{pipeline_id}' is disabled")

        start_time = time.time()
        self.metrics.increment_counter("pipeline_runs_total", 1, {"pipeline_id": pipeline_id})

        records = input_data or []
        try:
            transformed = self.transformer.transform(records, config.transform_operations)
            duration = time.time() - start_time
            
            run_result = {
                "pipeline_id": pipeline_id,
                "status": "success",
                "records_in": len(records),
                "records_out": len(transformed),
                "duration_seconds": round(duration, 4),
                "output": transformed,
                "timestamp": time.time(),
            }
            
            run_id = f"{pipeline_id}_{int(time.time() * 1000)}"
            self.storage.save("runs", run_id, run_result)
            self.metrics.record_gauge("last_pipeline_duration_seconds", duration)
            self.metrics.increment_counter("pipeline_success_total", 1)
            
            return run_result

        except Exception as ex:
            self.metrics.increment_counter("pipeline_failure_total", 1)
            self.notifications.send_notification(
                "alerts",
                f"Pipeline {pipeline_id} execution failed: {str(ex)}",
                level="ERROR",
            )
            raise
