# How to Start a New LegacyFlow Orchestrator Workflow

Welcome to **LegacyFlow Orchestrator** — an IBM Bob 2.0 powered system for analysing, understanding, and modernising legacy IBM i / RPG / COBOL codebases.

---

## Overview

LegacyFlow works by reading a **project folder** you create, running a structured Bob workflow against your codebase, and writing all outputs back into that folder. There is no server, no CLI — Bob does everything.

---

## Step 1 — Create a Project Folder

Create a new folder under `.legacyflow/projects/` using the naming convention:

```
.legacyflow/projects/YYYYMMDD-<short-description>/
```

Example:
```
.legacyflow/projects/20260829-cust-status-impact/
```

Copy the template from `.legacyflow/project-template/` into your new folder:

```
cp -r .legacyflow/project-template/* .legacyflow/projects/20260829-cust-status-impact/
```

Or on Windows:
```
xcopy .legacyflow\project-template\* .legacyflow\projects\20260829-cust-status-impact\ /E
```

---

## Step 2 — Write Your Goal

Open `goal.md` in your new project folder and fill in the three required fields:

```markdown
## Goal

<Your natural-language description of what you want to achieve>

## Codebase Path

<Relative path from workspace root to your codebase, e.g. sample-codebase/>

## Workflow

<Choose one:>
- impact-analysis
- business-rules-extraction
```

### Example goal for Impact Analysis:
```markdown
## Goal

Assess the impact of changing field CUST_STATUS in the customer master.
I want to know: every program that references this field, what each one does with it,
the risk score for making a change, the effort estimate, and the top recommended actions
before touching this field.

## Codebase Path

sample-codebase/

## Workflow

impact-analysis
```

### Example goal for Business Rules Extraction:
```markdown
## Goal

Extract all business rules governing the CUST_STATUS field and the customer master
system. Produce a structured catalogue with citations to source files and line numbers.
Flag any duplicated rules across files.

## Codebase Path

sample-codebase/

## Workflow

business-rules-extraction
```

---

## Step 3 — Invoke Bob

In IBM Bob, start a new task and say:

> **"I want to run a LegacyFlow [workflow name] workflow. The project folder is `.legacyflow/projects/[your-project-id]/`."**

Bob will:
1. Activate the relevant skill automatically
2. Read your `goal.md`
3. Run in **Plan mode** first — producing a detailed plan with subagent assignments
4. **Stop and ask for your approval** before doing any analysis
5. After approval, run parallel explore subagents across your codebase
6. Write all outputs into your project folder
7. Update the dashboard index

---

## Step 4 — Review Your Results

All outputs are written to your project folder:

| File | Content |
|---|---|
| `plan.md` | Bob's analysis plan (what subagents were spawned, what they investigated) |
| `impact-report.md` | Full impact analysis report (Impact Analysis workflow) |
| `business-rules.md` | Full business rules catalogue (Business Rules Extraction workflow) |
| `risk-score.json` | Machine-readable risk score and breakdown |
| `effort-estimate.json` | Effort estimate in structured JSON |
| `audit-trail.md` | Full audit log of every Bob action and decision |
| `diffs/` | Any proposed code diffs (future workflows) |

Open `dashboard/index.html` in your browser to see all project runs in a visual dashboard.

---

## Supported Workflows (MVP)

| Workflow | Skill name | What it produces |
|---|---|---|
| Impact Analysis / What-If | `impact-analysis` | Impact report, field reference map, risk score, effort estimate |
| Business Rules Extraction | `business-rules-extraction` | Rule catalogue by category, state machine map, duplication report |

---

## Project Folder Structure

```
.legacyflow/
├── project-template/         ← copy this to start a new project
│   ├── goal.md
│   ├── plan.md
│   ├── impact-report.md
│   ├── business-rules.md
│   ├── risk-score.json
│   ├── effort-estimate.json
│   ├── audit-trail.md
│   └── diffs/
└── projects/
    └── YYYYMMDD-description/ ← your project folder
        └── (same files, populated by Bob)
```

---

## Audit Trail Format

Every Bob action during a workflow run is logged to `audit-trail.md`. The format is:

```markdown
## <Workflow Name> Run — <ISO timestamp>

**Phase N (<Phase Name>):** <What happened>
**Key decisions made:**
- <Decision and reason>
**Subagent summaries:** See Appendix in <output file>
```

You can use the audit trail to:
- Review exactly what Bob analysed and decided
- Reproduce a run
- Share findings with colleagues with full transparency
