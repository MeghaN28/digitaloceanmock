from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.models import DeploymentMetric  # noqa: F401
from app.db.session import engine

settings = get_settings()
configure_logging()


def build_success_response(data):
    return {"success": True, "data": data}


def build_error_response(message: str, code: str = "internal_error", details: dict | None = None):
    return {"success": False, "error": {"message": message, "code": code, "details": details or {}}}


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Deployment Metrics Ingestion Service",
    description="REST API for receiving and aggregating application deployment metrics.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/healthz")
def health_check() -> dict:
    return build_success_response(
        {
            "status": "ok",
            "service": settings.app_name,
            "environment": settings.app_env,
        }
    )


from app.api.v1.routes.metrics import router as metrics_router

app.include_router(metrics_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    payload = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    message = payload.get("message", payload.get("detail", str(exc.detail)))
    code = payload.get("code", "http_exception")
    details = payload.get("details", {})
    return JSONResponse(status_code=exc.status_code, content=build_error_response(message, code, details))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    message = errors[0].get("msg", "Validation error") if errors else "Validation error"
    details = {
        "fields": [
            {
                "loc": item.get("loc", []),
                "msg": item.get("msg", "Validation error"),
                "type": item.get("type", "validation_error"),
            }
            for item in errors
        ]
    }
    return JSONResponse(status_code=422, content=build_error_response(message, "validation_error", details))


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content=build_error_response("Internal server error", "internal_error", {}))
