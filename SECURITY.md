# Security policy

Sentinel AI is a defensive security research project maintained by one person.
It is **not production software** and has no deployed instance.

## Reporting a vulnerability

Please report privately through GitHub: this repository's **Security** tab →
**Report a vulnerability**. Do not open a public issue for security problems.

Please include:
- what is affected (file, endpoint or commit);
- how to reproduce it, using the synthetic demo data only;
- what an attacker could do with it.

You can expect an acknowledgement within 7 days. Fixes are made on a `fix/`
branch with a regression test, and reporters are credited unless they ask not
to be.

## Scope

- **In scope:** the code in this repository: the backend API, sign-in and
  sessions, the permission matrix, event ingestion, the detection engine and
  the frontend.
- **Out of scope:**
  - any deployment you run yourself;
  - the fictional demo data;
  - findings that need the documented demo credentials outside development
    (startup refuses them there);
  - denial of service by volume.

Test only on your own local copy. Never test systems you do not own or have
permission to test.

## Known open issues

These are tracked publicly; there is no need to report them again.
- **Findings R5–R10** in `docs/PROGRESS.md` (review pass, 2026-11-17).
  Examples: no per-address rate limit at sign-in, and public API docs.
- **Bearer tokens stay in `localStorage`**: an accepted risk, with its
  reasoning in `docs/DECISIONS.md`, ADR-002.

The threat model is in `docs/THREAT_MODEL.md`.
