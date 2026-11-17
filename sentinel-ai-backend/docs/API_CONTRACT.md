# Sentinel AI — Frontend API Contract

> **Generated, not written.** Every example below was captured from a live call
> against the running backend with the real ingested datasets. Regenerate with:
> ```bash
> uvicorn app.main:app &
> python scripts/generate_api_contract.py
> ```

Base URL: `http://127.0.0.1:8000/api/v1` · Interactive docs: `http://127.0.0.1:8000/api/docs`  
Captured: 2026-08-08 10:03 UTC

Long lists and deep objects are truncated for readability. Every truncation is
marked inline (`... N more items`); nothing is silently omitted.

---

## Conventions

Every response uses the same envelope, including errors:

```jsonc
// list    {"data": [...], "meta": {...}, "error": null}
// detail  {"data": {...}, "error": null}
// error   {"data": null, "error": {"code": "http_404", "message": "..."}}
```

**Every list endpoint** accepts `?page=` (default 1), `?page_size=` (default 20,
max 200), `?search=` (case-insensitive partial match) and `?sort=` (column name,
prefix `-` for descending). Per-resource filters are listed in each endpoint's
description at `/api/docs`. Filters combine with AND.

**Auth**: `POST /api/v1/auth/login` returns an access token and a refresh token.
Send `Authorization: Bearer <access_token>`. Data endpoints are currently
unauthenticated for the Review-1 demo — see HANDOFF.md §6.

---

## Screen → endpoint map

| Frontend tab | Endpoint(s) |
|---|---|
| Command Center | `GET /dashboard` |
| Sentinel AI | *Phase 2 — no backend yet* |
| Investigations | `GET /risks`, `GET /risks/{id}` |
| Organization Graph | `GET /organization/graph` |
| Policies | `GET /policies`, `GET /policies/{id}` |
| Controls | `GET /controls`, `GET /controls/{id}` |
| Frameworks | `GET /frameworks`, `GET /frameworks/{framework}` |
| Risk Center | `GET /risks`, `GET /risks/{id}` |
| Findings | `GET /findings`, `GET /findings/{id}` |
| Employees | `GET /employees`, `GET /employees/{id}` |
| Identity & Access | `GET /iam`, `GET /iam/{id}` |
| Devices | `GET /devices`, `GET /devices/{id}` |
| Applications | `GET /applications`, `GET /applications/{id}` |
| Cloud Assets | `GET /cloud-assets`, `GET /cloud-assets/{id}` |
| Third-Party Vendors | `GET /vendors`, `GET /vendors/{id}` |
| DPDP Data Inventory | `GET /dpdp/personal-data`, `GET /dpdp/personal-data/{id}` |
| Consent Management | `GET /dpdp/consents`, `GET /dpdp/consents/{id}` |
| Evidence Repository | `GET /evidence`, `GET /evidence/{id}` |
| Audit Logs | `GET /audit-logs`, `GET /audit-logs/{id}` |
| Reports | `GET /reports`, `GET /reports/{id}` |
| Settings | *frontend-only — no backend needed* |

---

## System & Authentication

### Health check

`GET /api/v1/health`

```jsonc
// HTTP 200
{
  "data": {
    "status": "ok",
    "service": "Sentinel AI",
    "version": "0.1.0-phase1"
  },
  "error": null
}
```

### Login

`POST /api/v1/auth/login`

```jsonc
// HTTP 200
{
  "data": {
    "access_token": "<jwt redacted>",
    "refresh_token": "<jwt redacted>",
    "token_type": "bearer",
    "role": "admin",
    "email": "admin@sentinel.ai",
    "full_name": "Platform Admin"
  },
  "error": null
}
```

### Current user

`GET /api/v1/auth/me`

```jsonc
// HTTP 200
{
  "data": {
    "id": "f7f0d75c-a910-4fa0-9ab7-33ed6eb3e31b",
    "email": "admin@sentinel.ai",
    "full_name": "Platform Admin",
    "role": "admin",
    "is_active": true,
    "employee_id": null
  },
  "error": null
}
```

---

## Command Center

### Dashboard aggregate

`GET /api/v1/dashboard`

