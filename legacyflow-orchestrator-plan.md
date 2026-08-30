# LegacyFlow Orchestrator — Implementation Plan

**Version:** 1.0  
**Status:** Ready for Agent execution  
**Owner:** Bob 2.0 (Plan Mode → Agent Mode)

---

## Top-Level Overview

**Goal:** Build LegacyFlow Orchestrator — an AI-powered, Bob-driven workflow system that turns a natural-language goal + a legacy codebase into structured, auditable outputs (impact reports, business rules, risk scores, generated tests, and documentation).

**Scope (MVP):**
- Two fully operational workflow templates: **Impact Analysis / What-If** and **Business Rules Extraction**
- Synthetic RPG/RPGLE fixed-format + free-format sample codebase (built by us, used as the demo corpus)
- All orchestration runs inside Bob (Plan → parallel explore subagents → human approval → Agent execution)
- Outputs written as JSON + Markdown files directly to the workspace
- Static HTML dashboard that reads those output files from disk — no backend, no auth, no database
- Reusable Bob Skills for each workflow template

**Not in scope for MVP:**
- Fixed-to-Free Format modernization, Test Generation, or Full Modernization Package workflows
- Backend server, database, or authentication
- Live IBM i / IBM Z connectivity
- MCP servers or Premium Package skills

**Core principle:** Bob is not a coding assistant here — Bob is the orchestration engine. Every workflow starts in Plan mode, uses parallel explore subagents for isolation, gates on human approval, then executes in Agent mode.

---

## Architecture Summary

```
workspace/
├── sample-codebase/          # Synthetic RPG/RPGLE corpus
├── .legacyflow/
│   ├── projects/             # One folder per project run
│   │   └── {project-id}/
│   │       ├── goal.md       # User's natural language goal
│   │       ├── plan.md       # Bob's generated plan for this run
│   │       ├── impact-report.md
│   │       ├── business-rules.md
│   │       ├── risk-score.json
│   │       ├── effort-estimate.json
│   │       ├── audit-trail.md
│   │       └── diffs/
├── skills/                   # Bob SKILL.md files for each workflow
│   ├── impact-analysis.md
│   └── business-rules-extraction.md
├── dashboard/                # Static HTML dashboard
│   ├── index.html
│   ├── viewer.html
│   └── assets/
└── legacyflow-orchestrator-plan.md   # This file
```

---

## Sub-Tasks

---

### Milestone 1 — Synthetic RPG/RPGLE Sample Codebase

**Intent:**  
Create a realistic but controlled synthetic IBM i codebase that will be used as the demo corpus for all workflows. It must contain enough complexity (field references, cross-module dependencies, embedded business rules) to make Impact Analysis and Business Rules Extraction non-trivial and visually compelling in a demo.

**Expected Outcomes:**
- `sample-codebase/` folder with at least 5–8 RPG/RPGLE source members
- A mix of fixed-format (OPM RPG/400 style) and free-format (ILE RPGLE) programs
- At least one field (`CUST_STATUS`) referenced across multiple programs and a copybook — this is the demo field for the Impact Analysis workflow
- A `README.md` inside `sample-codebase/` explaining each file's fictional business purpose
- Files cover: customer master maintenance, order processing, status validation, a shared copybook/data structure, and a CL job entry

**Todo List:**
- [ ] Create `sample-codebase/` directory
- [ ] Write `CUSTMAST.rpg` — fixed-format RPG/400 customer master program (reads/writes customer file, uses `CUST_STATUS` field)
- [ ] Write `ORDPROC.rpgle` — free-format ILE RPGLE order processing program (reads customer status via copybook)
- [ ] Write `STATVLD.rpgle` — free-format ILE RPGLE status validation service program (encapsulates `CUST_STATUS` rules)
- [ ] Write `CUSTCP.rpgleinc` — shared copybook/data structure defining `CUST_STATUS` and customer fields
- [ ] Write `RPTGEN.rpg` — fixed-format RPG report generation program (references `CUST_STATUS` in selection criteria)
- [ ] Write `JOBCTL.clle` — CL program that orchestrates the job stream calling the above programs
- [ ] Write `sample-codebase/README.md` — explains fictional business domain and purpose of each file

