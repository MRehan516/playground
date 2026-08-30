---
name: impact-analysis
description: Use when the user wants to assess the impact of changing a field, variable, constant, or data structure across a legacy codebase — walks through parallel codebase exploration, dependency mapping, risk scoring, effort estimation, and produces a structured impact report.
---

# Impact Analysis / What-If Workflow

You are the LegacyFlow Orchestrator executing an **Impact Analysis / What-If** workflow.
Your job is to determine the full blast radius of changing a target field (or constant, data structure, or parameter) in a legacy IBM i / RPG / COBOL codebase.

Follow every phase in order. Do not skip phases. Do not ask the user for information that is already in `goal.md`.

---

## Phase 0 — Read the Project Goal

1. Read the project's `goal.md` file to extract:
   - **Target field** (e.g. `CUST_STATUS`)
   - **Codebase path** (relative to the workspace root)
   - **Scope** (all files, or a named subset)
   - **Change description** (what the user wants to change about the field)

2. Read `sample-codebase/README.md` (or any README present in the codebase path) to understand the domain and file inventory before spawning subagents.

3. List all source files in the codebase path using `list_files` (recursive). Record the full inventory — you will assign one subagent per logical file group.

---

## Phase 1 — Plan (MUST run in Plan mode first)

Switch to **Plan mode** before doing any analysis.

