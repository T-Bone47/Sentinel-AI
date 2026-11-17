# PRD — Readiness for CVP individual Defense Access (Claude Mythos)

*Owner: the repository owner, applying as an individual. Drafted 2026-11-17 by
Claude Opus 5.5. Program facts were read on 2026-11-13 and must be re-checked
before applying. Status: DRAFT — requirements only. Each milestone gets its own
implementation plan; the first is `PLAN_GATE3_DETECTIONS.md`.*

**Admission is Anthropic's decision.** This document defines what "ready to
apply" means and how to get there. It does not estimate an acceptance
probability: Anthropic publishes no acceptance rates and no scoring rubric.

---

## 1. Problem

The owner, an independent computer-science student in India, wants to apply to
Anthropic's Cyber Verification Program for individual Defense Access, which
includes Claude Mythos 5.2. Today the application would rest on a private,
unpublished project with no detection results, no public history and no record
of reported vulnerabilities — the one qualification Anthropic's announcement
names for individuals. Applied for now, it would most likely be declined, and an
application cannot be edited after submission. More fundamentally, there is not
yet a body of defensive-security work that stands on its own, with or without
Mythos.

## 2. Evidence

| Observation | Source | Date |
|---|---|---|
| Individuals may apply for Defense Access only. No CVE, certification or employer is required | CVP help article | updated 2026-10-06, read 2026-11-13 |
| Reviewers recommend "publicly checkable links"; a profile or screenshot "usually isn't enough" | CVP help article | same |
| Qualifying individuals are described as researchers "with a track record of reported vulnerabilities" | CVP announcement | 2026-10-06 |
| Mythos 5.2 is "available only to organizations verified through Anthropic's verification programs" — which contradicts the help article | Mythos 5.2 model documentation | read 2026-11-13 |
| The program exists for when Claude "blocks authorized security work"; Mythos 5.2 is the same model as Fable 5.2 | CVP help article; Mythos page | read 2026-11-13 |
| Phishing-resistant MFA (passkey or security key) is required for individual grants by 2026-12-15 | CVP security requirements | read 2026-11-13 |
| Sentinel had P0 authorization defects, no detection or incident-response capability, and unlabelled data of unknown origin | Feasibility review | 2026-11-13 |
| Gates 1–2 are implemented and tested on SQLite (507 tests) but CONDITIONAL on PostgreSQL. The project is not public and not under version control, and has no detectors | `docs/PROGRESS.md` | 2026-11-17 |
| All work so far — authorization, event pipeline, security review — ran on Fable 5.2 and Opus 5.5 without one safeguard block | This project's sessions | 2026-11-13 to 2026-11-17 |

**Assumption — needs validation via the refusal log (M6):** that the owner's
intended defensive work needs capabilities general models withhold. There is no
evidence for it yet.

## 3. Users

- **Primary — the owner, as an individual detection engineer.** Builds and
  evaluates identity-and-access detections on owned, synthetic or authorized data.
  The need would be triggered by authorized defensive tasks that safeguards block.
- **Evaluators — Anthropic CVP reviewers.** They decide on identity, legitimate
  security work, intended use and security controls. They can check a public link;
  they cannot check a private repository or a screenshot.
- **Independent reviewers — maintainers of public detection projects, and of any
  software a disclosure concerns.** Their review is what turns the owner's work
  into a record a stranger can trust.
- **Product user — a security analyst using Sentinel** to trace an alert back to
  the events behind it (Gates 3–4).
- **Not for:**
  - organizations seeking Red Team or Specialized Access (individuals are ineligible);
  - anyone wanting offensive capability;
  - a public, multi-user service built on CVP access, which needs a separate
    external-use approval.

## 4. Hypotheses

**H1 — credibility.** We believe a small body of publicly verifiable defensive
work will make an individual Defense Access application credible on its merits to
CVP reviewers. That body of work is:
- detection rules reviewed and merged by maintainers who don't know the owner;
- a reproducible evaluation on public data that reports its own failures;
- Sentinel published with honest history.

We'll know we're right when every claim in the application links to a public
artifact a stranger can check in under ten minutes, and no claim is unsupported.

**H2 — need.** We believe the owner's defensive work will run into real,
authorized tasks that safeguards block. We'll know when the refusal log holds at
least one dated, genuine entry. If it stays empty, the right decision is to not
apply yet; the work keeps its value either way.