**Relevant Context:**
- Fixed-format RPG uses columns 1–80, F-specs, C-specs with op-codes like `CHAIN`, `UPDATE`, `EXFMT`
- Free-format RPGLE uses `/free` ... `/end-free` blocks or fully free `**FREE` header with `dcl-s`, `dcl-proc`, `if/endif`, `select/when/other/endsl`
- `CUST_STATUS` values: `'A'` = Active, `'I'` = Inactive, `'S'` = Suspended, `'C'` = Closed — these are the business rules to extract
- The synthetic code does not need to compile against a real IBM i — it just needs to be syntactically plausible

**Status:** [x] done

---

### Milestone 2 — Bob Skill: Impact Analysis / What-If

**Intent:**  
Create a reusable Bob Skill (`SKILL.md`) that gives Bob precise, repeatable instructions for running the Impact Analysis / What-If workflow. This skill is the "recipe" Bob follows when a user says "assess the impact of changing field X". It defines the subagent strategy, the output schema, and the risk scoring rubric.

**Expected Outcomes:**
- `skills/impact-analysis.md` SKILL.md file registered and usable by Bob
- Skill instructs Bob to: spawn parallel explore subagents to locate every reference to the target field; trace data flows and call chains; classify each reference as read/write/conditional/display; score risk; estimate effort; produce a structured `impact-report.md` and `risk-score.json`
- Risk score rubric defined (1–10 scale with criteria)
- Effort estimate schema defined (files touched, reference count, change complexity buckets)
- Output file schemas documented inside the skill

**Todo List:**
- [ ] Define the skill's trigger description and frontmatter
- [ ] Document the subagent strategy: which explore subagents to spawn, what each one investigates, how results are merged
- [ ] Define the impact report output schema (Markdown template with sections: Executive Summary, Field Reference Map, Risk Score, Effort Estimate, Cascade Risk, Recommended Actions)
- [ ] Define `risk-score.json` schema
- [ ] Define `effort-estimate.json` schema  
- [ ] Define the audit trail entry format for this workflow
- [ ] Write `skills/impact-analysis.md` as a complete SKILL.md

**Relevant Context:**
- Bob skills live as `SKILL.md` files in the `skills/` directory
- The skill must reference the output file paths under `.legacyflow/projects/{project-id}/`
- Parallel subagents should be used: one per major program in the codebase for isolation
- Risk scoring criteria: number of files affected, presence of batch jobs, DB field vs display field, whether the field drives branching logic

**Status:** [x] done

---

### Milestone 3 — Bob Skill: Business Rules Extraction

**Intent:**  
Create a reusable Bob Skill for the Business Rules Extraction workflow. This skill instructs Bob to read source files, identify and classify embedded business rules (validation rules, status transitions, conditional logic, hardcoded constants), and produce a structured Markdown document of extracted rules with source citations.

**Expected Outcomes:**
- `skills/business-rules-extraction.md` SKILL.md file
- Skill instructs Bob to: use explore subagents to read each source file in isolation; identify rules by category (field validation, status machine transitions, boundary conditions, error handling, hardcoded business constants); cite the exact source file and line reference for each rule
- Output is `business-rules.md` with a structured table and narrative per rule category
- Rules are tagged with confidence level (High / Medium / Low) based on how clearly they are expressed in code

**Todo List:**
- [ ] Define skill frontmatter and trigger description
- [ ] Document the subagent strategy for rule extraction (one subagent per source file or logical group)
- [ ] Define the rule taxonomy: Validation Rules, Status Transitions, Boundary Conditions, Error Handling, Business Constants
- [ ] Define the `business-rules.md` output schema (per-category tables with: Rule ID, Description, Source File, Line Reference, Confidence)
- [ ] Define the audit trail entry format for this workflow
- [ ] Write `skills/business-rules-extraction.md` as a complete SKILL.md

