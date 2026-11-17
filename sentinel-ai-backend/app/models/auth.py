"""
Platform authentication. Not derived from any dataset — invented for
Step 7 (JWT + RBAC foundation). Uses a UUID PK (UUIDPKMixin) since there
is no natural business key, per the approved architecture's default.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPKMixin


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=30),
        nullable=False,
        default=UserRole.EMPLOYEE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optional link to a real Employee row (from dataset1) so an "employee"-role
    # login can be traced back to their HR record. Nullable: admin/compliance/
    # security/auditor accounts are not necessarily also ingested Employees.
    employee_id: Mapped[str | None] = mapped_column(
        String(20), ForeignKey("employees.employee_id", ondelete="SET NULL"), nullable=True, index=True
    )


class AuthSession(Base, UUIDPKMixin):
    """One row per login. Access tokens carry this row's id (`sid`) and stop
    working the moment `revoked_at` is set. `refresh_jti` is the id of the
    one refresh token currently valid for the session; it changes on every
    refresh, so presenting an older one is detectable as a replay."""

    __tablename__ = "auth_sessions"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_jti: Mapped[str] = mapped_column(String(36), nullable=False)
    # Epoch seconds rather than a timestamp column: compared against JWT `exp`
    # values, and identical on SQLite (tests/CI) and PostgreSQL.
    expires_at: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
