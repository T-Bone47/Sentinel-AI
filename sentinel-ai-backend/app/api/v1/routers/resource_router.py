"""
Router factory. Turns one ResourceSpec into GET list + GET detail.

Filters are read from the raw query string and whitelisted against the
spec's `filter_fields`, rather than being declared as ~90 explicit FastAPI
Query params across 15 resources. The trade-off is that individual filters
don't appear as typed params in OpenAPI, so each endpoint's description
lists them explicitly instead — a deliberate hackathon-scope call, noted
in HANDOFF.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.routers.auth_router import require_permission
from app.core.config import settings
from app.core.permissions import RowScope, row_scope
from app.database.session import get_db
from app.models import AuditLog, User
from app.repositories.base import scope_condition
from app.schemas.common import page_meta
from app.services.resource import ResourceService, ResourceSpec

RESERVED = {"page", "page_size", "search", "sort", "date_from", "date_to", "min_risk_score"}


def _parse_dt(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            # Stored timestamps are UTC; a naive bound would be read as server-local time.
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def build_resource_router(spec: ResourceSpec) -> APIRouter:
    # One guard for both routes of this resource. At router level it protects
    # the routes; as a handler parameter (same cached dependency, so it runs
    # once) it hands the handler the user for row scoping.
    guard = require_permission(spec.name)
    router = APIRouter(dependencies=[Depends(guard)])
    filters_doc = ", ".join(f"`{f}`" for f in spec.filter_fields) or "none"
    sort_doc = ", ".join(f"`{f}`" for f in spec.sort_fields) or "primary key only"

    @router.get(
        f"/{spec.name}",
        tags=[spec.tag],
        summary=f"List {spec.name}",
        description=(
            f"{spec.description}\n\n"
            f"**Filters:** {filters_doc}\n\n"
            f"**Sort:** {sort_doc} (prefix with `-` for descending)\n\n"
            f"**Search:** matches {', '.join(spec.search_fields) or 'nothing'}"
        ),
        response_model=None,
    )
    async def list_resource(  # noqa: ANN202
        request: Request,
        page: int = Query(1, ge=1),
        page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
        search: str | None = Query(None, description="Case-insensitive partial match"),
        sort: str | None = Query(None, description="Column name; prefix `-` for descending"),
        db: AsyncSession = Depends(get_db),
        user: User = Depends(guard),
    ) -> dict[str, Any]:
        filters = {
            key: values[0] if len(values) == 1 else values
            for key in request.query_params.keys()
            if key not in RESERVED
            for values in [request.query_params.getlist(key)]
        }
        service = ResourceService(db, spec)
        scope = row_scope(user.role, user.employee_id, spec.name)

        # Audit logs get date-range + risk-score filters on top of the generic
        # ones: 10,000 rows is the one dataset where the frontend genuinely
        # needs range queries, not just equality.
        if spec.model is AuditLog:
            rows, total = await _list_audit_logs(db, request, page, page_size, search, sort, filters, scope)
        else:
            rows, total = await service.list(
                page=page, page_size=page_size, search=search, filters=filters, sort=sort, scope=scope
            )

        return {
            "data": [spec.schema.model_validate(r).model_dump(mode="json") for r in rows],
            "meta": page_meta(page, page_size, total).model_dump(),
            "error": None,
        }

    if spec.has_custom_detail:
        # detail_router.py owns this path with a richer, relationship-aware
        # response. Registering a second handler here would only shadow it
        # in the schema.
        return router

    @router.get(
        f"/{spec.name}/{{identifier}}",
        tags=[spec.tag],
        summary=f"Get one {spec.name} record by ID",
        response_model=None,
    )
    async def get_resource(
        identifier: str, db: AsyncSession = Depends(get_db), user: User = Depends(guard)
    ) -> dict[str, Any]:
        service = ResourceService(db, spec)
        row = await service.get(identifier, scope=row_scope(user.role, user.employee_id, spec.name))
        return {"data": spec.schema.model_validate(row).model_dump(mode="json"), "error": None}

    return router


async def _list_audit_logs(
    db: AsyncSession,
    request: Request,
    page: int,
    page_size: int,
    search: str | None,
    sort: str | None,
    filters: dict[str, Any],
    scope: RowScope | None = None,
) -> tuple[list[Any], int]:
    """Audit logs need range filtering the generic repository doesn't do."""
    from app.api.v1.resources import BY_NAME

    spec = BY_NAME["audit-logs"]
    # No role holds a row scope on audit logs today; applied anyway so that
    # granting one later cannot silently expose every row through this path.
    conditions = [scope_condition(AuditLog, scope)] if scope is not None else []
    for name, value in filters.items():
        if name not in spec.filter_fields:
            continue
        column = getattr(AuditLog, name, None)
        if column is not None and value is not None:
            conditions.append(column == value)

    if (raw := request.query_params.get("date_from")) and (parsed := _parse_dt(raw)):
        conditions.append(AuditLog.timestamp >= parsed)
    if (raw := request.query_params.get("date_to")) and (parsed := _parse_dt(raw)):
        conditions.append(AuditLog.timestamp <= parsed)
    if raw := request.query_params.get("min_risk_score"):
        try:
            conditions.append(AuditLog.risk_score >= int(raw))
        except ValueError:
            pass
    if search:
        from sqlalchemy import or_

        conditions.append(
            or_(*[getattr(AuditLog, f).ilike(f"%{search}%") for f in spec.search_fields])
        )

    where = and_(*conditions) if conditions else None
    count_stmt = select(func.count()).select_from(AuditLog)
    stmt = select(AuditLog)
    if where is not None:
        count_stmt = count_stmt.where(where)
        stmt = stmt.where(where)

    total = (await db.execute(count_stmt)).scalar_one()

    descending = bool(sort and sort.startswith("-"))
    sort_name = (sort or "-timestamp").lstrip("-+")
    if sort_name not in spec.sort_fields:
        sort_name, descending = "timestamp", True
    column = getattr(AuditLog, sort_name)
    stmt = stmt.order_by(column.desc() if descending else column.asc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total