```jsonc
// HTTP 200
{
  "data": {
    "generated_at": "2026-08-08T10:03:16.291981+00:00",
    "totals": {
      "employees": 500,
      "devices": 500,
      "cloud_assets": 300,
      "applications": 100,
      "vendors": 100,
      "policies": 100,
      "controls": 300,
      "risks": 300,
      "evidence": 500,
      "findings": 300,
      "reports": 100,
      "personal_data_records": 300,
      "consent_records": 500,
      "iam_records": 500,
      "... 1 more keys": "..."
    },
    "risks": {
      "total": 300,
      "critical": 45,
      "high": 100,
      "medium": 108,
      "low": 47,
      "open": 165,
      "by_severity": {
        "Critical": 45,
        "High": 100,
        "Medium": 108,
        "Low": 47
      },
      "by_status": {
        "Accepted": 45,
        "Closed": 40,
        "In Remediation": 85,
        "Mitigated": 50,
        "Open": 80
      },
      "by_likelihood": {
        "High": 88,
        "Low": 78,
        "Medium": 134
      },
      "by_department": {
        "Data & Analytics": 33,
        "Engineering": 26,
        "Finance": 25,
        "Human Resources": 32,
        "Information Security": 28,
        "Information Technology": 30,
        "Internal Audit": 30,
        "Legal & Compliance": 29,
        "Operations": 20,
        "Procurement": 21,
        "Risk Management": 26
      },
      "mapped_to_control": 300
    },
    "findings": {
      "total": 300,
      "open": 170,
      "critical_open": 18,
      "high_open": 43,
      "severe_open": 61,
      "with_evidence": 300,
      "by_severity": {
        "Critical": 30,
        "High": 79,
        "Medium": 99,
        "Low": 92
      },
      "by_status": {
        "Closed": 38,
        "In Progress": 84,
        "Open": 86,
        "Remediated": 48,
        "Risk Accepted": 44
      },
      "open_statuses": [
        "Open",
        "In Progress"
      ]
    },
    "evidence_coverage": {
      "total_controls": 300,
      "controls_with_evidence": 217,
      "controls_without_evidence": 83,
      "coverage_pct": 72.33,
      "total_evidence": 500,
      "verified_evidence": 387,
      "verified_pct": 77.4,
      "auto_collected": 200,
      "by_type": {
        "Access Review Report": 37,
        "Audit Trail Export": 38,
        "Backup Verification Report": 33,
        "Configuration Export": 35,
        "Encryption Configuration Proof": 40,
        "Incident Report": 29,
        "Log Extract": 34,
        "Penetration Test Report": 43,
        "Policy Document": 24,
        "Screenshot": 35,
        "Signed Attestation": 34,
        "System Configuration Snapshot": 31,
        "Training Completion Report": 37,
        "Vendor Assessment Report": 26,
        "... 1 more keys": "..."
      }
    },
    "compliance_coverage": {
      "total_policies": 100,
      "mandatory_policies": 84,
      "total_controls": 300,
      "controls_with_evidence": 217,
      "controls_with_open_findings": 128,
      "passed_controls": 172,
      "failed_controls": 128,
      "pass_rate_pct": 57.33,
      "mandatory_controls": 249,
      "mandatory_controls_with_evidence": 181,
      "policies_by_framework": {
        "ISO 27001": 27,
        "NIST": 15,
        "DPDP": 16,
        "SOC2": 16,
        "CIS Controls": 26
      },
      "controls_by_severity": {
        "Critical": 53,
        "High": 84,
        "Medium": 110,
        "Low": 53
      },
      "definitions": {
        "passed_control": "a control with zero findings in status Open or In Progress",
        "failed_control": "a control with at least one finding in status Open or In Progress"
      }
    },
    "framework_status": [
      {
        "framework": "CIS Controls",
        "total_policies": 26,
        "mandatory_policies": 21,
        "total_controls": 76,
        "controls_with_evidence": 56,
        "controls_with_open_findings": 37,
        "passed_controls": 39,
        "failed_controls": 37,
        "evidence_count": 127,
        "verified_evidence_count": 100,
        "evidence_coverage_pct": 73.68,
        "total_findings": 86,
        "open_findings": 50,
        "critical_findings": 9,
        "... 5 more keys": "..."
      },
      {
        "framework": "DPDP",
        "total_policies": 16,
        "mandatory_policies": 13,
        "total_controls": 53,
        "controls_with_evidence": 42,
        "controls_with_open_findings": 22,
        "passed_controls": 31,
        "failed_controls": 22,
        "evidence_count": 99,
        "verified_evidence_count": 78,
        "evidence_coverage_pct": 79.25,
        "total_findings": 62,
        "open_findings": 33,
        "critical_findings": 5,
        "... 5 more keys": "..."
      },
      "... 3 more items"
    ],
    "recent_audit_activity": {
      "total_events": 10000,
      "latest_event_at": "2026-08-07T23:48:07+00:00",
      "window": "7 days back from the most recent log timestamp in the dataset",
      "events_in_window": 790,
      "failures_in_window": 117,
      "total_failures": 1497,
      "high_risk_events": 14,
      "by_result": {
        "Failure": 1497,
        "Success": 8503
      },
      "top_actions": {
        "Login": 1484,
        "File Download": 526,
        "Password Change": 524,
        "File Delete": 521,
        "Record Viewed": 519,
        "Privilege Escalation Request": 515,
        "Permission Change": 511,
        "Data Export": 507
      },
      "recent": [
        {
          "log_id": "LOG6150833",
          "timestamp": "2026-08-07T23:48:07+00:00",
          "employee_id": "EMP0005",
          "application_id": "APP2350",
          "action": "MFA Challenge",
          "result": "Success",
          "risk_score": 10,
          "geo_location": "Hyderabad, India"
        },
        {
          "log_id": "LOG4304385",
          "timestamp": "2026-08-07T23:38:07+00:00",
          "employee_id": "EMP0315",
          "application_id": "APP4469",
          "action": "Failed Login Attempt",
          "result": "Failure",
          "risk_score": 48,
          "geo_location": "Mumbai, India"
        },
        "... 8 more items"
      ]
    },
    "asset_statistics": {
      "employees": {
        "total": 500,
        "active": 449,
        "by_status": {
          "Active": 449,
          "Disabled": 30,
          "Suspended": 21
        },
        "by_department": {
          "Customer Support": 48,
          "Data & Analytics": 29,
          "Engineering": 110,
          "Executive": 5,
          "Finance": 27,
          "Human Resources": 23,
          "Information Security": 34,
          "Information Technology": 45,
          "Internal Audit": 10,
          "Legal & Compliance": 14,
          "Marketing": 29,
          "Operations": 25,
          "Procurement": 12,
          "Product Management": 25,
          "... 2 more keys": "..."
        },
        "mfa_enabled": 385
      },
      "devices": {
        "total": 500,
        "compliant": 186,
        "compliance_pct": 37.2,
        "by_compliance_status": {
          "Compliant": 186,
          "Non-Compliant": 129,
          "Partially Compliant": 185
        },
        "by_risk_level": {
          "Critical": 31,
          "High": 68,
          "Medium": 157,
          "Low": 244
        },
        "by_type": {
          "Desktop": 82,
          "Laptop": 260,
          "Mobile Phone": 83,
          "Tablet": 75
        },
        "encrypted": 421,
        "edr_installed": 375
      },
      "cloud_assets": {
        "total": 300,
        "public_access": 30,
        "public_access_pct": 10.0,
        "encrypted": 210,
        "logging_enabled": 228,
        "by_provider": {
          "AWS": 141,
          "Azure": 104,
          "GCP": 55
        },
        "by_risk_level": {
          "Critical": 8,
          "High": 63,
          "Medium": 152,
          "Low": 77
        },
        "by_criticality": {
          "Critical": 40,
          "High": 93,
          "Medium": 116,
          "Low": 51
        }
      },
      "applications": {
        "total": 100,
        "internet_facing": 40,
        "uses_mfa": 54,
        "encrypted": 85,
        "by_risk_level": {
          "Critical": 10,
          "High": 23,
          "Medium": 47,
          "Low": 20
        },
        "by_data_classification": {
          "Public": 9,
          "Internal": 33,
          "Confidential": 44,
          "Restricted": 14
        }
      }
    },
    "vendor_risk": {
      "total": 100,
      "by_risk_rating": {
        "Critical": 7,
        "High": 29,
        "Medium": 41,
        "Low": 23
      },
      "iso27001_certified": 66,
      "soc2_certified": 55,
      "dpdp_compliant": 46,
      "no_certifications": 15,
      "contracts_expiring_90d": 10,
      "by_service_category": {
        "Data Analytics": 4,
        "Customer Support Tooling": 4,
        "Legal Services": 11,
        "Background Verification": 7,
        "Cloud Hosting": 5,
        "Payment Processing": 3,
        "Recruitment Services": 10,
        "Document Management": 2,
        "Logistics & Courier": 7,
        "Cybersecurity Services": 2,
        "IT Managed Services": 9,
        "Facilities Management": 9,
        "Software Development Outsourcing": 7,
        "Email & Collaboration": 5,
        "... 2 more keys": "..."
      },
      "note": "Vendors are an island dataset \u2014 no verified FK to risks or controls."
    },
    "privacy_statistics": {
      "personal_data_records": 300,
      "third_party_sharing": 81,
      "encrypted": 239,
      "consent_required": 184,
      "by_data_category": {
        "Authentication Credentials": 25,
        "Background Verification Records": 18,
        "Biometric Data (Fingerprint/Facial Recognition)": 19,
        "Customer Contact Information": 18,
        "Customer Financial Details (Payment Card Data)": 17,
        "Customer Support Interaction Records": 7,
        "Customer Transaction History": 15,
        "Device and IP Address Data": 20,
        "Employee Contact Information": 18,
        "Employee Financial Details (Salary, Bank Account)": 20,
        "Employee Government ID (PAN/Aadhaar)": 21,
        "Employee Personal Details (Name, DOB, Address)": 17,
        "Health and Medical Records": 13,
        "Job Applicant Resume Data": 15,
        "... 3 more keys": "..."
      },
      "consent_records": 500,
      "consent_given": 412,
      "consent_revoked": 50,
      "consent_expired": 149,
      "applications_with_personal_data": 93
    },
    "iam_statistics": {
      "total": 500,
      "privileged_accounts": 267,
      "mfa_enabled": 385,
      "privileged_without_mfa": 68,
      "inactive_over_90_days": 30,
      "by_role": {
        "DevOps Engineer": 35,
        "Engineering Manager": 26,
        "QA Tester": 26,
        "Developer": 23,
        "Sales User": 21,
        "Support Administrator": 18,
        "CRM Administrator": 18,
        "Support Agent": 16,
        "System Administrator": 15,
        "Support Team Lead": 14
      }
    },
    "trust_score": {
      "value": 61.3,
      "engine": "deterministic_phase1",
      "weights": {
        "control_evidence_coverage": 0.25,
        "finding_health": 0.2,
        "risk_health": 0.2,
        "asset_hygiene": 0.2,
        "identity_hygiene": 0.15
      },
      "components": {
        "control_evidence_coverage": 0.7233,
        "finding_health": 0.4333,
        "risk_health": 0.45,
        "asset_hygiene": 0.7055,
        "identity_hygiene": 0.7618
      },
      "formula": "100 * SUM(component * weight)",
      "note": "Deterministic Phase 1 score. Every component is a live row-count ratio from this database; the weights are fixed constants. This is NOT the Phase 2 AI scoring e... (+74 chars)"
    },
    "audit_readiness": {
      "value": 74.8,
      "engine": "deterministic_phase1",
      "weights": {
        "evidence_coverage": 0.4,
        "evidence_verification": 0.25,
        "mandatory_control_coverage": 0.2,
        "severe_finding_health": 0.15
      },
      "components": {
        "evidence_coverage": 0.7233,
        "evidence_verification": 0.774,
        "mandatory_control_coverage": 0.7269,
        "severe_finding_health": 0.7967
      },
      "formula": "100 * SUM(component * weight)",
      "note": "Deterministic Phase 1 score. Every component is a live row-count ratio from this database; the weights are fixed constants. This is NOT the Phase 2 AI scoring e... (+74 chars)"
    }
  },
  "error": null
}
```