Approval itself is an outcome to observe, not a metric we can target.

## 5. Success metrics

These are internal readiness targets, set on 2026-11-13 and 2026-11-17. They are
not Anthropic criteria.

| Metric | Target | How measured |
|---|---|---|
| Detection contributions merged upstream by independent maintainers | ≥ 3 | Links to merged pull requests |
| Public, reproducible evaluation | 1, regenerated by one documented command, reporting at least one failure | A rerun from a clean checkout reproduces the published tables |
| Sentinel published | Public repository with a licence and version history from its first commit, never rewritten | The repository itself |
| Open P0 or P1 security findings | 0 | Findings tables in `docs/PROGRESS.md` |
| PostgreSQL validation | Full suite passes on PostgreSQL | A recorded run |
| Evidence of need | ≥ 1 genuine, dated refusal-log entry, or a recorded decision not to apply | The log |
| Account prerequisites | Paid plan, Google or equivalent sign-in, phishing-resistant MFA and a physical photo ID ready by 2026-12-15 | Owner's checklist (never in Git) |
| Unsupported claims in the application | 0 | Evidence-matrix review before submitting |
| Coordinated disclosure (stretch) | ≥ 1 accepted report | Advisory or CVE link |

## 6. Scope

**MVP — the minimum defensible portfolio**
1. Sentinel published with Gates 1–3, every suite green including PostgreSQL.
2. One evaluation on a licensed public dataset, reproducible and honest about
   what it misses.
3. At least three detection contributions merged upstream.
4. A refusal log, kept from now on.
5. Account prerequisites complete.

**Stretch**
- One coordinated vulnerability disclosure. This is stretch because it depends on
  finding a real flaw, which can't be scheduled.
- A minimal Gate 4: one alert traced to a case and a redacted report.
- A short public technical write-up.

**Out of scope**
- Expanding the Copilot (Gate 5) beyond fixing open findings F9 and F10 — it
  doesn't change credibility.
- Dashboards and visual polish beyond an honest README, security policy and
  evidence matrix.
- Offensive tooling, exploit development, or testing any system that is not owned,
  synthetic, isolated or explicitly authorized.
- A hosted Sentinel that uses CVP access.
- Provoking safeguard refusals to fill the log. That would be manufactured
  evidence and probing of safeguards.
- Paid infrastructure.
- Presenting results on synthetic fixtures as detection performance.

## 7. Constraints (non-negotiable)

- **Defensive only.** Work only on owned, synthetic, isolated or explicitly
  authorized systems. A disclosure target must be software the owner runs locally,
  and the report goes only through that project's published security policy.
- **No evasion of safeguards.** When a model declines cybersecurity work, switch to
  another model or record the refusal honestly. Never rephrase a request to get
  around a safeguard.
- **The owner sends everything.** No repository is made public, and no pull
  request, report or message is submitted, by Claude. Claude drafts; the owner
  reviews and sends.
- **No fabrication.** No invented identity, credentials, results, refusals or
  reviews, and every number traceable to a command.
- **Nothing private in Git.** No identity documents, secrets or personal data.
- **What a refusal-log entry records:** date, model, the task in one line, why it
  was authorized, what was blocked, and how it was resolved. The owner keeps the
  log privately; the application summarises it, it does not quote it.

## 8. Delivery milestones

Status is pending, in-progress or complete. "Who" separates what Claude can do
from what only the owner can do.

