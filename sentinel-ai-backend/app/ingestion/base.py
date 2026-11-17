"""
Generic, dataset-agnostic CSV ingestor.

Pipeline per dataset:  read -> validate -> transform -> upsert -> log

Design decisions worth knowing before you change anything here:

* **Sync SQLAlchemy, not async.** Ingestion is a batch CLI, not a request
  path. `psycopg` sync + one transaction per dataset is simpler to reason
  about and to make transactional than juggling an event loop, and it
  keeps the async engine reserved for the API layer.

* **Idempotency comes from the natural key.** Every dataset table's PK is
  the real source ID, so `INSERT ... ON CONFLICT (pk) DO UPDATE` makes a
  re-run a no-op-shaped UPDATE rather than a duplicate. Re-running the
  whole pipeline twice must not change row counts — that is the single
  most important property this module has, and it is covered by a test.

* **Inserted vs. updated is measured, not guessed.** Postgres exposes
  `xmax = 0` on the RETURNING row for a genuine INSERT; a conflict-update
  leaves xmax non-zero. That is where the per-dataset numbers come from.

* **FK-aware, fail-soft.** Parent keys are loaded into memory before the
  batch. A row pointing at a missing parent is nulled (nullable FK) or
  skipped (non-nullable) with a log row — never inserted blind, because a
  mid-transaction FK violation would roll back the whole dataset.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.ingestion.configs.registry import DatasetConfig, FieldSpec
from app.models.enums import IngestionLogLevel, IngestionStatus
from app.models.ingestion import IngestionJob, IngestionLog

logger = logging.getLogger("sentinel.ingestion")

TRUE_VALUES = {"true", "t", "yes", "y", "1"}
FALSE_VALUES = {"false", "f", "no", "n", "0"}

DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y")
DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%SZ",
)

# How many log rows to persist per dataset. Ingestion logs are a debugging
# aid, not an audit trail of every row — an unbounded write here would be
# slower than the ingest itself on a bad file.
MAX_PERSISTED_LOGS = 200


class ValidationError(Exception):
    """A row-level problem that makes the row unusable."""


@dataclass
class DatasetResult:
    dataset: str
    source_file: str
    rows_read: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    warnings: int = 0
    job_id: str | None = None
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.errors == 0


# --------------------------------------------------------------------------
# Value coercion
# --------------------------------------------------------------------------

def _coerce(raw: str | None, spec: FieldSpec) -> Any:
    if raw is None:
        value = None
    else:
        value = raw.strip()
        if value == "":
            value = None

    if value is None:
        if spec.nullable:
            return None
        raise ValidationError(f"'{spec.source}' is required but empty")

    if spec.kind == "str":
        return value

    if spec.kind == "int":
        try:
            return int(float(value))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"'{spec.source}'={value!r} is not an integer") from exc

    if spec.kind == "bool":
        low = value.lower()
        if low in TRUE_VALUES:
            return True
        if low in FALSE_VALUES:
            return False
        raise ValidationError(f"'{spec.source}'={value!r} is not a boolean")

    if spec.kind == "date":
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValidationError(f"'{spec.source}'={value!r} is not a parseable date")

    if spec.kind == "datetime":
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        raise ValidationError(f"'{spec.source}'={value!r} is not a parseable timestamp")

    raise ValidationError(f"unknown field kind {spec.kind!r} for '{spec.source}'")


# --------------------------------------------------------------------------
# Ingestor
# --------------------------------------------------------------------------

class DatasetIngestor:
    def __init__(self, session: Session, datasets_dir: Path, chunk_size: int = 1000) -> None:
        self.session = session
        self.datasets_dir = Path(datasets_dir)
        self.chunk_size = chunk_size

    # -- helpers ----------------------------------------------------------

    def _existing_keys(self, table: str, column: str) -> set[str]:
        rows = self.session.execute(text(f"SELECT {column} FROM {table}"))  # noqa: S608 - identifiers come from our own configs, never user input
        return {r[0] for r in rows if r[0] is not None}

    def _log(
        self,
        job: IngestionJob,
        result: DatasetResult,
        level: IngestionLogLevel,
        message: str,
        row_number: int | None = None,
        raw_row: dict | None = None,
    ) -> None:
        result.messages.append(f"[{level.value}] row {row_number}: {message}" if row_number else f"[{level.value}] {message}")
        if len(result.messages) <= MAX_PERSISTED_LOGS:
            self.session.add(
                IngestionLog(
                    job_id=job.id,
                    row_number=row_number,
                    level=level,
                    message=message[:2000],
                    raw_row=raw_row,
                )
            )

    # -- main entry point -------------------------------------------------

    def ingest(self, config: DatasetConfig) -> DatasetResult:
        source = self.datasets_dir / config.filename
        result = DatasetResult(dataset=config.dataset_type.value, source_file=config.filename)

        job = IngestionJob(
            dataset_type=config.dataset_type,
            source_file=config.filename,
            status=IngestionStatus.RUNNING,
        )
        self.session.add(job)
        self.session.flush()  # materialise job.id so rows can reference it
        result.job_id = job.id

        try:
            if not source.exists():
                raise FileNotFoundError(f"dataset file not found: {source}")

            # Parent keys for FK enforcement, loaded once per dataset.
            fk_keys: dict[str, set[str]] = {}
            for fk in config.fks:
                if fk.ref_table == config.model.__tablename__:
                    # Self-referential (employees.manager_id): parents may be
                    # in this very file, so seed from the file itself below.
                    fk_keys[fk.local] = self._existing_keys(fk.ref_table, fk.ref_column)
                else:
                    fk_keys[fk.local] = self._existing_keys(fk.ref_table, fk.ref_column)

            rows: list[dict[str, Any]] = []
            raw_rows: list[tuple[int, dict]] = []

            with source.open(newline="", encoding="utf-8-sig") as fh:
                reader = csv.DictReader(fh)
                missing = [f.source for f in config.fields if f.source not in (reader.fieldnames or [])]
                if missing:
                    raise ValidationError(
                        f"{config.filename} is missing expected column(s): {', '.join(missing)}"
                    )
                for line_no, raw in enumerate(reader, start=2):  # start=2: line 1 is the header
                    result.rows_read += 1
                    try:
                        record = {spec.target: _coerce(raw.get(spec.source), spec) for spec in config.fields}
                    except ValidationError as exc:
                        result.errors += 1
                        self._log(job, result, IngestionLogLevel.ERROR, str(exc), line_no, raw)
                        continue
                    rows.append(record)
                    raw_rows.append((line_no, raw))

            # Self-referential FKs can point at rows in this same file.
            for fk in config.fks:
                if fk.ref_table == config.model.__tablename__:
                    fk_keys[fk.local] |= {r[config.pk] for r in rows}

            # De-duplicate within the file itself: ON CONFLICT cannot handle
            # the same PK twice in one statement ("cannot affect row a second
            # time"). Last occurrence wins; earlier ones are counted skipped.
            seen: dict[str, int] = {}
            deduped: list[dict[str, Any]] = []
            for idx, record in enumerate(rows):
                key = record[config.pk]
                if key in seen:
                    result.skipped += 1
                    self._log(
                        job,
                        result,
                        IngestionLogLevel.WARNING,
                        f"duplicate primary key {key!r} within source file; keeping the later row",
                        raw_rows[idx][0],
                    )
                    deduped[seen[key]] = record
                    continue
                seen[key] = len(deduped)
                deduped.append(record)
            rows = deduped

            # FK validation.
            valid: list[dict[str, Any]] = []
            for record in rows:
                drop = False
                for fk in config.fks:
                    value = record.get(fk.local)
                    if value is None or value in fk_keys[fk.local]:
                        continue
                    if not fk.hard:
                        result.warnings += 1
                        self._log(
                            job,
                            result,
                            IngestionLogLevel.WARNING,
                            f"{config.model.__tablename__}.{fk.local}={value!r} has no match in "
                            f"{fk.ref_table}.{fk.ref_column} (advisory only, row kept)",
                        )
                        continue
                    if fk.nullable:
                        result.warnings += 1
                        self._log(
                            job,
                            result,
                            IngestionLogLevel.WARNING,
                            f"{fk.local}={value!r} not found in {fk.ref_table}; set to NULL",
                        )
                        record[fk.local] = None
                    else:
                        result.skipped += 1
                        drop = True
                        self._log(
                            job,
                            result,
                            IngestionLogLevel.ERROR,
                            f"{fk.local}={value!r} not found in {fk.ref_table}; row skipped",
                        )
                        break
                if not drop:
                    record["ingestion_job_id"] = job.id
                    valid.append(record)

            chunk = len(valid) or 1 if config.single_statement else self.chunk_size
            for start in range(0, len(valid), chunk):
                batch = valid[start : start + chunk]
                ins, upd = self._upsert(config, batch)
                result.inserted += ins
                result.updated += upd

            job.status = IngestionStatus.COMPLETED
            job.rows_total = result.rows_read
            job.rows_inserted = result.inserted
            job.rows_updated = result.updated
            job.rows_skipped = result.skipped
            job.rows_errored = result.errors
            job.completed_at = datetime.now()
            self.session.commit()

        except Exception as exc:  # noqa: BLE001 - one dataset failing must not kill the run
            self.session.rollback()
            # The job row was rolled back with everything else; re-record it
            # as failed in its own transaction so the failure is not invisible.
            failed = IngestionJob(
                dataset_type=config.dataset_type,
                source_file=config.filename,
                status=IngestionStatus.FAILED,
                rows_total=result.rows_read,
                error_summary=f"{type(exc).__name__}: {exc}"[:4000],
                completed_at=datetime.now(),
            )
            self.session.add(failed)
            self.session.commit()
            result.job_id = failed.id
            result.errors = max(result.errors, 1)
            result.inserted = result.updated = 0
            result.messages.append(f"[error] {type(exc).__name__}: {exc}")
            logger.error("Ingestion failed for %s: %s", config.dataset_type.value, exc)

        return result

    def _upsert(self, config: DatasetConfig, batch: list[dict[str, Any]]) -> tuple[int, int]:
        """Upsert one batch. Returns (inserted, updated) measured via xmax."""
        if not batch:
            return 0, 0

        table = config.model.__table__
        stmt = pg_insert(table).values(batch)

        updatable = {
            c.name: getattr(stmt.excluded, c.name)
            for c in table.columns
            if c.name not in (config.pk, "created_at")
        }
        # A row reappearing in a later ingest is by definition not deleted.
        if "deleted_at" in table.columns:
            updatable["deleted_at"] = None
        if "updated_at" in table.columns:
            updatable["updated_at"] = datetime.now()

        stmt = stmt.on_conflict_do_update(
            index_elements=[config.pk],
            set_=updatable,
        )
        if self.session.get_bind().dialect.name == "sqlite":
            stmt = stmt.returning(text("1 AS was_inserted"))
        else:
            stmt = stmt.returning(text("(xmax = 0) AS was_inserted"))

        rows = self.session.execute(stmt).fetchall()
        inserted = sum(1 for r in rows if r[0])
        return inserted, len(rows) - inserted


def table_counts(session: Session) -> dict[str, int]:
    """Live row count per dataset table — used by the CLI and the tests."""
    from app.ingestion.configs.registry import LOAD_ORDER

    counts: dict[str, int] = {}
    for config in LOAD_ORDER:
        table = config.model.__tablename__
        counts[table] = session.execute(select(text(f"count(*) FROM {table}"))).scalar_one()  # noqa: S608
    return counts