### Dashboard with scores disabled

`GET /api/v1/dashboard?scores=off`

```jsonc
// HTTP 200
{
  "data": {
    "generated_at": "2026-08-08T10:03:16.408339+00:00",
    "totals": {
      "employees": 500,
      "devices": 500,
      "cloud_assets": 300,
      "applications": 100,
      "vendors": 100,
      "policies": 100,
      "controls": 300,
      "risks": 300,
      "evidence": 500,
      "findings": 300,
      "reports": 100,
      "personal_data_records": 300,
      "consent_records": 500,
      "iam_records": 500,
      "... 1 more keys": "..."
    },
    "risks": {
      "total": 300,
      "critical": 45,
      "high": 100,
      "medium": 108,
      "low": 47,
      "open": 165,
      "by_severity": {
        "Critical": 45,
        "High": 100,
        "Medium": 108,
        "Low": 47
      },
      "by_status": {
        "Accepted": 45,
        "Closed": 40,
        "In Remediation": 85,
        "Mitigated": 50,
        "Open": 80
      },
      "by_likelihood": {
        "High": 88,
        "Low": 78,
        "Medium": 134
      },
      "by_department": {
        "Data & Analytics": 33,
        "Engineering": 26,
        "Finance": 25,
        "Human Resources": 32,
        "Information Security": 28,
        "Information Technology": 30,
        "Internal Audit": 30,
        "Legal & Compliance": 29,
        "Operations": 20,
        "Procurement": 21,
        "Risk Management": 26
      },
      "mapped_to_control": 300
    },
    "findings": {
      "total": 300,
      "open": 170,
      "critical_open": 18,
      "high_open": 43,
      "severe_open": 61,
      "with_evidence": 300,
      "by_severity": {
        "Critical": 30,
        "High": 79,
        "Medium": 99,
        "Low": 92
      },
      "by_status": {
        "Closed": 38,
        "In Progress": 84,
        "Open": 86,
        "Remediated": 48,
        "Risk Accepted": 44
      },
      "open_statuses": [
        "Open",
        "In Progress"
      ]
    },
    "evidence_coverage": {
      "total_controls": 300,
      "controls_with_evidence": 217,
      "controls_without_evidence": 83,
      "coverage_pct": 72.33,
      "total_evidence": 500,
      "verified_evidence": 387,
      "verified_pct": 77.4,
      "auto_collected": 200,
      "by_type": {
        "Access Review Report": 37,
        "Audit Trail Export": 38,
        "Backup Verification Report": 33,
        "Configuration Export": 35,
        "Encryption Configuration Proof": 40,
        "Incident Report": 29,
        "Log Extract": 34,
        "Penetration Test Report": 43,
        "Policy Document": 24,
        "Screenshot": 35,
        "Signed Attestation": 34,
        "System Configuration Snapshot": 31,
        "Training Completion Report": 37,
        "Vendor Assessment Report": 26,
        "... 1 more keys": "..."
      }
    },
    "compliance_coverage": {
      "total_policies": 100,
      "mandatory_policies": 84,
      "total_controls": 300,
      "controls_with_evidence": 217,
      "controls_with_open_findings": 128,
      "passed_controls": 172,
      "failed_controls": 128,
      "pass_rate_pct": 57.33,
      "mandatory_controls": 249,
      "mandatory_controls_with_evidence": 181,
      "policies_by_framework": {
        "ISO 27001": 27,
        "NIST": 15,
        "DPDP": 16,
        "SOC2": 16,
        "CIS Controls": 26
      },
      "controls_by_severity": {
        "Critical": 53,
        "High": 84,
        "Medium": 110,
        "Low": 53
      },
      "definitions": {
        "passed_control": "a control with zero findings in status Open or In Progress",
        "failed_control": "a control with at least one finding in status Open or In Progress"
      }
    },
    "framework_status": [
      {
        "framework": "CIS Controls",
        "total_policies": 26,
        "mandatory_policies": 21,
        "total_controls": 76,
        "controls_with_evidence": 56,
        "controls_with_open_findings": 37,
        "passed_controls": 39,
        "failed_controls": 37,
        "evidence_count": 127,
        "verified_evidence_count": 100,
        "evidence_coverage_pct": 73.68,
        "total_findings": 86,
        "open_findings": 50,
        "critical_findings": 9,
        "... 5 more keys": "..."
      },
      {
        "framework": "DPDP",
        "total_policies": 16,
        "mandatory_policies": 13,
        "total_controls": 53,
        "controls_with_evidence": 42,
        "controls_with_open_findings": 22,
        "passed_controls": 31,
        "failed_controls": 22,
        "evidence_count": 99,
        "verified_evidence_count": 78,
        "evidence_coverage_pct": 79.25,
        "total_findings": 62,
        "open_findings": 33,
        "critical_findings": 5,
        "... 5 more keys": "..."
      },
      "... 3 more items"
    ],
    "recent_audit_activity": {
      "total_events": 10000,
      "latest_event_at": "2026-08-07T23:48:07+00:00",
      "window": "7 days back from the most recent log timestamp in the dataset",
      "events_in_window": 790,
      "failures_in_window": 117,
      "total_failures": 1497,
      "high_risk_events": 14,
      "by_result": {
        "Failure": 1497,
        "Success": 8503
      },
      "top_actions": {
        "Login": 1484,
        "File Download": 526,
        "Password Change": 524,
        "File Delete": 521,
        "Record Viewed": 519,
        "Privilege Escalation Request": 515,
        "Permission Change": 511,
        "Data Export": 507
      },
      "recent": [
        {
          "log_id": "LOG6150833",
          "timestamp": "2026-08-07T23:48:07+00:00",
          "employee_id": "EMP0005",
          "application_id": "APP2350",
          "action": "MFA Challenge",
          "result": "Success",
          "risk_score": 10,
          "geo_location": "Hyderabad, India"
        },
        {
          "log_id": "LOG4304385",
          "timestamp": "2026-08-07T23:38:07+00:00",
          "employee_id": "EMP0315",
          "application_id": "APP4469",
          "action": "Failed Login Attempt",
          "result": "Failure",
          "risk_score": 48,
          "geo_location": "Mumbai, India"
        },
        "... 8 more items"
      ]
    },
    "asset_statistics": {
      "employees": {
        "total": 500,
        "active": 449,
        "by_status": {
          "Active": 449,
          "Disabled": 30,
          "Suspended": 21
        },
        "by_department": {
          "Customer Support": 48,
          "Data & Analytics": 29,
          "Engineering": 110,
          "Executive": 5,
          "Finance": 27,
          "Human Resources": 23,
          "Information Security": 34,
          "Information Technology": 45,
          "Internal Audit": 10,
          "Legal & Compliance": 14,
          "Marketing": 29,
          "Operations": 25,
          "Procurement": 12,
          "Product Management": 25,
          "... 2 more keys": "..."
        },
        "mfa_enabled": 385
      },
      "devices": {
        "total": 500,
        "compliant": 186,
        "compliance_pct": 37.2,
        "by_compliance_status": {
          "Compliant": 186,
          "Non-Compliant": 129,
          "Partially Compliant": 185
        },
        "by_risk_level": {
          "Critical": 31,
          "High": 68,
          "Medium": 157,
          "Low": 244
        },
        "by_type": {
          "Desktop": 82,
          "Laptop": 260,
          "Mobile Phone": 83,
          "Tablet": 75
        },
        "encrypted": 421,
        "edr_installed": 375
      },
      "cloud_assets": {
        "total": 300,
        "public_access": 30,
        "public_access_pct": 10.0,
        "encrypted": 210,
        "logging_enabled": 228,
        "by_provider": {
          "AWS": 141,
          "Azure": 104,
          "GCP": 55
        },
        "by_risk_level": {
          "Critical": 8,
          "High": 63,
          "Medium": 152,
          "Low": 77
        },
        "by_criticality": {
          "Critical": 40,
          "High": 93,
          "Medium": 116,
          "Low": 51
        }
      },
      "applications": {
        "total": 100,
        "internet_facing": 40,
        "uses_mfa": 54,
        "encrypted": 85,
        "by_risk_level": {
          "Critical": 10,
          "High": 23,
          "Medium": 47,
          "Low": 20
        },
        "by_data_classification": {
          "Public": 9,
          "Internal": 33,
          "Confidential": 44,
          "Restricted": 14
        }
      }
    },
    "vendor_risk": {
      "total": 100,
      "by_risk_rating": {
        "Critical": 7,
        "High": 29,
        "Medium": 41,
        "Low": 23
      },
      "iso27001_certified": 66,
      "soc2_certified": 55,
      "dpdp_compliant": 46,
      "no_certifications": 15,
      "contracts_expiring_90d": 10,
      "by_service_category": {
        "Data Analytics": 4,
        "Customer Support Tooling": 4,
        "Legal Services": 11,
        "Background Verification": 7,
        "Cloud Hosting": 5,
        "Payment Processing": 3,
        "Recruitment Services": 10,
        "Document Management": 2,
        "Logistics & Courier": 7,
        "Cybersecurity Services": 2,
        "IT Managed Services": 9,
        "Facilities Management": 9,
        "Software Development Outsourcing": 7,
        "Email & Collaboration": 5,
        "... 2 more keys": "..."
      },
      "note": "Vendors are an island dataset \u2014 no verified FK to risks or controls."
    },
    "privacy_statistics": {
      "personal_data_records": 300,
      "third_party_sharing": 81,
      "encrypted": 239,
      "consent_required": 184,
      "by_data_category": {
        "Authentication Credentials": 25,
        "Background Verification Records": 18,
        "Biometric Data (Fingerprint/Facial Recognition)": 19,
        "Customer Contact Information": 18,
        "Customer Financial Details (Payment Card Data)": 17,
        "Customer Support Interaction Records": 7,
        "Customer Transaction History": 15,
        "Device and IP Address Data": 20,
        "Employee Contact Information": 18,
        "Employee Financial Details (Salary, Bank Account)": 20,
        "Employee Government ID (PAN/Aadhaar)": 21,
        "Employee Personal Details (Name, DOB, Address)": 17,
        "Health and Medical Records": 13,
        "Job Applicant Resume Data": 15,
        "... 3 more keys": "..."
      },
      "consent_records": 500,
      "consent_given": 412,
      "consent_revoked": 50,
      "consent_expired": 149,
      "applications_with_personal_data": 93
    },
    "iam_statistics": {
      "total": 500,
      "privileged_accounts": 267,
      "mfa_enabled": 385,
      "privileged_without_mfa": 68,
      "inactive_over_90_days": 30,
      "by_role": {
        "DevOps Engineer": 35,
        "Engineering Manager": 26,
        "QA Tester": 26,
        "Developer": 23,
        "Sales User": 21,
        "Support Administrator": 18,
        "CRM Administrator": 18,
        "Support Agent": 16,
        "System Administrator": 15,
        "Support Team Lead": 14
      }
    },
    "trust_score": {
      "value": null,
      "status": "pending Phase 2 scoring engine"
    },
    "audit_readiness": {
      "value": null,
      "status": "pending Phase 2 scoring engine"
    }
  },
  "error": null
}
```

