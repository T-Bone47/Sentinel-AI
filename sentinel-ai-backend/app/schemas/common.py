"""Shared response envelope + pagination, used by every endpoint."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for every response DTO read straight off a SQLAlchemy row."""

    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class ErrorBody(BaseModel):
    code: str
    message: str


class Page(BaseModel, Generic[T]):
    """List response: {"data": [...], "meta": {...}, "error": null}"""

    data: list[T]
    meta: PageMeta
    error: ErrorBody | None = None


class Item(BaseModel, Generic[T]):
    """Detail response: {"data": {...}, "error": null}"""

    data: T
    error: ErrorBody | None = None


def page_meta(page: int, page_size: int, total: int) -> PageMeta:
    return PageMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=(total + page_size - 1) // page_size if page_size else 0,
    )