**Relevant Context:**
- The synthetic codebase deliberately embeds rules in: `STATVLD.rpgle` (status validation logic), `CUSTMAST.rpg` (field edit rules), `ORDPROC.rpgle` (order-status dependencies)
- Rules should be cross-referenced: if the same rule appears in multiple files, flag it as duplicated (a modernization risk)
- Confidence tagging: High = explicit constant or select/when block; Medium = inline comment + code; Low = inferred from data flow only

**Status:** [x] done

---

### Milestone 4 — Orchestration Harness (Project Runner)

**Intent:**  
Create the lightweight orchestration harness that wraps a user's goal into a reproducible project run. This is not a backend server — it is a set of workspace files and conventions that Bob reads and writes. When a user wants to run a workflow, they create a project folder, write their goal to `goal.md`, and Bob uses the relevant skill to execute the full Plan → subagents → Agent workflow, writing all outputs into the project folder.

**Expected Outcomes:**
- `projects/` template folder structure under `.legacyflow/` with clear file naming conventions
- A `NEW-PROJECT-INSTRUCTIONS.md` in the workspace root that tells the user exactly how to initiate a new workflow run (what to write in `goal.md`, how to reference the codebase, which skill to invoke)
- An `audit-trail.md` template that Bob populates during each run (timestamp, step name, subagent summary, decision made)
- A `project-template/` folder with blank starter files for a new project run

**Todo List:**
- [ ] Create `.legacyflow/` directory and `projects/` subdirectory
- [ ] Create `project-template/` with: `goal.md` (with prompting instructions), `plan.md` (blank), `impact-report.md` (blank), `business-rules.md` (blank), `risk-score.json` (schema), `effort-estimate.json` (schema), `audit-trail.md` (blank with headers)
- [ ] Write `NEW-PROJECT-INSTRUCTIONS.md` at workspace root — full user-facing guide to starting a workflow
- [ ] Define and document the audit trail entry format Bob must follow when populating `audit-trail.md`

**Relevant Context:**
- No backend or CLI — Bob reads `goal.md`, runs the workflow, writes outputs in place
- Project IDs are just timestamped folder names: `{YYYYMMDD-HHMMSS}-{short-description}`
- The audit trail must capture: which subagents were spawned, what each found, what decisions were made at the Plan gate

**Status:** [x] done

---

### Milestone 5 — Static HTML Dashboard

**Intent:**  
Build a minimal static HTML dashboard that reads the output files from a project folder and presents them in a clean, readable interface. No server, no build step — just HTML + vanilla JS (or minimal React CDN). The dashboard is the "face" of the product for the demo.