---

## Organization Graph

### Full graph

`GET /api/v1/organization/graph?scope=full&limit_employees=25`

```jsonc
// HTTP 200
{
  "data": {
    "nodes": [
      {
        "id": "EMP0001",
        "type": "employee",
        "label": "Harish Arora",
        "data": {
          "department": "Sales",
          "designation": "Sales Manager",
          "account_status": "Active",
          "mfa_enabled": false,
          "manager_id": "EMP0231"
        }
      },
      {
        "id": "EMP0002",
        "type": "employee",
        "label": "Sneha Thompson",
        "data": {
          "department": "Engineering",
          "designation": "DevOps Engineer",
          "account_status": "Active",
          "mfa_enabled": true,
          "manager_id": "EMP0408"
        }
      },
      "... 1593 more items"
    ],
    "edges": [
      {
        "id": "EMP0003->EMP0022:MANAGES",
        "source": "EMP0003",
        "target": "EMP0022",
        "relation": "MANAGES"
      },
      {
        "id": "EMP0010->DEV0010:USES_DEVICE",
        "source": "EMP0010",
        "target": "DEV0010",
        "relation": "USES_DEVICE"
      },
      "... 1769 more items"
    ],
    "meta": {
      "scope": "full",
      "node_count": 1595,
      "edge_count": 1771,
      "node_types": {
        "employee": 25,
        "device": 25,
        "iam": 25,
        "cloud_asset": 20,
        "policy": 100,
        "control": 300,
        "evidence": 500,
        "finding": 300,
        "risk": 300
      },
      "edge_types": {
        "MANAGES": 1,
        "USES_DEVICE": 25,
        "HAS_IDENTITY": 25,
        "OWNS_ASSET": 20,
        "DEFINES": 300,
        "HAS_EVIDENCE": 500,
        "HAS_FINDING": 300,
        "SUPPORTED_BY": 300,
        "MITIGATES": 300
      },
      "caps": {
        "employees": {
          "returned": 25,
          "total": 500
        }
      },
      "relationship_sources": {
        "MANAGES": "employees.manager_id",
        "USES_DEVICE": "devices.employee_id",
        "HAS_IDENTITY": "iam_records.employee_id",
        "OWNS_ASSET": "cloud_assets.owner_employee_id",
        "CONSENTED_TO": "consent_records.employee_id/application_id",
        "ACCESSED": "audit_logs.employee_id/application_id",
        "DEFINES": "controls.policy_id",
        "HAS_EVIDENCE": "evidence.control_id",
        "HAS_FINDING": "findings.control_id",
        "SUPPORTED_BY": "findings.evidence_id",
        "MITIGATES": "risks.mapped_control_id",
        "PROCESSES": "personal_data_inventory.application_id"
      }
    }
  },
  "error": null
}
```

### Focused on one employee

`GET /api/v1/organization/graph?scope=org&employee_id=EMP0001`

