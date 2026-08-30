# LegacyFlow Orchestrator — Dashboard

A minimal, static HTML dashboard that renders LegacyFlow workflow results with no build step and no server required.

---

## Pages

| Page | File | Purpose |
|---|---|---|
| Project List | `index.html` | Lists all completed workflow runs with risk score badges |
| Results Viewer | `viewer.html` | Tabbed view of all outputs for a specific project run |

## How to Open

The dashboard reads output files using `fetch()`, which requires a local HTTP server
(browsers block `fetch()` from `file://` URLs by default).

**Quickest option — Python:**
```bash
# From the workspace root
python -m http.server 8080
```
Then open: `http://localhost:8080/dashboard/`

**Node / npx:**
```bash
npx serve . -p 8080
```
Then open: `http://localhost:8080/dashboard/`

---

## Data Sources

| File | Used by |
|---|---|
| `dashboard/projects-index.json` | Project list page — Bob appends here after each workflow run |
| `.legacyflow/projects/{id}/impact-report.md` | Impact Report tab |
| `.legacyflow/projects/{id}/business-rules.md` | Business Rules tab |
| `.legacyflow/projects/{id}/risk-score.json` | Risk & Effort tab + header metrics |
| `.legacyflow/projects/{id}/effort-estimate.json` | Risk & Effort tab + header metrics |
| `.legacyflow/projects/{id}/plan.md` | Plan tab |
| `.legacyflow/projects/{id}/audit-trail.md` | Audit Trail tab |

---

## Dependencies

- **marked.js** (Markdown renderer) — loaded from CDN: `cdn.jsdelivr.net/npm/marked`
- Everything else is vanilla HTML + CSS + JS — no npm, no build step

---

## Tabs in the Results Viewer

| Tab | Content |
|---|---|
| Summary | Goal, workflow type, recommended actions, file index |
| Impact Report | Full rendered `impact-report.md` |
| Business Rules | Full rendered `business-rules.md` |
| Risk & Effort | Syntax-highlighted JSON from `risk-score.json` + `effort-estimate.json` |
| Plan | Bob's analysis plan (`plan.md`) |
| Audit Trail | Full execution log (`audit-trail.md`) |

Tabs that have not yet been generated show a "Not yet generated" placeholder.
