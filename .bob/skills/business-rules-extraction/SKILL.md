---
name: business-rules-extraction
description: Use when the user wants to extract, document, or catalogue the business rules embedded in a legacy codebase — walks through parallel source file analysis, rule classification by category, confidence tagging, duplication detection, and produces a structured business rules document with source citations.
---

# Business Rules Extraction Workflow

You are the LegacyFlow Orchestrator executing a **Business Rules Extraction** workflow.
Your job is to read a legacy IBM i / RPG / COBOL codebase and surface every embedded business rule as a structured, cited, human-readable document.

Follow every phase in order. Do not skip phases.

---

## Rule Taxonomy

Every extracted rule must be classified into one of these five categories:

| Category | Code | Description |
|---|---|---|
| Validation Rule | `VALID` | Checks that a field or input value meets required conditions before proceeding |
| Status Transition | `TRANS` | Governs which state changes are permitted (state machine logic) |
| Boundary Condition | `BOUND` | Numeric thresholds, date limits, count limits, percentage cutoffs |
| Error Handling | `ERROR` | What the system does when a rule is violated — messages, codes, defaults |
| Business Constant | `CONST` | Hardcoded values that encode a business decision (magic numbers, codes) |

## Confidence Levels

| Level | Meaning |
|---|---|
| **High** | Rule is explicit: a named constant, a `select/when` block, or a clearly-commented section |
| **Medium** | Rule is clear from code + inline comment, or from obvious naming conventions |
| **Low** | Rule is inferred from data flow, field naming, or structural pattern — not stated explicitly |

---

## Phase 0 — Read the Project Goal

1. Read the project's `goal.md` file.
2. Read the codebase `README.md` (or any available documentation) to understand the domain.
3. List all source files using `list_files` (recursive) on the codebase path.

---

## Phase 1 — Plan (MUST run in Plan mode first)

Switch to **Plan mode**.

Write a plan (append to `plan.md`) with these sections:

```
## Business Rules Extraction Plan

### Codebase path: <path>
### Files to analyse: <list>

### Subagent assignment
| Subagent | File(s) | Rule categories expected |
|---|---|---|
| SA-1 | CUSTCP.rpgleinc | CONST — field codes and thresholds |
| SA-2 | CUSTMAST.rpg | VALID, TRANS, BOUND, ERROR |
| SA-3 | STATVLD.rpgle | VALID, TRANS — authoritative rule service |
| SA-4 | ORDPROC.rpgle | VALID, BOUND, ERROR |
| SA-5 | CRDALERT.rpgle | BOUND — alert thresholds |
| SA-6 | RPTGEN.rpg | CONST, BOUND — filter and display rules |
| SA-7 | JOBCTL.clle | ERROR — batch error handling |

### Human approval required before proceeding to Phase 2.
```

**Stop and present the plan. Wait for explicit approval.**

State: *"Phase 1 complete. Review the extraction plan. Reply 'approved' to begin parallel rule extraction."*

---

## Phase 2 — Parallel Rule Extraction (explore subagents)

After approval, switch to **Agent mode**.

Spawn **one explore subagent per source file** in parallel (single batch `spawn_subagent` call).

Each subagent must return a structured summary:

```json
{
  "file": "<filename>",
  "rules": [
    {
      "rule_id": "<FILE_ABBREV>-<NNN>",
      "category": "VALID|TRANS|BOUND|ERROR|CONST",
      "description": "<plain-English statement of the rule>",
      "source_file": "<filename>",
      "line_reference": "<line number or range, e.g. 95-112>",
      "code_evidence": "<exact code snippet that expresses the rule>",
      "confidence": "High|Medium|Low",
      "confidence_reason": "<why this confidence level>",
      "related_field": "<primary field this rule governs>",
      "duplicate_candidate": true|false,
      "duplicate_note": "<if true, describe where else this rule may appear>"
    }
  ],
  "notes": "<any observations about rule clarity, documentation quality, or modernization concerns>"
}
```

**Rule ID convention:**
- `CM-001` for CUSTMAST.rpg
- `CP-001` for CUSTCP.rpgleinc  
- `SV-001` for STATVLD.rpgle
- `OP-001` for ORDPROC.rpgle
- `CA-001` for CRDALERT.rpgle
- `RG-001` for RPTGEN.rpg
- `JC-001` for JOBCTL.clle

Subagent instructions template:
> "Read `<file path>`. Extract every business rule embedded in this code. A business rule is any logic that enforces a business constraint, validates a value, controls a state transition, applies a numeric threshold, handles an error condition, or uses a hardcoded business constant. For each rule: assign a rule ID, classify it (VALID/TRANS/BOUND/ERROR/CONST), write a plain-English description, cite the exact source line(s) and code snippet, assign a confidence level (High/Medium/Low) and explain why, note the primary field the rule governs, and flag if this same rule appears to be duplicated from another file. Return all findings as a structured summary."

