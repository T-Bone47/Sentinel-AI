# M2 — public dataset shortlist (for the owner's approval)

*Prepared 2026-11-17 by Claude Opus 5.5 from each source's public pages. Nothing
has been downloaded. Licences were read on the date shown; re-check them before
use. Items marked "unverified" come from folder names or page text, not from
inspecting the data.*

## The finding that shapes M2

No public dataset found carries all the attributes the five rules need.

| Rule | Needs | Public data that has it |
|---|---|---|
| IA-001 privileged grant without approval | grant events, a privileged flag, approval references | CloudTrail IAM events (no approval references anywhere) |
| IA-002 privileged sign-in without MFA | sign-ins with MFA and privilege fields | **None found.** Entra ID sign-in logs give MFA but no privilege field (found while building the adapter, 2026-11-17); the role would need a second source |
| IA-003 failed sign-ins then success | sign-ins with outcome and account | LANL authentication data; CloudTrail and Entra sign-in data |
| IA-004 activity by a disabled account | disable events and later activity, same source | Possibly Entra ID and Windows account events (unverified) |
| IA-005 unapproved grant then sensitive access | grants, plus data access with a classification | **None found** |

So on public data, M2 can properly test:
- the CloudTrail adapter, which has never seen a real record;
- IA-003, against real ground truth.

IA-001 and IA-004 can be tested only in part. IA-002 cannot be tested on public
sign-in logs alone (see the table). IA-005 stays synthetic-only, and any write-up
must say so.

## Shortlist

| # | Dataset | Licence | Labels | What it would test | Size and access | Recommendation |
|---|---|---|---|---|---|---|
| 1 | **Splunk `attack_data`** (github.com/splunk/attack_data) | Apache 2.0 | Per dataset: each folder records one ATT&CK technique being performed. No benign background | CloudTrail adapter on real records. IA-003 on `T1110.001/aws_login_failure`. IA-002 and IA-003 on `azure_ad_*` folders, after building an Entra ID adapter. IA-001 against `T1098/aws_iam_*` (contents unverified) | Git LFS, can be fetched one folder at a time; the whole set is over 9 GB. Folder sizes unknown until listed | **First.** Permissive licence, no registration, small selective downloads |
| 2 | **OTRF Security-Datasets** (github.com/OTRF/Security-Datasets) | MIT (LICENSE file checked) | Per dataset, with metadata describing what was simulated | Second source of real-format AWS records for the CloudTrail adapter and IA-001 | Small JSON or zip files under `datasets/atomic/aws` (contents unverified) | **Second.** Cheap cross-check of the adapter |
| 3 | **LANL "Comprehensive, Multi-Source Cyber-Security Events"** (csr.lanl.gov/data/cyber1) | CC0 1.0 (public domain) | **Event-level ground truth:** red-team compromise authentications, over 58 days of real, de-identified enterprise activity | IA-003 against real attacks *and* real benign background: the only option that can measure false positives | `auth.txt.gz` is 7.2 GB compressed. The download form asks for your email and intended use. Citation required (Kent 2015, DOI 10.17021/1179829) | **Most valuable, most work.** Needs a new adapter and a sampling plan pre-registered before scoring (a run holds at most 50,000 events) |
| 4 | **flaws.cloud CloudTrail logs** (Summit Route) | **No licence stated** | None. "Largely attacks", unlabelled | Adapter robustness on 1.94 M real, anonymised CloudTrail events | About 240 MB | **Private robustness testing only**, unless the author grants permission to publish anything derived |

**Not shortlisted:**
- **Microsoft Sentinel sample data:** no identity logs visible, and the licence
  was not shown on the page checked.
- **CMU CERT insider-threat dataset:** the page refused access, so the licence
  is unverified. Its scenarios don't map to these rules.
- **Stratus Red Team:** it generates real attack telemetry in *your own* AWS
  account. It needs an AWS account and may cost money; that's an owner decision
  for later.

## What I expect, before looking at any of the data

These are expectations, not results.

- **LANL:** IA-003 will catch few or none of the red-team events. Red teams
  usually authenticate with valid stolen credentials, not by guessing. If so,
  that is the negative result M2 needs: a correct rule that misses the attack
  that actually happened.
- **CloudTrail:** the adapter will map most real records to `other`, because it
  covers only sign-in and core IAM calls. The share mapped, the reject rate, and
  any adapter crashes will be reported as measured.

## Steps that need you

1. **Approve item 1 and item 2.** Before anything is downloaded, I'll list the
   exact folders, files and sizes (read-only), then ask for your yes on that
   list.
2. **LANL (item 3), if you want it.** The download form asks for your email
   address and intended use. Only you can submit it; Claude does not enter
   personal data into forms. A truthful intended use would be "evaluating
   detection rules for a student research project".
