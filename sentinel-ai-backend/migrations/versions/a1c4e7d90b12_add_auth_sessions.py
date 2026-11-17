"""add auth_sessions (revocable, rotating login sessions)

Revision ID: a1c4e7d90b12
Revises: 3e5422bdcfdf
Create Date: 2026-11-16

Additive only: one new table, no change to existing tables or data.
Rollback (`alembic downgrade 3e5422bdcfdf`) drops the table, which signs
every user out; nothing else is lost.
"""
from alembic import op
import sqlalchemy as sa


revision = "a1c4e7d90b12"
down_revision = "3e5422bdcfdf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("refresh_jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_sessions_user_id"), table_name="auth_sessions")
    op.drop_table("auth_sessions")