| # | Milestone | Outcome | Depends on | Who | Status |
|---|---|---|---|---|---|
| M0 | Foundations | Version control; Gates 1–2 green on PostgreSQL; a decision on which datasets may be published; account prerequisites under way | — | Owner decides, starts Docker, sets up the account; Claude validates | in progress — data-publication decision, licence (Apache 2.0) and local version control done 2026-11-18; PostgreSQL and account prerequisites pending |
| M1 | Detection engine on synthetic data (Gate 3) | Five rules with written contracts; alerts that cite their source events; evaluation against labels, compared with Sentinel's current monitoring logic | Gate 2 | Claude (Opus did all of it) | complete on SQLite, 2026-11-17 — PostgreSQL pending (see `PROGRESS.md`) |
| M2 | Evaluation on public data | The rules and the CloudTrail adapter run on a licensed public dataset; a report with misses and coverage gaps | M1; licence check; owner approves the download | Claude; owner approves | complete on SQLite, 2026-11-17 — `research/M2_REPORT.md` (IA-003 recall 0.0071 on LANL, as pre-registered); PostgreSQL pending |
| M3 | Upstream contributions | ≥ 3 merged rule contributions, chosen from gaps found in M2 | M2 | Claude drafts; owner submits and answers review | pending |
| M4 | Minimal investigation (Gate 4, stretch) | One alert traced to a case, a timeline and a redacted report | M1 | Claude | pending |
| M5 | Publication | Public repository, write-up, evidence matrix, security policy | M0 dataset decision; M1–M3 | Claude prepares; owner publishes | pending |
| M6 | Need validation | Refusal log reviewed; owner decides to apply or to wait | Runs continuously from now | Owner | pending — starts now |
| M7 | Application | Submitted with the evidence matrix; outcome recorded; if declined, gaps closed and a new application no sooner than 7 days later | M5, M6, account prerequisites | Owner only | pending |
| S1 | Coordinated disclosure (stretch) | ≥ 1 accepted report | Owner chooses a target | Owner submits; Claude helps with local analysis | pending |

**Order:**
- M0 now.
- Then M1 → M2 → M3, because M3's contributions should come from gaps that M2 finds.
- M4 can follow M1.
- M5 follows M1–M3.
- M6 runs alongside everything.
- M7 comes last.

**Earliest sensible application:** after M1–M3 and M5. Upstream review time is the
critical path and is **TBD — needs validation by checking recent merge times on
the chosen project.**

**Alternative route:** if the owner's university has a security team or a
faculty-led lab, it can apply as an organization and add the owner as an approved
user. That sidesteps the individual track-record question entirely.

## 9. Open questions

- [ ] Does individual Defense Access include Mythos 5.2? The help article says
      every tier does; the model documentation says organizations only. Validate
      through the Verification Portal or support before M5.
- [ ] How are individual applicants in India handled? There is no public rule.
      Validate through the portal.
- [ ] Where did Sentinel's 15 CSV datasets come from, and under what licence?
      Until that is known, they stay out of the public repository and are replaced
      with synthetic data.
- [ ] Which licence for Sentinel and its fixtures? Owner's choice.
- [ ] Which public dataset for M2? It must permit publishing derived results.
      TBD — needs validation by licence review.
- [ ] Which upstream project for M3? Each has its own licence, contributor terms
      and log-source coverage. TBD — needs validation by reading the contribution
      guide and recent pull requests.
- [ ] How much time can the owner give each week? TBD; every date depends on it.
- [ ] Is there a university security team or lab that could sponsor an
      organizational application? Owner to ask.
- [ ] Does a declined application affect later ones? Unknown.

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The fixture and the rules have the same author, so the rules fit the fixture | High | High for credibility | Pre-register rule definitions and expected outcomes before code (M1); report the misses that are known by design; make M2 on public data the real test |
| Results on synthetic data are read as performance | Medium | High | Every report states what the fixture can and cannot show; no headline accuracy numbers |
| Upstream contributions are rejected or slow | Medium | Delays M3 | Small, gap-driven, well-tested contributions that follow each project's guide; start as soon as M2 shows a gap |
| No real vulnerability is found | High | No disclosure record | Kept as stretch; MVP does not depend on it |
| The refusal log stays empty | Medium | Weak "why do you need it" answer | Accept the honest outcome and don't apply yet; never provoke refusals |
| Individual access to Mythos is not offered (documentation conflict) | Unknown | High | Confirm before investing in application-specific packaging (M5) |
| CVP terms or Mythos availability change | Medium | Medium | Re-verify every fact in §2 on the day of applying |
| Sentinel's datasets can't be published | Medium | Blocks M5 | Exclude them from the public repository; use synthetic data |
| PostgreSQL stays unavailable | Medium | Gates stay CONDITIONAL | Owner starts Docker for one validation session, or CI runs a PostgreSQL service |
| Owner time and usage limits | High | Slower progress | Small steps that each leave the test suite green; full handoffs in `docs/PROGRESS.md` |
| A model declines detection work | Low–medium | Interruption | Expected behaviour: switch models, or log it if genuine; never evade |
| A disclosure attempt strays outside authorization | Low under §7 | Legal and ethical | Local software only, the project's policy only, owner submits |

---

*Status: DRAFT — requirements only. Implementation plan for M1:
`docs/PLAN_GATE3_DETECTIONS.md`.*
