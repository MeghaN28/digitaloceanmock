from datetime import datetime
from statistics import mean

from app.db.models import DeploymentMetric
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.metrics import AggregatedMetric


class MetricsService:
    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def ingest_metric(self, payload: dict) -> DeploymentMetric:
        metric_record = DeploymentMetric(
            app_id=payload["app_id"],
            environment=payload["environment"],
            metric=payload["metric"],
            value=float(payload["value"]),
            timestamp=payload["timestamp"],
        )
        return self.repository.create_metric(metric_record)

    def get_metrics(
        self,
        app_id: str,
        *,
        metric: str,
        environment: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[DeploymentMetric]:
        return self.repository.list_metrics(
            app_id,
            metric=metric,
            environment=environment,
            start_time=start_time,
            end_time=end_time,
        )

    def aggregate_metrics(
        self,
        app_id: str,
        *,
        metric: str,
        environment: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> AggregatedMetric:
        metrics = self.get_metrics(
            app_id,
            metric=metric,
            environment=environment,
            start_time=start_time,
            end_time=end_time,
        )
        if not metrics:
            raise ValueError("No metrics found for the requested criteria")

        values = [item.value for item in metrics]
        aggregate = AggregatedMetric(
            app_id=app_id,
            metric=metric,
            environment=environment,
            from_time=start_time or metrics[0].timestamp,
            to_time=end_time or metrics[-1].timestamp,
            count=len(values),
            average=round(mean(values), 2),
            minimum=round(min(values), 2),
            maximum=round(max(values), 2),
        )

        if metric in {"cpu_usage", "memory_usage"}:
            aggregate.total = None
        else:
            aggregate.total = round(sum(values), 2)

        return aggregate
