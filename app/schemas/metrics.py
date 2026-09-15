from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

METRIC_TYPES = {"cpu_usage", "memory_usage", "request_count", "error_count"}
VALID_ENVIRONMENTS = {"production", "staging", "development"}


class MetricPayload(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=255)
    app_id: str = Field(..., min_length=1, max_length=255)
    environment: Literal["production", "staging", "development"]
    metric: str = Field(..., min_length=1, max_length=64)
    value: float = Field(..., ge=0)
    timestamp: datetime

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, event_id: str) -> str:
        normalized = event_id.strip()
        if not normalized:
            raise ValueError("event_id cannot be blank")
        return normalized

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, metric: str) -> str:
        normalized = metric.strip()
        if normalized not in METRIC_TYPES:
            raise ValueError(
                "Unsupported metric. Supported values: cpu_usage, memory_usage, request_count, error_count"
            )
        return normalized

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, environment: str) -> str:
        normalized = environment.strip().lower()
        if normalized not in VALID_ENVIRONMENTS:
            raise ValueError("Environment must be one of: production, staging, development")
        return normalized

    @field_validator("value")
    @classmethod
    def validate_value_by_metric(cls, value: float, info):
        metric = info.data.get("metric")
        if metric in {"cpu_usage", "memory_usage"} and not 0 <= value <= 100:
            raise ValueError("cpu_usage and memory_usage must be between 0 and 100 inclusive")
        if metric in {"request_count", "error_count"} and value < 0:
            raise ValueError("request_count and error_count must be greater than or equal to 0")
        return value


class MetricQuery(BaseModel):
    metric: str = Field(..., min_length=1, max_length=64)
    start_time: datetime | None = None
    end_time: datetime | None = None
    environment: Literal["production", "staging", "development"] | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, metric: str) -> str:
        normalized = metric.strip()
        if normalized not in METRIC_TYPES:
            raise ValueError(
                "Unsupported metric. Supported values: cpu_usage, memory_usage, request_count, error_count"
            )
        return normalized

    @model_validator(mode="after")
    def validate_start_end(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be earlier than or equal to end_time")
        return self


class MetricRecord(BaseModel):
    id: int
    event_id: str
    app_id: str
    environment: str
    metric: str
    value: float
    timestamp: datetime
    created_at: datetime


class AggregatedMetric(BaseModel):
    app_id: str
    metric: str
    environment: str | None = None
    from_time: datetime = Field(alias="from")
    to_time: datetime = Field(alias="to")
    count: int
    average: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    total: float | None = None

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
