from dataclasses import dataclass
from datetime import datetime
from statistics import mean

from app.db.models import DeploymentMetric
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.metrics import AggregatedMetric


@dataclass
class IngestResult:
    record: DeploymentMetric
    created: bool


class MetricsService:
    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def ingest_metric(self, payload: dict) -> IngestResult:
        event_id = str(payload["event_id"]).strip()
        existing = self.repository.get_by_event_id(event_id)
        if existing is not None:
            return IngestResult(record=existing, created=False)

        metric_record = DeploymentMetric(
            event_id=event_id,
            app_id=payload["app_id"],
            environment=payload["environment"],
            metric=payload["metric"],
            value=float(payload["value"]),
            timestamp=payload["timestamp"],
        )
        created_record = self.repository.create_metric(metric_record)
        return IngestResult(record=created_record, created=True)

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
            return AggregatedMetric(
                app_id=app_id,
                metric=metric,
                environment=environment,
                from_time=start_time or datetime.min.replace(tzinfo=None),
                to_time=end_time or datetime.min.replace(tzinfo=None),
                count=0,
                average=None,
                minimum=None,
                maximum=None,
                total=None,
            )

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