```jsonc
// HTTP 200
{
  "data": {
    "nodes": [
      {
        "id": "EMP0001",
        "type": "employee",
        "label": "Harish Arora",
        "data": {
          "department": "Sales",
          "designation": "Sales Manager",
          "account_status": "Active",
          "mfa_enabled": false,
          "manager_id": "EMP0231"
        }
      },
      {
        "id": "EMP0003",
        "type": "employee",
        "label": "Fang Liu",
        "data": {
          "department": "Product Management",
          "designation": "Senior Product Manager",
          "account_status": "Active",
          "mfa_enabled": true,
          "manager_id": "EMP0231"
        }
      },
      "... 29 more items"
    ],
    "edges": [
      {
        "id": "EMP0231->EMP0001:MANAGES",
        "source": "EMP0231",
        "target": "EMP0001",
        "relation": "MANAGES"
      },
      {
        "id": "EMP0231->EMP0003:MANAGES",
        "source": "EMP0231",
        "target": "EMP0003",
        "relation": "MANAGES"
      },
      "... 28 more items"
    ],
    "meta": {
      "scope": "org",
      "node_count": 31,
      "edge_count": 30,
      "node_types": {
        "employee": 10,
        "device": 10,
        "iam": 10,
        "cloud_asset": 1
      },
      "edge_types": {
        "MANAGES": 9,
        "USES_DEVICE": 10,
        "HAS_IDENTITY": 10,
        "OWNS_ASSET": 1
      },
      "caps": {
        "employees": {
          "returned": 10,
          "total": 500
        }
      },
      "relationship_sources": {
        "MANAGES": "employees.manager_id",
        "USES_DEVICE": "devices.employee_id",
        "HAS_IDENTITY": "iam_records.employee_id",
        "OWNS_ASSET": "cloud_assets.owner_employee_id",
        "CONSENTED_TO": "consent_records.employee_id/application_id",
        "ACCESSED": "audit_logs.employee_id/application_id",
        "DEFINES": "controls.policy_id",
        "HAS_EVIDENCE": "evidence.control_id",
        "HAS_FINDING": "findings.control_id",
        "SUPPORTED_BY": "findings.evidence_id",
        "MITIGATES": "risks.mapped_control_id",
        "PROCESSES": "personal_data_inventory.application_id"
      }
    }
  },
  "error": null
}
```

---

## Frameworks

### All frameworks

`GET /api/v1/frameworks`

```jsonc
// HTTP 200
{
  "data": [
    {
      "framework": "CIS Controls",
      "total_policies": 26,
      "mandatory_policies": 21,
      "total_controls": 76,
      "controls_with_evidence": 56,
      "controls_with_open_findings": 37,
      "passed_controls": 39,
      "failed_controls": 37,
      "evidence_count": 127,
      "verified_evidence_count": 100,
      "evidence_coverage_pct": 73.68,
      "total_findings": 86,
      "open_findings": 50,
      "critical_findings": 9,
      "... 5 more keys": "..."
    },
    {
      "framework": "DPDP",
      "total_policies": 16,
      "mandatory_policies": 13,
      "total_controls": 53,
      "controls_with_evidence": 42,
      "controls_with_open_findings": 22,
      "passed_controls": 31,
      "failed_controls": 22,
      "evidence_count": 99,
      "verified_evidence_count": 78,
      "evidence_coverage_pct": 79.25,
      "total_findings": 62,
      "open_findings": 33,
      "critical_findings": 5,
      "... 5 more keys": "..."
    },
    "... 3 more items"
  ],
  "meta": {
    "count": 5,
    "derivation": "policies -> controls -> evidence/findings, grouped by policies.framework",
    "note": "Framework is a shared vocabulary across policies and reports, not a table."
  },
  "error": null
}
```

### One framework

`GET /api/v1/frameworks/ISO%2027001`

```jsonc
// HTTP 200
{
  "data": {
    "framework": "ISO 27001",
    "total_policies": 27,
    "mandatory_policies": 25,
    "total_controls": 78,
    "controls_with_evidence": 53,
    "controls_with_open_findings": 39,
    "passed_controls": 39,
    "failed_controls": 39,
    "evidence_count": 123,
    "verified_evidence_count": 95,
    "evidence_coverage_pct": 67.95,
    "total_findings": 78,
    "open_findings": 50,
    "critical_findings": 6,
    "... 5 more keys": "..."
  },
  "error": null
}
```

---

## Investigations / Risk Center

### Risk list (filtered)

`GET /api/v1/risks?severity=Critical&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "risk_id": "RISK-11085",
      "risk_name": "Phishing-Induced Credential Compromise",
      "description": "Employees without adequate security awareness training are susceptible to phishing attacks.",
      "business_impact": "Account takeover and lateral movement",
      "likelihood": "High",
      "severity": "Critical",
      "owner_department": "Data & Analytics",
      "mapped_control_id": "CTRL-84039",
      "current_status": "Closed"
    },
    {
      "risk_id": "RISK-13889",
      "risk_name": "Insufficient Vendor Contract Security Clauses",
      "description": "Vendor contracts lacking explicit data protection obligations weaken enforceability of security expectations.",
      "business_impact": "Limited recourse in case of vendor breach",
      "likelihood": "Medium",
      "severity": "Critical",
      "owner_department": "Engineering",
      "mapped_control_id": "CTRL-55962",
      "current_status": "Open"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 45,
    "total_pages": 23
  },
  "error": null
}
```

### Risk investigation detail

`GET /api/v1/risks/RISK-10244`

```jsonc
// HTTP 200
{
  "data": {
    "risk_id": "RISK-10244",
    "risk_name": "Unauthorized Access to Production Systems",
    "description": "Weak access controls could allow unauthorized personnel to reach production environments and sensitive data.",
    "business_impact": "Data breach and regulatory penalties",
    "likelihood": "High",
    "severity": "Medium",
    "owner_department": "Human Resources",
    "mapped_control_id": "CTRL-42825",
    "current_status": "In Remediation",
    "control": {
      "control_id": "CTRL-42825",
      "policy_id": "POL-SOC2-945",
      "control_name": "Breach Notification Timeliness",
      "description": "Notify affected parties and regulators within required timeframes following a breach",
      "severity": "Critical",
      "automation_possible": false,
      "evidence_required": true
    },
    "policy": {
      "policy_id": "POL-SOC2-945",
      "policy_name": "Incident Handling Policy",
      "framework": "SOC2",
      "category": "Incident Response",
      "version": "2.0",
      "owner_department": "Information Security",
      "mandatory": false
    },
    "findings": [
      {
        "finding_id": "FIND-58174",
        "control_id": "CTRL-42825",
        "severity": "High",
        "description": "Vendor security certification expired or missing: The associated third-party vendor's security certification could not be verified as current.",
        "evidence_id": "EVD-403326",
        "recommendation": "Obtain updated certification from the vendor or escalate to procurement for contract review.",
        "status": "In Progress"
      }
    ],
    "evidence": [
      {
        "evidence_id": "EVD-641026",
        "control_id": "CTRL-42825",
        "evidence_type": "System Configuration Snapshot",
        "evidence_location": "evidence-repo/snapshots/CTRL-42825-2113.json",
        "collected_date": "2026-05-03",
        "verified": false,
        "collected_automatically": false
      },
      {
        "evidence_id": "EVD-694434",
        "control_id": "CTRL-42825",
        "evidence_type": "Signed Attestation",
        "evidence_location": "evidence-repo/attestations/CTRL-42825-4632.pdf",
        "collected_date": "2026-06-12",
        "verified": false,
        "collected_automatically": false
      },
      "... 1 more items"
    ],
    "open_finding_count": 0,
    "... 1 more keys": "..."
  },
  "error": null
}
```

---

## Findings

### Findings list (filtered)

