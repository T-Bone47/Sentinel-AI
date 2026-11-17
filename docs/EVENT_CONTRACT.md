# Security event contract — version 1

The executable form of this document is `sentinel-ai-backend/app/events/contract.py`.
If the two disagree, that is a bug in one of them.

Status: IMPLEMENTED and TESTED on SQLite. Not yet run on PostgreSQL (see
"Known limitations").

## 1. What an event is

An event is **what a source system said happened**: who did what to what, when,
and with what result. It is stored once and never changed.

An event is not an alert, a score, a verdict or a label. Those are
interpretations. They are computed from events and stored elsewhere, so the
record of what happened can always be told apart from an opinion about it.

Sentinel's older `audit_logs` table is a separate, retrospective dataset and is
not part of this pipeline (`docs/DECISIONS.md`, ADR-009).

## 2. Fields

| Field | Type | Meaning |
|---|---|---|
| `event_id` | 64 hex chars | Permanent id, derived from the three source fields below (§4) |
| `schema_version` | int | Version of this contract: `1` |
| `source_type` | string | Which adapter read the record, e.g. `sentinel.native` |
| `source_id` | string | Which feed it came from. Letters, digits, `.` `_` `:` `-`; up to 120 chars |
| `source_event_id` | string | The source's own id for the record. Up to 200 printable chars |
| `occurred_at` | UTC timestamp | When it happened, according to the source |
| `ingested_at` | UTC timestamp | When this system stored it |
| `ingest_batch_id` | uuid | The ingestion run that stored it |
| `normalizer` | string | Adapter and version that read it, e.g. `aws.cloudtrail@1` |
| `actor` | `{type, id}` or absent | Who did it. `type`: `user`, `service`, `role`, `unknown` |
| `target` | `{type, id}` or absent | What it was done to. `type`: `principal`, `application`, `resource` |
| `action` | vocabulary (§3) | What was done, normalized |
| `source_action` | string | The source's own name for the action. Defaults to `action` |
| `outcome` | `success`, `failure`, `unknown` | Result, according to the source |
| `src_ip` | IPv4/IPv6 or absent | Address the source recorded |
| `attributes` | object (§3) | A small, typed set of extra facts the source asserted |
| `raw` | JSON | The source record as received (§4) |
| `raw_sha256` | 64 hex chars | SHA-256 of the record's canonical form (§4) |

"Printable" excludes C0 and C1 control characters and the invisible formatting
characters that can change how text displays: zero-width spaces and joiners,
directional marks, embeddings, overrides and isolates, and the byte-order mark.

Actor and target ids are identifiers only. Names, email addresses and HR data are
never copied into an event; joining to them happens at read time, under the
reader's permissions.

## 3. Vocabularies

**Actions** (14): `auth.login`, `account.create`, `account.disable`,
`account.enable`, `account.delete`, `privilege.grant`, `privilege.revoke`,
`credential.change`, `resource.read`, `resource.write`, `resource.delete`,
`resource.export`, `config.change`, `other`.

The list is short on purpose. Anything a source reports that is not on it is
stored as `other`, with its native name kept in `source_action`.

**Attributes.** Only these keys are accepted, with exactly these types. An unknown
key or a wrong type refuses the record.

| Key | Type | Meaning |
|---|---|---|
| `mfa_used` | bool | This authentication satisfied a second factor |
| `privileged` | bool | The session, account or granted role is administrative |
| `auth_method` | string | For example `password`, `sso`, `api_key` |
| `approval_ref` | string | Change or approval ticket the source attached |
| `role` | string | Role, policy or group granted or revoked |
| `sensitivity` | `public`, `internal`, `confidential`, `restricted` | Classification of the target |
| `failure_reason` | string | The source's reason code for a failure |

Every attribute is something the source asserted. Nothing is inferred or enriched
at ingestion. `privileged: false` and a missing `privileged` are different: the
second means the source did not say.

## 4. Identity and integrity

**`event_id`** is the SHA-256 of `source_type`, `source_id` and `source_event_id`
joined by the byte `0x1F`, which none of the three may contain. The same source
record therefore always gets the same id. That is what makes re-ingestion
harmless. It is an identifier, not an integrity check.

When a source has no id of its own, its adapter must construct one from the
record's content. No adapter needs this yet.