**Expected Outcomes:**
- `dashboard/index.html` — project list page that reads a `projects-index.json` file and renders clickable project cards
- `dashboard/viewer.html` — results viewer with tabs: Summary, Impact Report, Business Rules, Risk & Effort, Diffs, Audit Trail
- Each tab reads the corresponding Markdown/JSON output file from the selected project folder and renders it
- A `dashboard/assets/` folder with minimal CSS (clean, dark-optional, professional look)
- A `projects-index.json` file format that lists all completed project runs (Bob appends to this after each workflow)
- Dashboard works by opening `index.html` directly in a browser (file:// protocol or simple static serve)

**Todo List:**
- [ ] Design the `projects-index.json` schema (array of: project-id, goal-summary, date, workflow-type, risk-score, status)
- [ ] Write `dashboard/assets/style.css` — clean, professional, minimal
- [ ] Write `dashboard/index.html` — reads `projects-index.json`, renders project cards with goal summary + risk score badge
- [ ] Write `dashboard/viewer.html` — tabbed results viewer; each tab fetches and renders the corresponding output file from the project folder
- [ ] Add Markdown rendering for `.md` output files (use a CDN-hosted marked.js)
- [ ] Add JSON pretty-printing for `risk-score.json` and `effort-estimate.json`
- [ ] Write `dashboard/README.md` explaining how to open and use the dashboard

**Relevant Context:**
- Output files are in `.legacyflow/projects/{project-id}/` relative to workspace root
- Dashboard must handle gracefully missing files (a tab that says "Not yet generated" if the file does not exist)
- No build tools — pure HTML/CSS/JS or React via CDN only
- Marked.js CDN: `https://cdn.jsdelivr.net/npm/marked/marked.min.js`

**Status:** [x] done

---

### Milestone 6 — End-to-End Demo Run

**Intent:**  
Execute a complete end-to-end demo workflow using the synthetic codebase, the Impact Analysis skill, and the Business Rules Extraction skill. This validates that all milestones work together and produces the actual demo artifacts that prove the system works.

**Expected Outcomes:**
- A completed project run under `.legacyflow/projects/` with all output files populated
- `impact-report.md` covering the impact of changing `CUST_STATUS` across the synthetic codebase
- `business-rules.md` with all extracted rules from the synthetic codebase, properly cited
- `risk-score.json` and `effort-estimate.json` populated with real values derived from the analysis
- `audit-trail.md` showing the full Bob execution trace (Plan, subagents, decisions, Agent execution)
- `projects-index.json` updated with this demo run
- Dashboard renders the demo run correctly in the browser

**Todo List:**
- [ ] Create a demo project folder: `.legacyflow/projects/20260829-demo-cust-status/`
- [ ] Write `goal.md` with the canonical demo goal: "Assess the impact of changing field CUST_STATUS in the customer master — what programs are affected, what business rules govern its values, and what is the risk of changing it?"
- [ ] Activate the Impact Analysis skill and execute the full workflow against the synthetic codebase using Bob in Plan → Agent mode
- [ ] Activate the Business Rules Extraction skill and execute against the synthetic codebase
- [ ] Verify all output files are written and well-formed
- [ ] Append the demo run to `projects-index.json`
- [ ] Open `dashboard/index.html` and verify the demo run renders correctly in all tabs

**Relevant Context:**
- This milestone depends on all previous milestones being complete
- The demo narrative: "We have a legacy IBM i system. We need to change a critical status field. In minutes, Bob tells us every program it touches, every business rule governing it, the risk score, and the effort estimate — with full audit trail."
- The quality of the Impact Report and Business Rules doc here is the primary demo artifact — it should be genuinely impressive

**Status:** [x] done

---

## Execution Order

```
Milestone 1  →  Milestone 2  →  Milestone 3
                                      ↓
                              Milestone 4  →  Milestone 5
                                                    ↓
                                            Milestone 6 (demo run)
```

Milestones 2 and 3 (the two skills) can be worked in parallel. Milestones 4 and 5 can be worked in parallel after 2 and 3. Milestone 6 requires all others complete.

---

## Bob Execution Strategy Per Milestone

Each milestone is handed to Agent mode as a separate `start_subtask`. Before executing any milestone, Agent mode must:
1. Read this plan file to get full context
2. Read any output or skill files produced by earlier milestones that this one depends on
3. Execute the milestone's Todo List in order
4. Mark the milestone's status as `[x] done` in this file when complete
5. Note any decisions or surprises in the relevant milestone section

---

## Open Questions (Resolved)

| Question | Resolution |
|---|---|
| IBM Bob Premium Package available? | No — standard Bob 2.0 only; use custom skills + generic agentic workflows |
| Sample codebase? | Synthetic RPG/RPGLE (fixed + free format), built by us |
| Dashboard fidelity vs orchestration depth? | Minimal static HTML dashboard; maximize orchestration quality |
| Backend? | None — Bob writes files directly, dashboard reads statically |
| MCP servers? | None — clean start |
| Workflow templates for MVP? | Impact Analysis/What-If + Business Rules Extraction only |
| Invocation mechanism? | Bob drives directly — no CLI wrapper; user approves plan, Bob executes |
