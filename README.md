# Deployment Metrics Service

A FastAPI-based service for ingesting application deployment metrics and returning aggregated insights by app, environment, metric, and time range.

## Project Idea

This project models a metrics ingestion service inspired by DigitalOcean-style deployment monitoring. It allows clients to:

- submit runtime metric events
- query stored metrics for a given app and time range
- aggregate values by metric type and environment
- maintain a clean, layered, testable backend structure

The service is designed to support production-style concerns such as:

- environment-based configuration
- validation of inputs
- structured success/error responses
- database-backed persistence
- indexing for common query patterns
- containerized deployment readiness

## Business Requirements

### API behavior

The service supports the following behavior:

1. Receive metric events via POST
2. Persist them to the database
3. Retrieve metrics for an app within a time window
4. Aggregate values for a metric based on type and environment

### Metric rules

- CPU and memory metrics are percentage-based values and must be in the range 0 to 100
- Request and error counts are numeric counters and can be greater than or equal to 0
- Aggregation logic differs by metric type

### Response contract

All endpoints use a consistent response envelope:

```json
{
  "success": true,
  "data": {
    ...
  }
}
```

Error responses follow a consistent structure:

```json
{
  "success": false,
  "error": {
    "message": "...",
    "code": "...",
    "details": {}
  }
}
```

## Architecture

The app follows a layered and decoupled design:

- config layer for environment-driven settings
- database layer for engine and session management
- schema layer for payload validation and DTOs
- repository layer for persistence operations
- service layer for business logic
- API layer for REST endpoints
- test layer for API verification

### Main folders

- `app/` – application source
- `app/api/v1/routes/` – routing and endpoint handlers
- `app/config.py` – runtime settings and environment resolution
- `app/db/` – SQLAlchemy models and session config
- `app/repositories/` – DB access layer
- `app/services/` – business logic
- `app/schemas/` – request/query validation and response schemas
- `tests/` – API and validation tests

## API Endpoints

### Health check

GET `/healthz`

Returns a simple service health response.

### Ingest a metric

POST `/v1/apps/metrics`

Request payload:

```json
{
  "app_id": "app-123",
  "environment": "production",
  "metric": "cpu_usage",
  "value": 72.5,
  "timestamp": "2026-09-15T16:30:00Z"
}
```

Supported metrics:

- `cpu_usage`
- `memory_usage`
- `request_count`
- `error_count`

Supported environments:

- `development`
- `staging`
- `production`

### Get metrics for an app

GET `/v1/apps/{app_id}/metrics`

Query params:

- `metric`
- `environment`
- `from`
- `to`

### Aggregate metrics

GET `/v1/apps/{app_id}/aggregate`

Query params:

- `metric`
- `environment`
- `from`
- `to`

Aggregation differs by metric type:

- `cpu_usage`, `memory_usage` → average, minimum, maximum, no total
- `request_count`, `error_count` → average, minimum, maximum, total

## Data Model

The project stores metrics in a relational table with relevant fields:

- `id`
- `app_id`
- `environment`
- `metric`
- `value`
- `timestamp`

Indexes are created for efficient lookup by app, environment, metric, and timestamp.

## Configuration

The app is configured through environment variables.

### Local development defaults

By default, the project uses SQLite for local dev so it can run without a local Postgres server.

### Production deployment

When `DB_HOST`, `DB_USER`, and `DB_NAME` are set, the app uses PostgreSQL automatically.

### Example env values

```env
APP_NAME=deployment-metrics-service
APP_ENV=production
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000
DB_HOST=your-db-host
DB_PORT=25060
DB_NAME=defaultdb
DB_USER=doadmin
DB_PASSWORD=your-db-password
DB_SSLMODE=require
LOG_LEVEL=INFO
```

The credentials should be managed through deployment secret/config settings and never committed to source control.

## Local Setup

### Prerequisites

- Python 3.13+
- pip

### Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the app locally

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Test the app

```bash
pytest -q
```

## Docker

The project includes a Dockerfile for containerized deployment.

```bash
docker build -t deployment-metrics-service .
docker run -p 8000:8000 deployment-metrics-service
```

## DigitalOcean App Platform

The app is designed for deployment on DigitalOcean App Platform using:

- a GitHub repository
- a web service on port 8000
- environment variables for runtime configuration
- PostgreSQL database connection details for production

Recommended deployment pattern:

- create a PostgreSQL database in DigitalOcean
- attach it to the app as environment variables or a managed database reference
- use secrets for the DB password
- deploy the app from GitHub

## Validation and Testing

The project includes end-to-end API tests covering:

- health endpoint
- valid metric ingestion
- invalid payload handling
- invalid environment and metric values
- invalid percentage values
- negative counter values
- aggregation behavior for percentage vs count metrics
- empty result handling
- invalid time-range validation

## Example Input Data

```json
{
  "app_id": "app-123",
  "environment": "production",
  "metric": "cpu_usage",
  "value": 72.5,
  "timestamp": "2026-09-15T16:30:00Z"
}
```

```json
{
  "app_id": "app-123",
  "environment": "production",
  "metric": "memory_usage",
  "value": 81.2,
  "timestamp": "2026-09-15T16:31:00Z"
}
```

```json
{
  "app_id": "app-123",
  "environment": "production",
  "metric": "request_count",
  "value": 128,
  "timestamp": "2026-09-15T16:32:00Z"
}
```

```json
{
  "app_id": "app-123",
  "environment": "production",
  "metric": "error_count",
  "value": 4,
  "timestamp": "2026-09-15T16:33:00Z"
}
```

## Notes

This project intentionally keeps a clean separation between:

- environment values
- DB configuration
- business logic
- persistence code
- API layer

That separation reduces tight coupling and makes the app easier to test, reuse, and deploy.

## Summary

This project demonstrates a production-minded FastAPI service for deployment metrics ingestion and aggregation, covering:

- API design
- DB persistence
- validation
- aggregation logic
- environment-based config
- deployment readiness
- test coverage

It is built to support both local development and production deployment without exposing sensitive credentials in source control.