**`raw`** is the parsed source record. It is stored as canonical JSON: keys
sorted, no insignificant whitespace, non-ASCII characters written literally,
UTF-8. This is our own definition; it is close to RFC 8785 but is not claimed
to implement it.

**`raw_sha256`** is the SHA-256 of exactly that canonical text. Anyone holding an
event can recompute it.

What this gives you:
- Two copies of a record that differ only in key order or spacing are recognised
  as the same record.
- If the stored text is altered by accident, the hash no longer matches.

What it does not give you:
- **Byte-exact preservation.** The original spacing and key order are not kept,
  and if a record contained the same key twice only the last value survives.
- **Tamper-proofing.** Someone who can write to the database can change the
  record and its hash together.

## 5. Time and ordering

- A timestamp must say which timezone it is in. `2026-09-01T08:00:00Z` and
  `2026-09-01T13:30:00+05:30` are accepted and are the same instant. A timestamp
  with no offset is **refused**, never assumed to be UTC.
- An event dated more than 24 hours in the future is refused.
- Events are ordered by `occurred_at`, then `event_id`. Arrival order plays no part.
- **Events with an identical `occurred_at` have no defined order relative to each
  other.** The `event_id` tie-break is stable but arbitrary. Anything built on
  events must not depend on the order of simultaneous events.

## 6. Ingestion

**Exactly once.** Ingesting a record whose `event_id` is already stored, with the
same content, is a no-op counted as a duplicate.

**First write wins.** If the content differs, the stored event is kept and the new
record is logged as a conflict, by hash, not by content.

**Everything is accounted for.** For every batch:

```
received = inserted + duplicates + conflicts + rejected
```

**Every refusal has a reason on file.** Reports and stored reject rows contain the
record's position, a reason code, the names of the offending fields and the
record's hash. They never contain the record's content.

| Reason | Meaning |
|---|---|
| `invalid_json` | Not valid UTF-8 JSON, or cannot be written in canonical form |
| `not_an_object` | Valid JSON, but not an object |
| `record_too_large` | Larger than 64 KiB |
| `invalid_record` | Breaks this contract; the detail names the fields |
| `timestamp_in_future` | `occurred_at` more than 24 hours ahead |
| `normalizer_error` | The adapter failed on the record; details are in the server log |
| `conflicting_duplicate` | Same id as a stored event, different content |

**Limits.**

| Limit | Value |
|---|---|
| One record | 64 KiB in canonical form; a file line longer than that is refused unparsed |
| One API request | 500 records and 1 MiB |
| One transaction | 500 records |
| Reject rows kept per batch | 1,000; beyond that they are only counted |

**Failure and retry.** Ingestion runs inline; there is no queue or worker. Input is
committed in chunks of 500. If a run fails part-way, what was committed stays
(those are valid events) and the batch is marked `failed`. A batch still marked
`running` was killed outright. In both cases the remedy is the same: run the same
input again.

## 7. Adapters

| `source_type` | Reads | Validation status |
|---|---|---|
| `sentinel.native@1` | This contract as JSON (example below) | TESTED, including the synthetic fixture |
| `aws.cloudtrail@1` | One element of a CloudTrail file's `Records` array | TESTED on hand-written records and on 266 real ones (Splunk attack_data: 7 console sign-in failures, 259 IAM deletions), pinned by hash. Grant, revoke, account, credential and successful sign-in mappings: hand-written records only |
| `lanl.auth@1` | One line of LANL's `auth.txt` as `{"line": n, "text": "…"}`. Mapping registered in `research/M2_PREREGISTRATION.md` §5: only `LogOn` is a sign-in; time is seconds after 1970-01-01T00:00Z because LANL's real start is undisclosed | TESTED on hand-written lines; run on LANL by the M2 benchmark |
| `entra.signin@1` | One Azure Monitor `SignInLogs` record, the sign-in in `properties` | TESTED on hand-written records and on 30 real failed sign-ins (Splunk attack_data), pinned by hash. Success and MFA mappings: hand-written records only |

Native record:

```json
{"source_event_id": "ia1-5f2c9a41d7e0", "occurred_at": "2026-09-02T10:14:09Z",
 "actor": {"type": "user", "id": "lab-admin-02"},
 "target": {"type": "principal", "id": "lab-user-007"},
 "action": "privilege.grant", "outcome": "success", "src_ip": "198.51.100.21",
 "attributes": {"role": "payroll-admin", "privileged": true}}
```

