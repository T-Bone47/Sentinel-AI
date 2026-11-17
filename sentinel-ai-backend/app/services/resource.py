"""
Resource service layer: the thin business layer between routers and
repositories. For Phase 1 the "business logic" for a plain dataset table
is genuinely just pagination-bounds enforcement and 404 semantics, so it
stays small on purpose — the substantial services (dashboard, risk
investigation, graph) are separate modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import RowScope
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class ResourceSpec:
    """Declares how one dataset table is exposed over HTTP."""

    name: str            # url segment, e.g. "employees"
    model: Any
    pk: str
    schema: Any          # pydantic response DTO
    tag: str
    search_fields: tuple[str, ...] = ()
    filter_fields: tuple[str, ...] = ()
    sort_fields: tuple[str, ...] = ()
    description: str = ""
    # True when an enriched detail endpoint for this resource already exists in
    # detail_router.py — the factory then skips its generic /{id} route so the
    # path isn't declared twice in OpenAPI.
    has_custom_detail: bool = False


class ResourceService:
    def __init__(self, session: AsyncSession, spec: ResourceSpec) -> None:
        self.spec = spec
        self.repo = BaseRepository(session, spec.model, spec.pk)

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        filters: dict[str, Any],
        sort: str | None,
        scope: RowScope | None = None,
    ) -> tuple[list[Any], int]:
        page = max(1, page)
        page_size = max(1, min(page_size, settings.max_page_size))
        clean = {k: v for k, v in filters.items() if k in self.spec.filter_fields}
        return await self.repo.list(
            page=page,
            page_size=page_size,
            search=search,
            search_fields=self.spec.search_fields,
            filters=clean,
            sort=sort,
            sort_fields=self.spec.sort_fields,
            scope=scope,
        )

    async def get(self, identifier: str, scope: RowScope | None = None) -> Any:
        row = await self.repo.get(identifier)
        # A row outside the caller's scope is reported exactly like a missing
        # one, so the response does not confirm that the record exists.
        out_of_scope = (
            row is not None
            and scope is not None
            and (scope.value is None or getattr(row, scope.column) != scope.value)
        )
        if row is None or out_of_scope:
            raise HTTPException(
                status_code=404,
                detail=f"{self.spec.name[:-1] if self.spec.name.endswith('s') else self.spec.name} "
                       f"'{identifier}' not found",
            )
        return row