`GET /api/v1/findings?status=Open&severity=High&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "finding_id": "FIND-14356",
      "control_id": "CTRL-23452",
      "severity": "High",
      "description": "Segregation of duties violation identified: A single user was found with conflicting permissions that violate segregation of duties requirements.",
      "evidence_id": "EVD-214814",
      "recommendation": "Revoke conflicting privileges and implement approval workflow for sensitive role combinations.",
      "status": "Open"
    },
    {
      "finding_id": "FIND-16056",
      "control_id": "CTRL-85715",
      "severity": "High",
      "description": "Vendor security certification expired or missing: The associated third-party vendor's security certification could not be verified as current.",
      "evidence_id": "EVD-765049",
      "recommendation": "Obtain updated certification from the vendor or escalate to procurement for contract review.",
      "status": "Open"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 22,
    "total_pages": 11
  },
  "error": null
}
```

### Finding detail

`GET /api/v1/findings/FIND-10336`

```jsonc
// HTTP 200
{
  "data": {
    "finding_id": "FIND-10336",
    "control_id": "CTRL-45167",
    "severity": "Medium",
    "description": "Consent records incomplete for processed data: Personal data processing activity was identified without a corresponding valid consent record.",
    "evidence_id": "EVD-190922",
    "recommendation": "Reconcile data processing activities against consent records and remediate gaps.",
    "status": "Closed",
    "control": {
      "control_id": "CTRL-45167",
      "policy_id": "POL-ISO-971",
      "control_name": "Firewall Rule Review",
      "description": "Review firewall rule sets quarterly to remove unused or overly permissive rules",
      "severity": "Low",
      "automation_possible": false,
      "evidence_required": true
    },
    "policy": {
      "policy_id": "POL-ISO-971",
      "policy_name": "Communications Security Policy",
      "framework": "ISO 27001",
      "category": "Network Security",
      "version": "2.0",
      "owner_department": "Risk Management",
      "mandatory": true
    },
    "evidence": {
      "evidence_id": "EVD-190922",
      "control_id": "CTRL-45167",
      "evidence_type": "Penetration Test Report",
      "evidence_location": "evidence-repo/pentest/CTRL-45167-2040.pdf",
      "collected_date": "2026-07-17",
      "verified": true,
      "collected_automatically": false
    },
    "related_risks": [
      {
        "risk_id": "RISK-22766",
        "risk_name": "Excessive Data Retention Beyond Policy",
        "description": "Personal or sensitive data retained beyond defined retention periods increases breach exposure and compliance risk.",
        "business_impact": "Regulatory non-compliance",
        "likelihood": "Medium",
        "severity": "High",
        "owner_department": "Operations",
        "mapped_control_id": "CTRL-45167",
        "current_status": "Mitigated"
      }
    ]
  },
  "error": null
}
```

---

## Evidence Repository

### Evidence list

`GET /api/v1/evidence?verified=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "evidence_id": "EVD-100113",
      "control_id": "CTRL-58193",
      "evidence_type": "Training Completion Report",
      "evidence_location": "evidence-repo/training/CTRL-58193-3539.xlsx",
      "collected_date": "2026-05-17",
      "verified": true,
      "collected_automatically": false
    },
    {
      "evidence_id": "EVD-102577",
      "control_id": "CTRL-66319",
      "evidence_type": "Encryption Configuration Proof",
      "evidence_location": "evidence-repo/encryption/CTRL-66319-9148.json",
      "collected_date": "2026-03-21",
      "verified": true,
      "collected_automatically": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 387,
    "total_pages": 194
  },
  "error": null
}
```

### Evidence detail

`GET /api/v1/evidence/EVD-100113`

```jsonc
// HTTP 200
{
  "data": {
    "evidence_id": "EVD-100113",
    "control_id": "CTRL-58193",
    "evidence_type": "Training Completion Report",
    "evidence_location": "evidence-repo/training/CTRL-58193-3539.xlsx",
    "collected_date": "2026-05-17",
    "verified": true,
    "collected_automatically": false,
    "control": {
      "control_id": "CTRL-58193",
      "policy_id": "POL-DPDP-483",
      "control_name": "Incident Response Plan Testing",
      "description": "Test the incident response plan through tabletop exercises at least annually",
      "severity": "Medium",
      "automation_possible": true,
      "evidence_required": true
    },
    "policy": {
      "policy_id": "POL-DPDP-483",
      "policy_name": "Data Breach Notification Policy",
      "framework": "DPDP",
      "category": "Incident Response",
      "version": "3.0",
      "owner_department": "Information Security",
      "mandatory": true
    },
    "findings": [],
    "related_risks": []
  },
  "error": null
}
```

---

## Policies & Controls

### Policies list

`GET /api/v1/policies?framework=DPDP&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "policy_id": "POL-DPDP-186",
      "policy_name": "Personal Data Processing Policy",
      "framework": "DPDP",
      "category": "Data Privacy",
      "version": "1.0",
      "owner_department": "Legal & Compliance",
      "mandatory": false
    },
    {
      "policy_id": "POL-DPDP-188",
      "policy_name": "Children's Data Protection Policy",
      "framework": "DPDP",
      "category": "Data Privacy",
      "version": "1.2",
      "owner_department": "Information Security",
      "mandatory": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 16,
    "total_pages": 8
  },
  "error": null
}
```

### Policy detail

`GET /api/v1/policies/POL-CIS-174`

```jsonc
// HTTP 200
{
  "data": {
    "policy_id": "POL-CIS-174",
    "policy_name": "Incident Response Management Policy",
    "framework": "CIS Controls",
    "category": "Incident Response",
    "version": "3.0",
    "owner_department": "Information Technology",
    "mandatory": true,
    "controls": [
      {
        "control_id": "CTRL-84531",
        "policy_id": "POL-CIS-174",
        "control_name": "Incident Response Plan Testing",
        "description": "Test the incident response plan through tabletop exercises at least annually",
        "severity": "Low",
        "automation_possible": true,
        "evidence_required": false
      },
      {
        "control_id": "CTRL-87329",
        "policy_id": "POL-CIS-174",
        "control_name": "Incident Response Plan Testing",
        "description": "Test the incident response plan through tabletop exercises at least annually",
        "severity": "Critical",
        "automation_possible": false,
        "evidence_required": true
      },
      "... 1 more items"
    ],
    "control_count": 3
  },
  "error": null
}
```

### Controls list

`GET /api/v1/controls?severity=High&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "control_id": "CTRL-11507",
      "policy_id": "POL-SOC2-732",
      "control_name": "Breach Notification Timeliness",
      "description": "Notify affected parties and regulators within required timeframes following a breach",
      "severity": "High",
      "automation_possible": true,
      "evidence_required": true
    },
    {
      "control_id": "CTRL-11690",
      "policy_id": "POL-DPDP-186",
      "control_name": "Data Minimization Practices",
      "description": "Limit collection of personal data to what is necessary for stated purposes",
      "severity": "High",
      "automation_possible": true,
      "evidence_required": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 84,
    "total_pages": 42
  },
  "error": null
}
```

### Control detail

`GET /api/v1/controls/CTRL-10128`

```jsonc
// HTTP 200
{
  "data": {
    "control_id": "CTRL-10128",
    "policy_id": "POL-ISO-660",
    "control_name": "Dependency Vulnerability Scanning",
    "description": "Scan third-party dependencies for known vulnerabilities before release",
    "severity": "Medium",
    "automation_possible": false,
    "evidence_required": true,
    "policy": {
      "policy_id": "POL-ISO-660",
      "policy_name": "System Acquisition, Development and Maintenance Policy",
      "framework": "ISO 27001",
      "category": "Secure Development",
      "version": "2.0",
      "owner_department": "Risk Management",
      "mandatory": false
    },
    "evidence": [
      {
        "evidence_id": "EVD-989477",
        "control_id": "CTRL-10128",
        "evidence_type": "Screenshot",
        "evidence_location": "evidence-repo/screenshots/CTRL-10128-6319.png",
        "collected_date": "2026-02-15",
        "verified": true,
        "collected_automatically": false
      },
      {
        "evidence_id": "EVD-347441",
        "control_id": "CTRL-10128",
        "evidence_type": "Backup Verification Report",
        "evidence_location": "evidence-repo/backups/CTRL-10128-5150.pdf",
        "collected_date": "2026-07-12",
        "verified": true,
        "collected_automatically": true
      }
    ],
    "findings": [],
    "risks": [
      {
        "risk_id": "RISK-35820",
        "risk_name": "Excessive Data Retention Beyond Policy",
        "description": "Personal or sensitive data retained beyond defined retention periods increases breach exposure and compliance risk.",
        "business_impact": "Regulatory non-compliance",
        "likelihood": "High",
        "severity": "Critical",
        "owner_department": "Information Security",
        "mapped_control_id": "CTRL-10128",
        "current_status": "In Remediation"
      }
    ]
  },
  "error": null
}
```