CloudTrail mapping, in brief:
- `eventID` → `source_event_id`; `eventTime` → `occurred_at`.
- `userIdentity` → actor. `IAMUser`, `Root` and federated types are `user`;
  `AssumedRole` is `role`; `AWSService` is `service`. `Root` sets `privileged`.
- `signin:ConsoleLogin` → `auth.login`, outcome from `responseElements.ConsoleLogin`,
  `mfa_used` from `additionalEventData.MFAUsed`.
- IAM user create/delete → `account.*`; attach/put/add-to-group →
  `privilege.grant`; detach/delete/remove → `privilege.revoke`; password, access-key
  and MFA-device changes → `credential.change`.
- Any `errorCode` → `failure`, with the code as `failure_reason`.
- Everything else → `other`, named `service:EventName` in `source_action`.

Entra ID sign-in mapping, in brief:
- `properties.id` → `source_event_id`; `properties.createdDateTime` → `occurred_at`
  (Entra writes seven fractional digits; the seventh is dropped).
- `userPrincipalName`, else `userId` → actor (`user`); `appId` → target
  (`application`); `ipAddress` → `src_ip`. Categories other than `SignInLogs` are refused.
- Always `auth.login`, with `SignInLogs` as `source_action`.
- `status.errorCode` 0 → `success`; any other code → `failure`, with the code as
  `failure_reason`. Entra also gives interrupted sign-ins a code (for example
  50074, strong authentication required), so a failure is not always a wrong password.
- `mfa_used` from `authenticationRequirement`, on successes only: it names the
  factor the sign-in needed, and only a success shows it was met.
- `privileged` is never set: sign-in logs carry no role information, so IA-002
  cannot evaluate Entra sign-ins without a second source.

The stored `normalizer` records which adapter version read each event, so a later
change to a mapping cannot silently reinterpret older events.

## 8. Access

| Action | Who |
|---|---|
| Read events and ingestion batches | admin, compliance officer, security analyst |
| Ingest | admin (API); a local operator (command line) |
| Update | nobody. There is no such endpoint |

Auditors and employees cannot read events: they are per-person activity records.
Events are not reachable through the AI query engine.

There is no per-source or per-row scoping yet. A reader with access sees every
source. Sentinel is single-tenant.

## 9. Immutability

A database trigger refuses `UPDATE` on `security_events`, on PostgreSQL and
SQLite. This guards against accidental modification by any code path or ad-hoc
SQL. It is not a defence against a database administrator, who can drop it.

`DELETE` is not blocked: removing whole events is how retention will be applied.

## 10. Data minimisation and retention

Collected: the fields in §2 and the source record.
Not collected: names, emails, HR attributes, or anything looked up from another
system at ingestion time.

Retention:
- **Synthetic fixtures**: kept indefinitely. They contain no personal data.
- **Real sources**: none is connected. Before one is, the owner must set a
  retention period for it.
- **Purge mechanism: PLANNED.** It is deliberately not built yet. Deleting an
  event must also deal with any alert that cites it, and alerts do not exist
  until the next gate. Building the purge first would get that wrong.

## 11. Labels

Ground-truth labels for evaluation live only in a fixture's `labels.jsonl`. They
are never ingested. The events table has no column, and the attribute list no
key, that could hold one. A detector therefore cannot read the answer.

## 12. Known limitations

- **PostgreSQL: not run.** All tests ran on SQLite. The trigger, the migrations
  and the concurrent-writer path are unverified on PostgreSQL.
- The CloudTrail adapter has never seen real CloudTrail data.
- No purge (§10) and no rate limit on the ingest endpoint.
- Offset-free paging is by cursor only; there is no total count.
- One process: nothing here has been tested with several API workers.
- Simultaneous events have no defined order (§5).

## 13. Changing this contract

- Adding an action or an attribute: add it here and in `contract.py`; no version
  bump, because existing events remain valid.
- Changing the meaning or type of anything existing: bump `schema_version`, and
  bump the version of every adapter whose output changes.
- Fixtures are frozen. A change to a fixture is a new fixture with a new
  `source_id`.
