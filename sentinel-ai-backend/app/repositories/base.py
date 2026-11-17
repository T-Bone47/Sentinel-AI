"""
Generic async data-access layer.

One repository class serves every dataset table: they all follow the same
shape (natural-key PK, flat columns, list + get-by-id). Per-resource
behaviour is expressed as data (which columns are searchable/filterable/
sortable) rather than as a subclass per table, which would be ~15 near
identical files. Anything genuinely bespoke — the dashboard aggregates,
the risk investigation chain, the org graph — lives in its own service
instead, where the SQL actually differs.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


def scope_condition(model: Any, scope: Any):
    """SQL condition for a `permissions.RowScope`. An account with no linked
    record (`value is None`) matches nothing, never "rows where it is NULL"."""
    return false() if scope.value is None else getattr(model, scope.column) == scope.value


class BaseRepository:
    def __init__(self, session: AsyncSession, model: Any, pk: str) -> None:
        self.session = session
        self.model = model
        self.pk = pk

    def _column(self, name: str):
        return getattr(self.model, name, None)

    def _apply_filters(self, stmt, filters: dict[str, Any]):
        for name, value in filters.items():
            column = self._column(name)
            if column is None or value is None:
                continue
            if isinstance(value, list):
                stmt = stmt.where(column.in_(value))
            elif isinstance(value, str) and value.lower() in ("true", "false"):
                stmt = stmt.where(column.is_(value.lower() == "true"))
            else:
                stmt = stmt.where(column == value)
        return stmt

    def _apply_search(self, stmt, search: str | None, fields: tuple[str, ...]):
        if not search or not fields:
            return stmt
        clauses = []
        for name in fields:
            column = self._column(name)
            if column is not None:
                clauses.append(column.ilike(f"%{search}%"))
        return stmt.where(or_(*clauses)) if clauses else stmt

    def _apply_sort(self, stmt, sort: str | None, allowed: tuple[str, ...]):
        if not sort:
            return stmt.order_by(getattr(self.model, self.pk))
        descending = sort.startswith("-")
        name = sort.lstrip("-+")
        if allowed and name not in allowed:
            return stmt.order_by(getattr(self.model, self.pk))
        column = self._column(name)
        if column is None:
            return stmt.order_by(getattr(self.model, self.pk))
        return stmt.order_by(column.desc() if descending else column.asc())

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str | None = None,
        search_fields: tuple[str, ...] = (),
        filters: dict[str, Any] | None = None,
        sort: str | None = None,
        sort_fields: tuple[str, ...] = (),
        scope: Any = None,
    ) -> tuple[list[Any], int]:
        filters = filters or {}

        stmt = select(self.model)
        if scope is not None:
            # Authorization, not a filter: applied first and independently of
            # anything the caller sent, so no filter or search can widen it.
            stmt = stmt.where(scope_condition(self.model, scope))
        stmt = self._apply_filters(stmt, filters)
        stmt = self._apply_search(stmt, search, search_fields)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = self._apply_sort(stmt, sort, sort_fields)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total

    async def get(self, identifier: str) -> Any | None:
        stmt = select(self.model).where(getattr(self.model, self.pk) == identifier)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        stmt = self._apply_filters(stmt, filters or {})
        return (await self.session.execute(stmt)).scalar_one()
