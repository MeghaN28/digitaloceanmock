from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.metrics_repository import MetricsRepository
from app.schemas.metrics import MetricPayload, MetricQuery
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/v1", tags=["metrics"])


def get_metrics_service(db: Session = Depends(get_db)) -> MetricsService:
    repository = MetricsRepository(db)
    return MetricsService(repository)


def success_response(data):
    return {"success": True, "data": data}


@router.post("/apps/metrics")
def ingest_metric(
    payload: MetricPayload,
    response: Response,
    service: MetricsService = Depends(get_metrics_service),
):
    try:
        result = service.ingest_metric(payload.model_dump())
        response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
        record = result.record
        return success_response(
            {
                "id": record.id,
                "event_id": record.event_id,
                "app_id": record.app_id,
                "environment": record.environment,
                "metric": record.metric,
                "value": record.value,
                "timestamp": record.timestamp.isoformat(),
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": str(exc), "code": "ingest_error"}) from exc


@router.get("/apps/{app_id}/metrics")
def get_application_metrics(
    app_id: str,
    metric: str = Query(..., description="Metric name to retrieve"),
    environment: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None, alias="from"),
    end_time: datetime | None = Query(default=None, alias="to"),
    service: MetricsService = Depends(get_metrics_service),
):
    try:
        query = MetricQuery(
            metric=metric,
            environment=environment,
            start_time=start_time,
            end_time=end_time,
        )
        records = service.get_metrics(
            app_id,
            metric=query.metric,
            environment=query.environment,
            start_time=query.start_time,
            end_time=query.end_time,
        )
        payload = {
            "app_id": app_id,
            "metric": query.metric,
            "environment": query.environment,
            "from": query.start_time.isoformat() if query.start_time else None,
            "to": query.end_time.isoformat() if query.end_time else None,
            "count": len(records),
            "items": [
                {
                    "id": item.id,
                    "app_id": item.app_id,
                    "environment": item.environment,
                    "metric": item.metric,
                    "value": item.value,
                    "timestamp": item.timestamp.isoformat(),
                }
                for item in records
            ],
        }
        return success_response(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": exc.errors()[0].get("msg", "Invalid query parameters"), "code": "query_validation_error"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc), "code": "query_validation_error"}) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": str(exc), "code": "query_error"}) from exc


@router.get("/apps/{app_id}/aggregate")
def get_application_aggregate(
    app_id: str,
    metric: str = Query(..., description="Metric name to aggregate"),
    environment: str | None = Query(default=None),
    start_time: datetime | None = Query(default=None, alias="from"),
    end_time: datetime | None = Query(default=None, alias="to"),
    service: MetricsService = Depends(get_metrics_service),
):
    try:
        query = MetricQuery(
            metric=metric,
            environment=environment,
            start_time=start_time,
            end_time=end_time,
        )
        result = service.aggregate_metrics(
            app_id,
            metric=query.metric,
            environment=query.environment,
            start_time=query.start_time,
            end_time=query.end_time,
        )
        return success_response(result.model_dump(by_alias=True))
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": exc.errors()[0].get("msg", "Invalid aggregate query"), "code": "aggregate_validation_error"}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": str(exc), "code": "aggregate_validation_error"}) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"message": str(exc), "code": "aggregate_error"}) from exc