---

## People & Assets

### Employees list

`GET /api/v1/employees?department=Engineering&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "employee_id": "EMP0002",
      "first_name": "Sneha",
      "last_name": "Thompson",
      "email": "sneha.thompson@meridianfintech.example",
      "department": "Engineering",
      "designation": "DevOps Engineer",
      "manager_id": "EMP0408",
      "office_location": "Hyderabad, IN",
      "employment_type": "Part-Time",
      "joining_date": "2026-04-29",
      "password_length": 10,
      "password_last_changed": "2026-06-27",
      "mfa_enabled": true,
      "account_status": "Active",
      "... 2 more keys": "..."
    },
    {
      "employee_id": "EMP0005",
      "first_name": "Rekha",
      "last_name": "Wu",
      "email": "rekha.wu@meridianfintech.example",
      "department": "Engineering",
      "designation": "Principal Engineer",
      "manager_id": "EMP0145",
      "office_location": "Mumbai, IN",
      "employment_type": "Contract",
      "joining_date": "2021-04-22",
      "password_length": 16,
      "password_last_changed": "2022-11-27",
      "mfa_enabled": true,
      "account_status": "Active",
      "... 2 more keys": "..."
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 110,
    "total_pages": 55
  },
  "error": null
}
```

### Employee 360 detail

`GET /api/v1/employees/EMP0001`

```jsonc
// HTTP 200
{
  "data": {
    "employee_id": "EMP0001",
    "first_name": "Harish",
    "last_name": "Arora",
    "email": "harish.arora@meridianfintech.example",
    "department": "Sales",
    "designation": "Sales Manager",
    "manager_id": "EMP0231",
    "office_location": "Bengaluru, IN",
    "employment_type": "Part-Time",
    "joining_date": "2020-11-21",
    "password_length": 8,
    "password_last_changed": "2025-10-30",
    "mfa_enabled": false,
    "account_status": "Active",
    "... 8 more keys": "..."
  },
  "error": null
}
```

### Identity & access

`GET /api/v1/iam?privileged_account=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "iam_user_id": "USR10098",
      "employee_id": "EMP0300",
      "role": "IT Manager",
      "privileges": "Admin: IT Systems; Approve: Access Requests",
      "privileged_account": true,
      "mfa_enabled": true,
      "inactive_days": 23,
      "last_privilege_review": "2026-05-24"
    },
    {
      "iam_user_id": "USR10398",
      "employee_id": "EMP0041",
      "role": "System Administrator",
      "privileges": "Admin: Servers; Admin: Backup Systems",
      "privileged_account": true,
      "mfa_enabled": true,
      "inactive_days": 70,
      "last_privilege_review": "2025-10-11"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 267,
    "total_pages": 134
  },
  "error": null
}
```

### Devices

`GET /api/v1/devices?compliance_status=Non-Compliant&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "device_id": "DEV0002",
      "employee_id": "EMP0002",
      "device_type": "Desktop",
      "operating_system": "Windows",
      "os_version": "10 Enterprise 22H2",
      "encryption_enabled": false,
      "firewall_enabled": true,
      "antivirus_installed": true,
      "edr_installed": true,
      "compliance_status": "Non-Compliant",
      "risk_level": "High",
      "last_patch_date": "2026-04-30"
    },
    {
      "device_id": "DEV0007",
      "employee_id": "EMP0007",
      "device_type": "Laptop",
      "operating_system": "macOS",
      "os_version": "Sonoma 14.5",
      "encryption_enabled": true,
      "firewall_enabled": true,
      "antivirus_installed": false,
      "edr_installed": false,
      "compliance_status": "Non-Compliant",
      "risk_level": "Critical",
      "last_patch_date": "2026-04-15"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 129,
    "total_pages": 65
  },
  "error": null
}
```

### Device detail

`GET /api/v1/devices/DEV0001`

```jsonc
// HTTP 200
{
  "data": {
    "device_id": "DEV0001",
    "employee_id": "EMP0001",
    "device_type": "Mobile Phone",
    "operating_system": "iOS",
    "os_version": "17.4",
    "encryption_enabled": false,
    "firewall_enabled": true,
    "antivirus_installed": true,
    "edr_installed": true,
    "compliance_status": "Partially Compliant",
    "risk_level": "Medium",
    "last_patch_date": "2026-06-09"
  },
  "error": null
}
```

### Applications

`GET /api/v1/applications?internet_facing=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "application_id": "APP1029",
      "application_name": "IAM Gateway 2",
      "owner_department": "Information Security",
      "authentication_method": "Azure AD SSO",
      "uses_mfa": true,
      "encryption_enabled": true,
      "data_classification": "Internal",
      "internet_facing": true,
      "risk_level": "Medium"
    },
    {
      "application_id": "APP1166",
      "application_name": "EmailBlast Console 2",
      "owner_department": "Marketing",
      "authentication_method": "Azure AD SSO",
      "uses_mfa": true,
      "encryption_enabled": true,
      "data_classification": "Confidential",
      "internet_facing": true,
      "risk_level": "Medium"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 40,
    "total_pages": 20
  },
  "error": null
}
```

### Application detail

`GET /api/v1/applications/APP1029`

```jsonc
// HTTP 200
{
  "data": {
    "application_id": "APP1029",
    "application_name": "IAM Gateway 2",
    "owner_department": "Information Security",
    "authentication_method": "Azure AD SSO",
    "uses_mfa": true,
    "encryption_enabled": true,
    "data_classification": "Internal",
    "internet_facing": true,
    "risk_level": "Medium",
    "personal_data_records": [
      {
        "data_id": "DPDP-66360",
        "application_id": "APP1029",
        "data_category": "Customer Transaction History",
        "purpose_of_processing": "Employee Onboarding",
        "retention_period": "5 Years",
        "third_party_sharing": false,
        "encryption_enabled": true,
        "consent_required": true
      },
      {
        "data_id": "DPDP-47929",
        "application_id": "APP1029",
        "data_category": "Device and IP Address Data",
        "purpose_of_processing": "Performance Management",
        "retention_period": "7 Years",
        "third_party_sharing": false,
        "encryption_enabled": false,
        "consent_required": false
      },
      "... 2 more items"
    ],
    "consent_records": [
      {
        "consent_id": "CNS-484525",
        "employee_id": "EMP0373",
        "application_id": "APP1029",
        "consent_given": true,
        "consent_date": "2025-11-18",
        "expiry_date": "2028-08-10",
        "revoked": false
      },
      {
        "consent_id": "CNS-302393",
        "employee_id": "EMP0139",
        "application_id": "APP1029",
        "consent_given": false,
        "consent_date": "2024-02-12",
        "expiry_date": "2025-04-23",
        "revoked": false
      },
      "... 2 more items"
    ],
    "recent_activity": [
      {
        "log_id": "LOG7459071",
        "timestamp": "2026-08-07T21:15:09Z",
        "employee_id": "EMP0420",
        "application_id": "APP1029",
        "action": "API Key Created",
        "ip_address": "103.21.58.77",
        "geo_location": "Hyderabad, India",
        "result": "Success",
        "risk_score": 18
      },
      {
        "log_id": "LOG4488648",
        "timestamp": "2026-08-07T11:35:10Z",
        "employee_id": "EMP0036",
        "application_id": "APP1029",
        "action": "Privilege Escalation Request",
        "ip_address": "115.96.45.179",
        "geo_location": "Chennai, India",
        "result": "Success",
        "risk_score": 24
      },
      "... 18 more items"
    ]
  },
  "error": null
}
```

