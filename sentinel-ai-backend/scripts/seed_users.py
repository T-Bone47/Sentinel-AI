"""
Seed demo platform users (one per role) so the login endpoint has something
real to authenticate against.

    python scripts/seed_users.py
    python scripts/seed_users.py --password 'YourOwnPassword'

Idempotent: existing emails are updated in place, never duplicated.
The default password is a well-known demo value and is fine ONLY because
this is a hackathon demo database. Pass --password for anything else.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Employee, User  # noqa: E402
from app.models.enums import UserRole  # noqa: E402

DEMO_PASSWORD = "Sentinel@123"  # noqa: S105 - demo seed only, override with --password

SEED = [
    ("admin@sentinel.ai", "Platform Admin", UserRole.ADMIN),
    ("compliance@sentinel.ai", "Compliance Officer", UserRole.COMPLIANCE_OFFICER),
    ("security@sentinel.ai", "Security Analyst", UserRole.SECURITY_ANALYST),
    ("auditor@sentinel.ai", "External Auditor", UserRole.AUDITOR),
    ("employee@sentinel.ai", "Demo Employee", UserRole.EMPLOYEE),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", default=DEMO_PASSWORD)
    args = parser.parse_args()

    if args.password == DEMO_PASSWORD and not settings.is_local:
        print(
            "Refusing to seed accounts with the public demo password outside local "
            f"development (ENVIRONMENT={settings.environment!r}). Pass --password."
        )
        return 1

    engine = create_engine(settings.database_url_sync, future=True)
    with Session(engine) as session:
        # Link the employee-role account to a real ingested Employee row if one exists.
        first_employee = session.execute(
            select(Employee.employee_id).order_by(Employee.employee_id).limit(1)
        ).scalar_one_or_none()

        created = updated = 0
        for email, full_name, role in SEED:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                session.add(
                    User(
                        email=email,
                        full_name=full_name,
                        role=role,
                        hashed_password=hash_password(args.password),
                        is_active=True,
                        employee_id=first_employee if role is UserRole.EMPLOYEE else None,
                    )
                )
                created += 1
            else:
                user.full_name = full_name
                user.role = role
                user.hashed_password = hash_password(args.password)
                user.is_active = True
                updated += 1
        session.commit()

    print(f"Users seeded: {created} created, {updated} updated.")
    for email, _, role in SEED:
        print(f"  {email:<28} role={role.value}")
    print(f"\nPassword: {args.password}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
