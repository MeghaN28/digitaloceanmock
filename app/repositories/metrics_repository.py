from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DeploymentMetric


class MetricsRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_metric(self, metric_record: DeploymentMetric) -> DeploymentMetric:
        self.db.add(metric_record)
        self.db.commit()
        self.db.refresh(metric_record)
        return metric_record

    def list_metrics(
        self,
        app_id: str,
        *,
        metric: str | None = None,
        environment: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[DeploymentMetric]:
        stmt = select(DeploymentMetric).where(DeploymentMetric.app_id == app_id)

        if metric is not None:
            stmt = stmt.where(DeploymentMetric.metric == metric)
        if environment is not None:
            stmt = stmt.where(DeploymentMetric.environment == environment)
        if start_time is not None:
            stmt = stmt.where(DeploymentMetric.timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(DeploymentMetric.timestamp <= end_time)

        stmt = stmt.order_by(DeploymentMetric.timestamp.asc())
        return self.db.execute(stmt).scalars().all()
