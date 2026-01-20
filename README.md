ImpactProof — Project Hub

This document is the single source of truth for the ImpactProof project. It organizes vision, product decisions, technical design, and next actions so the project stays focused and easy to grow.

⸻

1. Project Overview

Project name: ImpactProof
Tagline: Turn messy program data into donor-ready proof.

Problem: NGOs across sectors struggle with unreliable data and stressful donor reporting cycles.

Solution: A configuration-driven data quality and reporting toolkit that validates data reliability and produces donor-ready outputs with confidence.

Primary users:
	•	M&E Managers
	•	Data Managers

⸻

2. Core Principles (Non‑Negotiables)
	•	Sector-agnostic at the core
	•	Configuration over hard-coded schemas
	•	Explainable logic (no black boxes)
	•	Read-only, safe by design
	•	Decisions before dashboards

⸻

3. Product Scope

In Scope (v1)
	•	Data quality checks (generic)
	•	Scorecard + fix lists
	•	Donor-ready reporting tables (optional gate)
	•	CSV + database inputs
	•	CommCare-first workflows

Explicitly Out of Scope (v1)
	•	Dashboards
	•	Data collection
	•	Real-time pipelines
	•	AI/ML predictions

⸻

4. MVP Data Quality Checks
	1.	Completeness (required fields)
	2.	Duplicate & overcount detection
	3.	Logical consistency rules
	4.	Explicit missing value classification (NO / NA / UNKNOWN)
	5.	Volume & trend drift detection

Each check outputs pass/warn/fail, record-level issues, and recommended fixes.

⸻

5. High-Level Workflow

Raw Data → Standardization → Quality Checks → Scorecard → Fix List → (Optional) Donor-Ready Tables → Reporting & Decisions

ImpactProof acts as a quality gate between raw data and reporting.

⸻

6. Technical Architecture (Reference)
	•	Config-driven execution (YAML)
	•	Modular checks with standard interfaces
	•	Canonical roles (entity_id, record_id, event_date)
	•	Pluggable input/output layers

See: Technical Architecture notes (to be added).

⸻

7. Key Documents
	•	README.md — Product explanation (public-facing)
	•	Project Hub (this document)
	•	Flow Diagram — How ImpactProof works
	•	Technical Architecture — Modules and execution
	•	MVP Checklist — What defines “done” for v1

⸻

8. Current Status

Phase: Early development / concept-to-prototype

Completed:
	•	Product concept
	•	Naming and positioning
	•	Workflow design
	•	MVP check definition
	•	README

⸻

9. Next Milestones

Milestone 1: Thin Vertical Slice
	•	One dataset (CSV)
	•	Two checks implemented
	•	One scorecard output

Milestone 2: Full MVP Checks
	•	All 5 checks
	•	Fix list generation
	•	Config-driven mappings

Milestone 3: Pilot Validation
	•	1–2 real NGO datasets
	•	Feedback from M&E/Data Managers

⸻

10. Guardrails
	•	No reuse of employer IP or data
	•	Generic datasets only
	•	Nights/weekends development only
	•	Keep scope intentionally small

⸻

11. Success Definition (Early)
	•	At least 1 paying pilot user
	•	Clear time/stress reduction for reporting teams
	•	Evidence that the scorecard changes behavior

⸻
12. Quick Start (Local)

Requirements
	• Python 3.9+

Setup
```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate

pip install -e .
```

Configure
Create or edit `impactproof.yaml`:
```yaml
input:
  mode: "csv"
  csv:
    file: "data/sample.csv"

standardization:
  missing_labels:
    na_values: ["", " ", "N/A", "NA", "na", "n/a", null]
    no_values: ["NO", "No", "no", "FALSE", "False", "false", "0"]
    unknown_values: ["UNKNOWN", "Unknown", "unknown", "Not sure", "NOT_SURE"]

checks:
  completeness:
    required_fields: ["learner_id", "encounter_date", "school"]
    pass_threshold: 0.95
    warn_threshold: 0.85

  duplicates:
    keys: ["learner_id", "encounter_date"]
    pass_threshold: 0.00
    warn_threshold: 0.02

  consistency:
    rules:
      - name: "CompletedRequiresFollowupDate"
        when:
          field: "outcome"
          equals: "Completed"
        then_required: ["followup_date"]

  drift:
    date_field: "encounter_date"
    period: "monthly"
    baseline_periods: 2
    warn_pct_change: 0.30
    fail_pct_change: 0.50

output:
  mode: "csv"
  path: "outputs/"
```

Run
```bash
python -m impactproof run --config impactproof.yaml
```

Outputs
ImpactProof writes to `outputs/`:
	• `quality_scorecard.csv` — PASS/WARN/FAIL per check + overall
	• `issues_all.csv` — record-level issues across checks
	• `fix_list.csv` — grouped summary of top issues

⸻

9. Current Status