### Cloud assets

`GET /api/v1/cloud-assets?public_access=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "resource_id": "AWS-RES-11327",
      "cloud_provider": "AWS",
      "resource_type": "ELB Load Balancer",
      "region": "us-east-1",
      "owner_employee_id": "EMP0454",
      "public_access": true,
      "encryption_enabled": true,
      "logging_enabled": true,
      "criticality": "Medium",
      "risk_level": "Medium"
    },
    {
      "resource_id": "AWS-RES-15640",
      "cloud_provider": "AWS",
      "resource_type": "EC2 Instance",
      "region": "ap-southeast-1",
      "owner_employee_id": "EMP0254",
      "public_access": true,
      "encryption_enabled": false,
      "logging_enabled": true,
      "criticality": "Medium",
      "risk_level": "High"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 30,
    "total_pages": 15
  },
  "error": null
}
```

---

## Third-Party Vendors

### Vendors list

`GET /api/v1/vendors?risk_rating=Critical&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "vendor_id": "VEN1110",
      "vendor_name": "Sentinel Group",
      "service_category": "Logistics & Courier",
      "iso27001_certified": false,
      "soc2_certified": false,
      "dpdp_compliant": false,
      "risk_rating": "Critical",
      "contract_expiry": "2028-04-10"
    },
    {
      "vendor_id": "VEN2951",
      "vendor_name": "Bluewave Data Services",
      "service_category": "Software Development Outsourcing",
      "iso27001_certified": false,
      "soc2_certified": false,
      "dpdp_compliant": false,
      "risk_rating": "Critical",
      "contract_expiry": "2028-11-09"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 7,
    "total_pages": 4
  },
  "error": null
}
```

### Vendor detail

`GET /api/v1/vendors/VEN1000`

```jsonc
// HTTP 200
{
  "data": {
    "vendor_id": "VEN1000",
    "vendor_name": "Northgate Labs",
    "service_category": "Background Verification",
    "iso27001_certified": true,
    "soc2_certified": true,
    "dpdp_compliant": true,
    "risk_rating": "Medium",
    "contract_expiry": "2027-02-05"
  },
  "error": null
}
```

---

## DPDP / Privacy

### Personal data inventory

`GET /api/v1/dpdp/personal-data?third_party_sharing=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "data_id": "DPDP-11306",
      "application_id": "APP6784",
      "data_category": "Employee Contact Information",
      "purpose_of_processing": "Performance Management",
      "retention_period": "1 Year",
      "third_party_sharing": true,
      "encryption_enabled": true,
      "consent_required": false
    },
    {
      "data_id": "DPDP-12554",
      "application_id": "APP7088",
      "data_category": "Marketing Preference Data",
      "purpose_of_processing": "Payment Processing",
      "retention_period": "6 Months",
      "third_party_sharing": true,
      "encryption_enabled": true,
      "consent_required": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 81,
    "total_pages": 41
  },
  "error": null
}
```

### Consent records

`GET /api/v1/dpdp/consents?revoked=true&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "consent_id": "CNS-101609",
      "employee_id": "EMP0442",
      "application_id": "APP8967",
      "consent_given": true,
      "consent_date": "2026-03-25",
      "expiry_date": "2028-04-06",
      "revoked": true
    },
    {
      "consent_id": "CNS-109546",
      "employee_id": "EMP0421",
      "application_id": "APP1700",
      "consent_given": true,
      "consent_date": "2025-01-11",
      "expiry_date": "2026-01-27",
      "revoked": true
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 50,
    "total_pages": 25
  },
  "error": null
}
```

---

## Audit Logs

### Audit logs (date range + risk filter)

`GET /api/v1/audit-logs?date_from=2026-07-01&date_to=2026-07-31&min_risk_score=60&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "log_id": "LOG9719223",
      "timestamp": "2026-07-01T03:56:44Z",
      "employee_id": "EMP0240",
      "application_id": "APP5830",
      "action": "User Account Disabled",
      "ip_address": "185.220.101.15",
      "geo_location": "Unknown Location",
      "result": "Success",
      "risk_score": 60
    },
    {
      "log_id": "LOG1139140",
      "timestamp": "2026-07-01T04:13:03Z",
      "employee_id": "EMP0345",
      "application_id": "APP6532",
      "action": "Failed Login Attempt",
      "ip_address": "85.25.67.47",
      "geo_location": "Frankfurt, Germany",
      "result": "Failure",
      "risk_score": 69
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 27,
    "total_pages": 14
  },
  "error": null
}
```

### Audit logs (failures)

`GET /api/v1/audit-logs?result=Failure&sort=-timestamp&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "log_id": "LOG4304385",
      "timestamp": "2026-08-07T23:38:07Z",
      "employee_id": "EMP0315",
      "application_id": "APP4469",
      "action": "Failed Login Attempt",
      "ip_address": "223.190.12.240",
      "geo_location": "Mumbai, India",
      "result": "Failure",
      "risk_score": 48
    },
    {
      "log_id": "LOG4963185",
      "timestamp": "2026-08-07T23:21:48Z",
      "employee_id": "EMP0046",
      "application_id": "APP8952",
      "action": "Failed Login Attempt",
      "ip_address": "103.21.58.19",
      "geo_location": "Hyderabad, India",
      "result": "Failure",
      "risk_score": 39
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 1497,
    "total_pages": 749
  },
  "error": null
}
```

---

## Reports

### Reports list

`GET /api/v1/reports?framework=SOC2&page_size=2`

```jsonc
// HTTP 200
{
  "data": [
    {
      "report_id": "RPT-16761",
      "framework": "SOC2",
      "generated_date": "2026-05-11",
      "overall_score": 61,
      "critical_findings": 1,
      "high_findings": 3,
      "medium_findings": 3,
      "low_findings": 0,
      "compliance_status": "Partially Compliant"
    },
    {
      "report_id": "RPT-19766",
      "framework": "SOC2",
      "generated_date": "2025-11-13",
      "overall_score": 35,
      "critical_findings": 2,
      "high_findings": 5,
      "medium_findings": 3,
      "low_findings": 2,
      "compliance_status": "Non-Compliant"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 2,
    "total": 20,
    "total_pages": 10
  },
  "error": null
}
```

### Report detail

`GET /api/v1/reports/RPT-10899`

```jsonc
// HTTP 200
{
  "data": {
    "report_id": "RPT-10899",
    "framework": "ISO 27001",
    "generated_date": "2026-05-05",
    "overall_score": 57,
    "critical_findings": 3,
    "high_findings": 1,
    "medium_findings": 0,
    "low_findings": 1,
    "compliance_status": "Partially Compliant"
  },
  "error": null
}
```

---

## Error shapes

### Not found

`GET /api/v1/risks/DOES-NOT-EXIST`

```jsonc
// HTTP 404
{
  "data": null,
  "error": {
    "code": "http_404",
    "message": "Risk 'DOES-NOT-EXIST' not found"
  }
}
```

### Unauthorized

`GET /api/v1/auth/me`

```jsonc
// HTTP 401
{
  "data": null,
  "error": {
    "code": "http_401",
    "message": "Missing bearer token"
  }
}
```

---