---

## Phase 3 — Synthesise and Deduplicate

After all subagents return:

1. **Assign global Rule IDs** — sequential across all files: `LF-001`, `LF-002`, etc. Retain the per-file ID as a cross-reference.

2. **Detect duplicates** — rules with the same description or same code pattern in 2+ files. Mark each with `DUPLICATE` tag and list all files where the duplication exists.

3. **Group by category** — organise all rules into the 5 taxonomy buckets.

4. **Identify the CUST_STATUS state machine** explicitly — collect all `TRANS` rules and verify they form a consistent, complete state machine. Flag any gaps or contradictions.

5. **Count totals** — total rules by category, total duplicates, confidence distribution.

---

## Phase 4 — Write the Business Rules Document

Write the complete document to `business-rules.md` in the project folder.

Use this exact structure:

```markdown
# Business Rules Catalogue

**Project:** <project-id>
**Codebase:** <path>
**Extraction date:** <today's date>
**Analyst:** IBM Bob 2.0 (LegacyFlow Orchestrator)

---

## Summary

| Category | Count | Duplicated | High Confidence | Medium | Low |
|---|---|---|---|---|---|
| Validation Rules (VALID) | N | N | N | N | N |
| Status Transitions (TRANS) | N | N | N | N | N |
| Boundary Conditions (BOUND) | N | N | N | N | N |
| Error Handling (ERROR) | N | N | N | N | N |
| Business Constants (CONST) | N | N | N | N | N |
| **Total** | **N** | **N** | **N** | **N** | **N** |

**Key finding:** <1–2 sentence headline: most important thing found>

---

## Status Machine Map — CUST_STATUS

<Full state machine reconstructed from all TRANS rules, in ASCII diagram>

Permitted transitions:
| From | To | Governing Rule ID | Source File |
|---|---|---|---|

Blocked transitions:
| From | To | Reason | Source File |
|---|---|---|---|

---

## Validation Rules (VALID)

| Rule ID | Description | Source File | Line | Code Evidence | Confidence | Notes |
|---|---|---|---|---|---|---|

---

## Status Transition Rules (TRANS)

| Rule ID | Description | From Status | To Status | Source File | Line | Code Evidence | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|

---

## Boundary Conditions (BOUND)

| Rule ID | Description | Threshold Value | Field Governed | Source File | Line | Code Evidence | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|

---

## Error Handling Rules (ERROR)

| Rule ID | Description | Trigger Condition | System Response | Source File | Line | Code Evidence | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|

---

## Business Constants (CONST)

| Rule ID | Constant Name | Value | Business Meaning | Source File | Line | Confidence | Notes |
|---|---|---|---|---|---|---|---|

---

## ⚠️ Duplicated Rules (Modernization Risk)

Rules that appear in more than one file. Each duplication is a risk: if files diverge, the system becomes inconsistent.

| Rule ID | Description | Files Containing Duplication | Risk if Diverged |
|---|---|---|---|

### Duplication Detail

<For each duplicated rule: description, full code from each file side-by-side, recommendation>

---

## Modernization Observations

<Numbered list of observations about rule quality, documentation gaps, centralization opportunities>

---

## Appendix: Per-File Subagent Summaries

<One section per file>
```

---

## Phase 5 — Audit Trail

Append to `audit-trail.md`:

```markdown
## Business Rules Extraction Run — <timestamp>

**Workflow:** Business Rules Extraction
**Phase 1 (Plan):** Completed — <N> files assigned to <N> subagents
**Phase 2 (Extraction):** <N> explore subagents run in parallel
**Phase 3 (Synthesis):** <N> rules extracted, <N> duplicates found
**Phase 4 (Document):** business-rules.md written
**Rule counts by category:**
- VALID: N
- TRANS: N
- BOUND: N
- ERROR: N
- CONST: N
**Total duplicates flagged:** N
**Key decisions made:**
- <decision 1>
- <decision 2>
```

---

## Phase 6 — Update projects-index.json

Append or update the entry in `dashboard/projects-index.json`:

```json
{
  "project_id": "<project-id>",
  "goal_summary": "<one sentence>",
  "date": "<YYYY-MM-DD>",
  "workflow_type": "business-rules-extraction",
  "rules_extracted": <total count>,
  "duplicates_found": <count>,
  "status": "complete"
}
```

---

## Completion

Summarise the run to the user:
- Total rules extracted and breakdown by category
- Number of duplicates flagged
- State machine completeness (any gaps or contradictions)
- Top 3 modernization observations
- Paths to all output files

State: *"Business Rules Extraction complete. Review `business-rules.md` for the full catalogue. The dashboard has been updated."*