3. **flaws.cloud (item 4).** Optional: decide whether to ask the author for
   permission to publish derived results.

## Approval list (updated 2026-11-17)

**Verified file by file (nothing downloaded yet):**

| Source | File | Size | What it is |
|---|---|---|---|
| Splunk `attack_data` (Apache 2.0) | `datasets/attack_techniques/T1110.001/aws_login_failure/aws_cloudtrail_events.json` | 7.9 KB (Git LFS) | Real AWS CloudTrail events from Splunk's lab environment ("attack_range"), 2022-08-08: AWS console sign-in failures |
| Splunk `attack_data` | `…/aws_login_failure/aws_login_failure.yml` | under 1 KB | The dataset's metadata (already read) |
| LANL (CC0 1.0) | `auth.txt.gz` | 7.2 GB compressed | 58 days of de-identified enterprise authentication events |
| LANL | `redteam.txt.gz` | 4.8 KB | The red-team compromise events: the ground truth |

LANL's other files (`proc`, `flows`, `dns`; 3.5 GB) are not needed.

**Folder exists; file sizes still to be listed:**

- `T1110.001/azure_ad_high_number_of_failed_authentications_for_user/` (needs
  an Entra ID adapter);
- `T1098/aws_iam_delete_policy/`;
- `T1098/aws_iam_successful_group_deletion/`;
- `T1098/aws_iam_failure_group_deletion/`.

Their sizes could not be read today: GitHub's anonymous API limit for this
network address was used up (HTTP 403, 0 requests remaining), and the GitHub CLI
is not installed. They will be listed before anything in them is downloaded.

**OTRF changed:** its `datasets/atomic/aws` folder holds only `collection` and
`discovery` scenarios, with no sign-in or permission-grant activity. It is now
an optional adapter-robustness check, not a test of any rule.

## Remaining Splunk files, sized (2026-11-17; not downloaded)

Sizes are read from each file's Git LFS pointer, and log types from each folder's metadata.

| File | Size | Log type | What it can test |
|---|---|---|---|
| `T1110.001/azure_ad_high_number_of_failed_authentications_for_user/azuread.log` | 102.8 KB | `azure:monitor:aad` (Entra ID) | IA-003, and IA-002 if MFA fields are present — **needs a new Entra ID adapter first** |
| `T1098/aws_iam_delete_policy/aws_iam_delete_policy.json` | 104.8 KB | `aws:cloudtrail` | Adapter robustness on real IAM records. Policy deletion maps to `other`, so no rule fires by design |
| `T1098/aws_iam_successful_group_deletion/aws_iam_successful_group_deletion.json` | 75.7 KB | `aws:cloudtrail` | Adapter robustness |
| `T1098/aws_iam_failure_group_deletion/aws_iam_failure_group_deletion.json` | 46.0 KB | `aws:cloudtrail` | Adapter robustness, including real failed calls (`errorCode`) |

The four files total 329.3 KB. The folders also hold copies in Amazon Security
Lake's OCSF format (`asl_ocsf_cloudtrail.json`, `amazon_security_lake.json`,
2–6 KB each). Our adapters don't read that format, so they are not proposed.

The real-data adapter check is now repeatable:
`test_cloudtrail_adapter_reads_real_console_login_failures` pins the file's
hash, and skips with a reason where the file has not been downloaded.

## Downloaded, batch 2 (owner approved, 2026-11-17)

Each file is in its own folder,
`research/external/splunk-attack-data/<technique>-<folder>/`. Every file's
size and SHA-256 match its Git LFS pointer. Source: splunk/attack_data, branch
`master`, licence Apache 2.0.

| File | Bytes | SHA-256 |
|---|---|---|
| `azuread.log` (Entra ID) | 105,311 | `1d5c729dc5e864ca2894cceae832ff4119f17a709e1ec33838b3f60baab3af87` |
| `aws_iam_delete_policy.json` | 107,317 | `862f9c73569bcdd38006b242bcdcd82b1424cabaaee01c4f931732e5f4c04b33` |
| `aws_iam_successful_group_deletion.json` | 77,518 | `6f526a69b82e0d53ef733e79f44e6422bd599af51d2f31896b853ded069c3396` |
| `aws_iam_failure_group_deletion.json` | 47,083 | `3dae36751402bc19f86cecfac3f622ac41ef6d4c4ede6f334e3b7fbcde35a991` |

**CloudTrail adapter on these real records** (in memory, throwaway script):

- **Normalized:** all 259 IAM records — 116 `DeletePolicy`, 93 `DeleteGroup`
  successes and 50 `DeleteGroup` failures — with 0 rejected and 0 crashes.
