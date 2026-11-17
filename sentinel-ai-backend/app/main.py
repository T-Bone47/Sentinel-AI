"""
FastAPI application factory.

Only the foundation required for a coherent, importable, runnable app:
health check + CORS + a global exception handler + OpenAPI metadata.
Routers are added incrementally as they're built — see
IMPLEMENTATION_STATUS.md for what's wired in vs. still pending.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.resources import RESOURCES
from app.api.v1.routers import (
    auth_router,
    dashboard_router,
    detail_router,
    detections_router,
    events_router,
    intelligence_router,
)
from app.api.v1.routers.auth_router import get_current_user
from fastapi import Depends
from app.api.v1.routers.resource_router import build_resource_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinel")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sentinel AI backend starting — env=%s", settings.environment)
    yield
    logger.info("Sentinel AI backend shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Sentinel AI — From Compliance Documents to Continuous Trust. Phase 1: backend foundation + dataset integration.",
        lifespan=lifespan,
        # R7: the schema maps every route; publish it only where developers need it.
        docs_url="/api/docs" if settings.is_local else None,
        redoc_url="/api/redoc" if settings.is_local else None,
        openapi_url="/api/openapi.json" if settings.is_local else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Keep error responses in the same {data, error} envelope as successes."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)},
            },
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field path and reason only. Pydantic's full error objects echo the
        # submitted input, which on /auth/login would include the password.
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in exc.errors()
        )
        return JSONResponse(
            status_code=422,
            content={"data": None, "error": {"code": "validation_error", "message": problems}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"data": None, "error": {"code": "internal_error", "message": "An unexpected error occurred."}},
        )

    @app.get("/api/v1/health", tags=["system"])
    async def health() -> dict:
        return {"data": {"status": "ok", "service": settings.app_name, "version": settings.app_version}, "error": None}

    # --- Routers ---------------------------------------------------------
    # Order matters: the enriched detail routes (/risks/{id} etc.) must be
    # registered BEFORE the generic resource routes, or the generic
    # `/{identifier}` handler would shadow them.
    app.include_router(auth_router.router, prefix="/api/v1/auth")
    app.include_router(dashboard_router.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.include_router(intelligence_router.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.include_router(detail_router.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.include_router(events_router.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])
    app.include_router(detections_router.router, prefix="/api/v1", dependencies=[Depends(get_current_user)])

    for spec in RESOURCES:
        app.include_router(build_resource_router(spec), prefix="/api/v1", dependencies=[Depends(get_current_user)])

    return app


app = create_app()
