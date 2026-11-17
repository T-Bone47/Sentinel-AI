"""
Generate docs/API_CONTRACT.md by calling every endpoint against the running
backend and recording what actually comes back.

The point is that no example in the contract is hand-written. A hand-typed
sample response drifts from the code the first time a field is renamed, and
the frontend team finds out at integration time. These are captured live,
so regenerating is the fix:

    uvicorn app.main:app &
    python scripts/generate_api_contract.py

Long lists and deep objects are truncated for readability — truncation is
marked inline, never silent.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BASE = "http://127.0.0.1:8000"
OUT = ROOT / "docs" / "API_CONTRACT.md"

MAX_LIST_ITEMS = 2
MAX_DICT_KEYS = 14
MAX_STRING = 160


def call(method: str, path: str, body: dict | None = None, token: str | None = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())
    except URLError as exc:
        raise SystemExit(f"Backend not reachable at {BASE}: {exc}. Start uvicorn first.") from exc


def shrink(value, depth: int = 0):
    """Truncate for readability, marking every cut so nothing looks complete when it isn't."""
    if isinstance(value, list):
        if not value:
            return []
        shrunk = [shrink(v, depth + 1) for v in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            shrunk.append(f"... {len(value) - MAX_LIST_ITEMS} more items")
        return shrunk
    if isinstance(value, dict):
        items = list(value.items())
        shrunk = {k: shrink(v, depth + 1) for k, v in items[:MAX_DICT_KEYS]}
        if len(items) > MAX_DICT_KEYS:
            shrunk[f"... {len(items) - MAX_DICT_KEYS} more keys"] = "..."
        return shrunk
    if isinstance(value, str) and len(value) > MAX_STRING:
        return value[:MAX_STRING] + f"... (+{len(value) - MAX_STRING} chars)"
    return value


def block(status: int, payload) -> str:
    return f"```jsonc\n// HTTP {status}\n{json.dumps(shrink(payload), indent=2)}\n```"


def main() -> int:
    status, _ = call("GET", "/api/v1/health")
    if status != 200:
        raise SystemExit("health check failed — is the backend running?")

    _, login = call(
        "POST",
        "/api/v1/auth/login",
        {"email": "admin@sentinel.ai", "password": "Sentinel@123"},
    )
    token = login.get("data", {}).get("access_token")

    # Real IDs, pulled from the live API so the examples are followable.
    ids: dict[str, str] = {}
    for key, path, predicate in [
        ("risk", "/api/v1/risks?page_size=50", lambda r: r.get("mapped_control_id")),
        ("finding", "/api/v1/findings?page_size=50", lambda r: r.get("evidence_id")),
        ("evidence", "/api/v1/evidence?page_size=1", lambda r: True),
        ("control", "/api/v1/controls?page_size=1", lambda r: True),
        ("policy", "/api/v1/policies?page_size=1", lambda r: True),
        ("employee", "/api/v1/employees?page_size=1", lambda r: True),
        ("application", "/api/v1/applications?page_size=1", lambda r: True),
        ("device", "/api/v1/devices?page_size=1", lambda r: True),
        ("vendor", "/api/v1/vendors?page_size=1", lambda r: True),
        ("report", "/api/v1/reports?page_size=1", lambda r: True),
    ]:
        _, body = call("GET", path)
        row = next((r for r in body["data"] if predicate(r)), body["data"][0])
        ids[key] = next(iter(row.values()))

    sections: list[tuple[str, list[tuple[str, str, str]]]] = [
        (
            "System & Authentication",
            [
                ("Health check", "GET", "/api/v1/health"),
                ("Login", "POST", "/api/v1/auth/login"),
                ("Current user", "GET", "/api/v1/auth/me"),
            ],
        ),
        (
            "Command Center",
            [
                ("Dashboard aggregate", "GET", "/api/v1/dashboard"),
                ("Dashboard with scores disabled", "GET", "/api/v1/dashboard?scores=off"),
            ],
        ),
        (
            "Organization Graph",
            [
                ("Full graph", "GET", "/api/v1/organization/graph?scope=full&limit_employees=25"),
                (
                    "Focused on one employee",
                    "GET",
                    f"/api/v1/organization/graph?scope=org&employee_id={ids['employee']}",
                ),
            ],
        ),
        (
            "Frameworks",
            [
                ("All frameworks", "GET", "/api/v1/frameworks"),
                ("One framework", "GET", "/api/v1/frameworks/ISO%2027001"),
            ],
        ),
        (
            "Investigations / Risk Center",
            [
                ("Risk list (filtered)", "GET", "/api/v1/risks?severity=Critical&page_size=2"),
                ("Risk investigation detail", "GET", f"/api/v1/risks/{ids['risk']}"),
            ],
        ),
        (
            "Findings",
            [
                ("Findings list (filtered)", "GET", "/api/v1/findings?status=Open&severity=High&page_size=2"),
                ("Finding detail", "GET", f"/api/v1/findings/{ids['finding']}"),
            ],
        ),
        (
            "Evidence Repository",
            [
                ("Evidence list", "GET", "/api/v1/evidence?verified=true&page_size=2"),
                ("Evidence detail", "GET", f"/api/v1/evidence/{ids['evidence']}"),
            ],
        ),
        (
            "Policies & Controls",
            [
                ("Policies list", "GET", "/api/v1/policies?framework=DPDP&page_size=2"),
                ("Policy detail", "GET", f"/api/v1/policies/{ids['policy']}"),
                ("Controls list", "GET", "/api/v1/controls?severity=High&page_size=2"),
                ("Control detail", "GET", f"/api/v1/controls/{ids['control']}"),
            ],
        ),
        (
            "People & Assets",
            [
                ("Employees list", "GET", "/api/v1/employees?department=Engineering&page_size=2"),
                ("Employee 360 detail", "GET", f"/api/v1/employees/{ids['employee']}"),
                ("Identity & access", "GET", "/api/v1/iam?privileged_account=true&page_size=2"),
                ("Devices", "GET", "/api/v1/devices?compliance_status=Non-Compliant&page_size=2"),
                ("Device detail", "GET", f"/api/v1/devices/{ids['device']}"),
                ("Applications", "GET", "/api/v1/applications?internet_facing=true&page_size=2"),
                ("Application detail", "GET", f"/api/v1/applications/{ids['application']}"),
                ("Cloud assets", "GET", "/api/v1/cloud-assets?public_access=true&page_size=2"),
            ],
        ),
        (
            "Third-Party Vendors",
            [
                ("Vendors list", "GET", "/api/v1/vendors?risk_rating=Critical&page_size=2"),
                ("Vendor detail", "GET", f"/api/v1/vendors/{ids['vendor']}"),
            ],
        ),
        (
            "DPDP / Privacy",
            [
                ("Personal data inventory", "GET", "/api/v1/dpdp/personal-data?third_party_sharing=true&page_size=2"),
                ("Consent records", "GET", "/api/v1/dpdp/consents?revoked=true&page_size=2"),
            ],
        ),
        (
            "Audit Logs",
            [
                (
                    "Audit logs (date range + risk filter)",
                    "GET",
                    "/api/v1/audit-logs?date_from=2026-07-01&date_to=2026-07-31&min_risk_score=60&page_size=2",
                ),
                ("Audit logs (failures)", "GET", "/api/v1/audit-logs?result=Failure&sort=-timestamp&page_size=2"),
            ],
        ),
        (
            "Reports",
            [
                ("Reports list", "GET", "/api/v1/reports?framework=SOC2&page_size=2"),
                ("Report detail", "GET", f"/api/v1/reports/{ids['report']}"),
            ],
        ),
        (
            "Error shapes",
            [
                ("Not found", "GET", "/api/v1/risks/DOES-NOT-EXIST"),
                ("Unauthorized", "GET", "/api/v1/auth/me"),
            ],
        ),
    ]

    lines: list[str] = [
        "# Sentinel AI — Frontend API Contract",
        "",
        "> **Generated, not written.** Every example below was captured from a live call",
        "> against the running backend with the real ingested datasets. Regenerate with:",
        "> ```bash",
        "> uvicorn app.main:app &",
        "> python scripts/generate_api_contract.py",
        "> ```",
        "",
        f"Base URL: `{BASE}/api/v1` · Interactive docs: `{BASE}/api/docs`  ",
        f"Captured: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Long lists and deep objects are truncated for readability. Every truncation is",
        "marked inline (`... N more items`); nothing is silently omitted.",
        "",
        "---",
        "",
        "## Conventions",
        "",
        "Every response uses the same envelope, including errors:",
        "",
        "```jsonc",
        '// list    {"data": [...], "meta": {...}, "error": null}',
        '// detail  {"data": {...}, "error": null}',
        '// error   {"data": null, "error": {"code": "http_404", "message": "..."}}',
        "```",
        "",
        "**Every list endpoint** accepts `?page=` (default 1), `?page_size=` (default 20,",
        "max 200), `?search=` (case-insensitive partial match) and `?sort=` (column name,",
        "prefix `-` for descending). Per-resource filters are listed in each endpoint's",
        "description at `/api/docs`. Filters combine with AND.",
        "",
        "**Auth**: `POST /api/v1/auth/login` returns an access token and a refresh token.",
        "Send `Authorization: Bearer <access_token>`. Data endpoints are currently",
        "unauthenticated for the Review-1 demo — see HANDOFF.md §6.",
        "",
        "---",
        "",
        "## Screen → endpoint map",
        "",
        "| Frontend tab | Endpoint(s) |",
        "|---|---|",
        "| Command Center | `GET /dashboard` |",
        "| Sentinel AI | *Phase 2 — no backend yet* |",
        "| Investigations | `GET /risks`, `GET /risks/{id}` |",
        "| Organization Graph | `GET /organization/graph` |",
        "| Policies | `GET /policies`, `GET /policies/{id}` |",
        "| Controls | `GET /controls`, `GET /controls/{id}` |",
        "| Frameworks | `GET /frameworks`, `GET /frameworks/{framework}` |",
        "| Risk Center | `GET /risks`, `GET /risks/{id}` |",
        "| Findings | `GET /findings`, `GET /findings/{id}` |",
        "| Employees | `GET /employees`, `GET /employees/{id}` |",
        "| Identity & Access | `GET /iam`, `GET /iam/{id}` |",
        "| Devices | `GET /devices`, `GET /devices/{id}` |",
        "| Applications | `GET /applications`, `GET /applications/{id}` |",
        "| Cloud Assets | `GET /cloud-assets`, `GET /cloud-assets/{id}` |",
        "| Third-Party Vendors | `GET /vendors`, `GET /vendors/{id}` |",
        "| DPDP Data Inventory | `GET /dpdp/personal-data`, `GET /dpdp/personal-data/{id}` |",
        "| Consent Management | `GET /dpdp/consents`, `GET /dpdp/consents/{id}` |",
        "| Evidence Repository | `GET /evidence`, `GET /evidence/{id}` |",
        "| Audit Logs | `GET /audit-logs`, `GET /audit-logs/{id}` |",
        "| Reports | `GET /reports`, `GET /reports/{id}` |",
        "| Settings | *frontend-only — no backend needed* |",
        "",
        "---",
        "",
    ]

    for title, endpoints in sections:
        lines += [f"## {title}", ""]
        for label, method, path in endpoints:
            if label == "Current user":
                status, payload = call(method, path, token=token)
            elif label == "Unauthorized":
                status, payload = call(method, path)
            elif method == "POST":
                status, payload = call(
                    method, path, {"email": "admin@sentinel.ai", "password": "Sentinel@123"}
                )
                # Never publish a live token in a committed document.
                for field in ("access_token", "refresh_token"):
                    if isinstance(payload.get("data"), dict) and field in payload["data"]:
                        payload["data"][field] = "<jwt redacted>"
            else:
                status, payload = call(method, path)

            lines += [f"### {label}", "", f"`{method} {path}`", "", block(status, payload), ""]
        lines += ["---", ""]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