- **Outcome from `errorCode`:** 88 failures and 171 successes.
- **Action mapping:** both calls map to `other`, as designed, because neither is
  a grant, revoke or sign-in. No rule fired, which is the expected result.

**Since done (2026-11-17, later session):**
- These checks are now pinned tests (`test_cloudtrail_adapter_reads_real_iam_deletions`),
  one per file, and each also ingests its file.
- **Correction:** two files repeat records verbatim, with the same `eventID` and
  identical content: `DeletePolicy` has 6 extra copies and successful
  `DeleteGroup` has 8. Ingest therefore stores 245 events and counts 14
  duplicates. "All 259 normalized" above is true of the records, not of distinct events.
- The Entra ID file is read by the new `entra.signin@1` adapter
  (`test_entra_adapter_reads_real_failed_password_sign_ins`). It holds 30 failed
  password sign-ins (code 50126) by one user from one address within 11 seconds,
  and no success. So IA-003 cannot fire on it, and IA-002 has nothing to evaluate.
  It tests the adapter, not a rule.

## Downloaded (owner approved, 2026-11-17)

| File | Stored at | Bytes | SHA-256 | Provenance |
|---|---|---|---|---|
| `aws_cloudtrail_events.json` | `research/external/splunk-attack-data/T1110.001-aws_login_failure/` | 8,107 | `d9d0ebbaf9a6aebd504b03f665eb1f35dfee4e34c0c6a5cf1c5318b7a12c1e9b` | splunk/attack_data, branch `master`, path `datasets/attack_techniques/T1110.001/aws_login_failure/`, retrieved 2026-11-17T10:08Z. Size and hash match the Git LFS pointer. Licence Apache 2.0: keep this attribution if it is ever redistributed |

**First real records through the CloudTrail adapter** (in memory, by a throwaway
script; not yet a repeatable test):

- **Parsed:** the file is JSON Lines holding 7 records, all
  `signin:ConsoleLogin`, from 4 actors, dated 2022-03-01 to 2022-08-05.
- **Adapter:** all 7 normalized, with 0 rejected and 0 crashes. Every one became
  `auth.login` / `failure` with `mfa_used` set.
- **Rules:** 0 alerts. IA-003 is correctly silent: the file holds only failures,
  spread over months, and no success.

**What this shows:** the adapter reads real ConsoleLogin failure records. It is
**not** a detection evaluation: 7 records with no successes cannot test whether
IA-003 fires when it should.

**Next for this source:**
- list and size the remaining Splunk folders, then, once approved, add a
  repeatable adapter test over the stored file;
- pre-register the full M2 plan before any scoring.

## LANL plan (outline; the full version is pre-registered before scoring)

1. **Owner:** submit LANL's download form with your own email address and a
   truthful intended use. Download `auth.txt.gz` and `redteam.txt.gz` to a
   folder outside the repository (for example `<your datasets folder>\lanl\`),
   and tell Claude the path.
   - It needs 7.2 GB of free disk. The file is read compressed and never
     unpacked.
   - It is never committed: CC0 would allow that, but 7.2 GB does not belong in
     Git.
2. **New adapter `lanl.auth@1`:** each line becomes one `auth.login` event.
   - The source user becomes the actor and the destination computer the target.
   - The outcome comes from LANL's success/failure field.
   - LANL timestamps are offsets from an undisclosed start, so they are mapped
     onto a fixed, documented origin. Only intervals between events are
     meaningful.
   - There are no MFA, privilege, grant or disable fields, so only IA-003
     applies; the other rules are reported as not evaluable on LANL.
3. **Ground truth:** every red-team record is matched to the authentication
   events with the same time, user, source and destination.
4. **Sampling, written and hashed before any scoring:**
   - every authentication by each red-team user, within a fixed window around
     each red-team event;
   - the same window for a fixed-seed random sample of other users, to measure
     false alarms;
   - each user's events form their own source, which keeps every run under the
     50,000-event limit.
5. **Pre-registered prediction:** IA-003 catches few or none of the red-team
   events, because red teams mostly use valid stolen credentials rather than
   guessing passwords. It is reported however it turns out.
6. **Credit:** results cite A. D. Kent, "Comprehensive, Multi-Source
   Cybersecurity Events," LANL, 2015, DOI 10.17021/1179829.

## Ground rules for M2

- Downloaded data goes to its own folder outside `research/fixtures/` and is
  never committed unless its licence allows redistribution. Apache 2.0, MIT and
  CC0 do; flaws.cloud has no licence.
- Sampling rules, parameters and expected outcomes are written and hashed before
  scoring, as in Gate 3.
- Rule parameters stay frozen at version 1. Any change after seeing public data
  is a version-2 rule, reported separately.