Produce a written plan (append to the project's `plan.md`) with these sections:

```
## Impact Analysis Plan

### Target field: <field name>
### Change description: <what the user intends to change>
### Codebase path: <path>
### Files to analyse: <list>

### Subagent assignment
| Subagent | Files | Investigation focus |
|---|---|---|
| SA-1 | CUSTCP.rpgleinc | Field definition, constants, data structure |
| SA-2 | CUSTMAST.rpg | Read/write/validate references |
| SA-3 | RPTGEN.rpg | Report filter and counter references |
| SA-4 | STATVLD.rpgle | Logic and API references |
| SA-5 | ORDPROC.rpgle | Order gate and write references |
| SA-6 | CRDALERT.rpgle | Alert rule references |
| SA-7 | JOBCTL.clle | Indirect / call-chain references |

### Risk factors identified before deep analysis
- <list any obvious high-risk factors from README>

### Human approval required before proceeding to Phase 2.
```

**Stop here and present the plan to the user. Wait for explicit approval before continuing.**

State clearly: *"Phase 1 complete. Review the plan above. Reply 'approved' or request changes before I begin the parallel exploration phase."*

---

## Phase 2 — Parallel Codebase Exploration (explore subagents)

After the user approves the plan, switch to **Agent mode**.

Spawn **one explore subagent per source file** (or per logical group for very small files).
Run all subagents **in parallel** using a single `spawn_subagent` call batch.

Each subagent must investigate its assigned file(s) and return a structured JSON-compatible summary:

```json
{
  "file": "<filename>",
  "field_references": [
    {
      "line": <number>,
      "reference_type": "read|write|conditional|constant_definition|parameter|indirect",
      "code_snippet": "<exact line or block>",
      "context": "<brief explanation of what this code does with the field>"
    }
  ],
  "business_rules_found": ["<plain-English description of each rule involving this field>"],
  "change_risk": "low|medium|high",
  "change_risk_reason": "<why this file is low/medium/high risk to change>",
  "calls_out_to": ["<other programs this file calls that may also reference the field>"],
  "called_by": ["<programs that call this one, if determinable from comments or CL>"]
}
```

Subagent instructions template (customise per file):
> "Read `<file path>`. Search for every reference to the field `<FIELD_NAME>` and to its associated constants (`ST_ACTIVE`, `ST_INACTIVE`, `ST_SUSPENDED`, `ST_CLOSED` etc.). For each reference record: line number, reference type (read/write/conditional/constant_definition/parameter/indirect), the exact code snippet, and a plain-English explanation of what the code does at that point. Also identify any business rules the code enforces around this field. Assess the risk of changing this field in this file (low/medium/high) and explain why. Note any other programs this file calls or is called by. Return your findings as a structured summary."

---

## Phase 3 — Synthesise Results

After all subagents return:

1. Merge all subagent summaries into a single **Field Reference Map** — a table of every reference sorted by file then line number.

2. Build the **Call Chain** — who calls whom, and trace the indirect exposure of the target field through the call graph.

3. Identify **duplicated rules** — the same business rule enforced in more than one file (these are high-risk modernization points).

4. Classify the **overall change impact**:
   - `TRIVIAL`: field used in 1 file, no branching logic
   - `MODERATE`: field used in 2–4 files, some conditional logic
   - `SIGNIFICANT`: field used in 5+ files, drives branching, appears in batch jobs
   - `CRITICAL`: field used in 7+ files, drives state machines, appears in interactive + batch + service programs

---

## Phase 4 — Risk Score

Compute a risk score from **1–10** using this rubric:

| Factor | Score contribution |
|---|---|
| Number of files referencing field | +1 per file (cap at +4) |
| Field drives branching / conditional logic | +2 |
| Field written (not just read) in 2+ places | +1 |
| Field appears in batch job (CL / JCL) | +1 |
| Same rule duplicated in multiple files | +1 |
| Field defined in shared copybook | +1 |
| No centralised validation service program | +1 |
| Centralised validation service program exists | −1 |

Score bands:
- **1–3**: Low risk — localised change, well-contained
- **4–6**: Medium risk — multiple touchpoints, test carefully
- **7–9**: High risk — significant coordination required
- **10**: Critical — do not change without full regression suite

Write the score and all factor contributions to `risk-score.json`:

```json
{
  "target_field": "<field>",
  "risk_score": <1-10>,
  "risk_band": "low|medium|high|critical",
  "score_breakdown": {
    "files_referencing_field": <count>,
    "drives_branching_logic": true|false,
    "written_in_multiple_places": true|false,
    "appears_in_batch_job": true|false,
    "duplicated_rules": true|false,
    "defined_in_shared_copybook": true|false,
    "no_centralised_validation": true|false,
    "centralised_validation_exists": true|false
  },
  "raw_score": <sum before adjustments>,
  "final_score": <capped 1-10>
}
```

---

## Phase 5 — Effort Estimate

Estimate the effort to safely change the target field using this schema.
Write to `effort-estimate.json`:

```json
{
  "target_field": "<field>",
  "files_to_modify": <count of files requiring code change>,
  "files_to_retest": <count of files requiring regression test>,
  "reference_count": <total number of field references across all files>,
  "write_references": <count of places where field is written>,
  "duplicated_rule_count": <number of duplicated rules to reconcile>,
  "change_complexity": "trivial|moderate|significant|complex",
  "complexity_reason": "<why>",
  "estimated_hours_range": "<e.g. 8-16 hours>",
  "estimated_hours_without_tool": "<e.g. 40-80 hours>",
  "hours_saved_estimate": "<e.g. 32-64 hours>",
  "recommended_actions": [
    "<action 1>",
    "<action 2>"
  ]
}
```

Effort estimation rules:
- Trivial: 1 write site, 1–2 read sites → 2–4 hours
- Moderate: 1–2 write sites, 3–5 read sites → 8–16 hours
- Significant: 2–3 write sites, 5–7 read sites, batch jobs → 16–40 hours
- Complex: 3+ write sites, 7+ read sites, state machine, duplicated rules → 40–80 hours

---

## Phase 6 — Write the Impact Report

Write the complete impact report to `impact-report.md` in the project folder.

Use this exact structure:

```markdown
# Impact Analysis Report

**Project:** <project-id>
**Target field:** `<FIELD_NAME>`
**Change description:** <what the user wants to change>
**Analysis date:** <today's date>
**Analyst:** IBM Bob 2.0 (LegacyFlow Orchestrator)

---

## Executive Summary

<2–4 sentences: what was found, the overall risk, the key finding, the headline recommendation>

**Risk score:** <X>/10 (<band>)
**Impact classification:** <TRIVIAL|MODERATE|SIGNIFICANT|CRITICAL>
**Files affected:** <N>
**Total references:** <N>
**Estimated change effort:** <range>
**Estimated hours saved vs manual analysis:** <range>

---

## Field Reference Map

| File | Line | Type | Code Snippet | Context |
|---|---|---|---|---|
| <file> | <line> | <read/write/conditional/…> | `<snippet>` | <explanation> |

---

## Call Chain

```
<ASCII or text diagram of the call chain showing field exposure path>
```

---

## Risk Analysis

### Risk Score: <X>/10

| Factor | Present | Score |
|---|---|---|
| <factor> | Yes/No | +/-N |
| … | … | … |
| **Total** | | **X/10** |

### Key Risk Factors

<Numbered list of the most important risk factors with explanation>

---

## Duplicated Rules (Modernization Risks)

<For each duplicated rule: rule description, files it appears in, risk if they drift out of sync>

---

## Recommended Actions

<Numbered, prioritised list of concrete actions before making the change>

---

## Effort Estimate

<Summary of effort-estimate.json in prose + table form>

---

## Files That Must Be Changed

<Table: file, reason, type of change required>

---

## Files That Must Be Regression Tested

<Table: file, test scenario description>

---

## Appendix: Subagent Summaries

<One section per subagent with their raw findings>
```

---

## Phase 7 — Audit Trail

Append a structured entry to `audit-trail.md` in the project folder:

```markdown
## Impact Analysis Run — <timestamp>

**Workflow:** Impact Analysis / What-If
**Target field:** `<field>`
**Phase 1 (Plan):** Completed — <N> files identified, <N> subagents planned
**Phase 2 (Exploration):** <N> explore subagents spawned in parallel
**Phase 3 (Synthesis):** <N> references found across <N> files
**Phase 4 (Risk):** Score <X>/10 (<band>)
**Phase 5 (Effort):** <range>
**Phase 6 (Report):** impact-report.md written
**Key decisions made:**
- <decision 1>
- <decision 2>
**Subagent summaries:** See Appendix in impact-report.md
```

---

## Phase 8 — Update projects-index.json

Append or update the entry for this project in `dashboard/projects-index.json`:

```json
{
  "project_id": "<project-id>",
  "goal_summary": "<one sentence>",
  "date": "<YYYY-MM-DD>",
  "workflow_type": "impact-analysis",
  "target_field": "<field>",
  "risk_score": <number>,
  "risk_band": "<band>",
  "files_affected": <number>,
  "status": "complete"
}
```

---

## Completion

Summarise the run to the user:
- Risk score and band
- Files affected and total references found
- Key finding (top risk factor)
- Top 3 recommended actions
- Paths to all output files

State: *"Impact Analysis complete. Review `impact-report.md` for the full findings. The dashboard has been updated."*
