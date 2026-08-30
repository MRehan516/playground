"""
LegacyFlow local backend
========================
Serves the dashboard as static files AND exposes a small API for triggering
live analysis runs via Bob Shell's headless (-p) mode.

Usage
-----
    pip install flask
    python server.py

Then open http://localhost:5000 in your browser.

Endpoints
---------
    GET  /                         → dashboard/index.html
    GET  /<path>                   → any file under dashboard/
    GET  /api/fields               → list of valid field names from CUSTCP.rpgleinc
    POST /api/analyze              → { "field": "CUST_STATUS" }  start a run
    GET  /api/status/<project_id>  → { "state": "running"|"complete"|"error", ... }

IMPORTANT — about the --yolo flag
----------------------------------
The LegacyFlow skills include a human-in-the-loop approval gate at Phase 1
(Plan mode). With --yolo that gate is bypassed: Bob will proceed through
Plan → subagents → Agent without pausing for your approval.

This is the intended headless behaviour for scripted invocation. If you want
to review the plan before analysis runs, set REQUIRE_PLAN_APPROVAL=true in
the environment. The run will then pause after Phase 1; you must manually
resume it from Bob's interactive chat.
"""

import json
import os
import re
import shlex
import shutil
import subprocess
import threading
from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

# ---------------------------------------------------------------------------
# Paths (all relative to the workspace root, which is where this file lives)
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).parent.resolve()
DASHBOARD  = ROOT / "dashboard"
PROJECTS   = ROOT / ".legacyflow" / "projects"
TEMPLATE   = ROOT / ".legacyflow" / "project-template"
COPYBOOK   = ROOT / "sample-codebase" / "CUSTCP.rpgleinc"
INDEX_FILE = DASHBOARD / "projects-index.json"

# ---------------------------------------------------------------------------
# Field extraction from CUSTCP.rpgleinc
# ---------------------------------------------------------------------------
_FIELD_PATTERN = re.compile(
    r"^\s+D\s+(\w+)\s+DS\b"             # data structure header (CUSTOMER_DS)
    r"|^\s+D\s+(\w+)\s+\d+[APD]\s",     # plain field definition  e.g.  D CUST_ID  7P 0
    re.MULTILINE,
)

def extract_fields(copybook_path: Path) -> list[str]:
    """
    Return the list of field names defined in CUSTCP.rpgleinc.

    Reads all D-spec lines and returns the identifier names.  The data
    structure name itself (CUSTOMER_DS) is included so the user can also
    analyse the whole structure.  Status constants (ST_*) and threshold
    constants are excluded — they are not top-level fields.
    """
    text    = copybook_path.read_text(encoding="utf-8", errors="replace")
    fields  = []

    # Match D-spec lines:  "       D  FIELDNAME      ..."
    # Fixed-format RPG: columns 7-16 are the name area.  We just look for
    # lines that start with optional whitespace, then D, then a name token.
    dspec = re.compile(r"^\s+D\s+([A-Za-z_][A-Za-z0-9_]*)\s", re.MULTILINE)
    for m in dspec.finditer(text):
        name = m.group(1)
        # Skip constants (they contain C specs later) — include only DS + fields
        # We detect constants by looking ahead: constants have 'C' in their type column
        # For simplicity: include all D-spec names that are not standalone constants
        # (constants in this file all start with ST_, CREDIT_, SUSPEND_)
        if not re.match(r"^(ST_|CREDIT_|SUSPEND_)", name):
            if name not in fields:
                fields.append(name)

    return sorted(fields)


VALID_FIELDS: list[str] = []

def load_fields() -> None:
    global VALID_FIELDS
    if not COPYBOOK.exists():
        VALID_FIELDS = []
        return
    VALID_FIELDS = extract_fields(COPYBOOK)


# ---------------------------------------------------------------------------
# Project helpers
# ---------------------------------------------------------------------------
def make_project_id(field: str) -> str:
    today = date.today().strftime("%Y%m%d")
    safe  = re.sub(r"[^A-Za-z0-9]", "-", field).lower()
    return f"{today}-live-{safe}"


def scaffold_project(project_id: str, field: str) -> Path:
    """Copy the project template into a new project folder and write goal.md."""
    project_dir = PROJECTS / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # Copy every template file (skip diffs/ subdirectory — empty placeholder)
    for src in TEMPLATE.iterdir():
        if src.is_file():
            shutil.copy2(src, project_dir / src.name)
        elif src.is_dir():
            dest_sub = project_dir / src.name
            dest_sub.mkdir(exist_ok=True)

    # Write goal.md with the specific field
    goal_text = f"""\
## Goal

Assess the full impact of changing field `{field}` in the Acme Distribution IBM i codebase.
Produce a field reference map, risk score, effort estimate, and full impact report.
Also extract all business rules that govern `{field}` and produce a structured catalogue
with source citations.  Flag any duplicated rules across files.

## Codebase Path

sample-codebase/

## Workflow

impact-analysis
business-rules-extraction

## Target Field (required for impact-analysis)

{field}

## Scope

(all files in sample-codebase/)
"""
    (project_dir / "goal.md").write_text(goal_text, encoding="utf-8")
    return project_dir


def write_status(project_dir: Path, state: str, **extra) -> None:
    payload = {"state": state, "updated": datetime.utcnow().isoformat() + "Z", **extra}
    (project_dir / "status.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def append_to_index(project_id: str, field: str) -> None:
    """Add a 'running' placeholder entry to projects-index.json."""
    try:
        existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        existing = []

    # Remove any stale entry for the same project_id
    existing = [p for p in existing if p.get("project_id") != project_id]
    existing.append({
        "project_id":     project_id,
        "goal_summary":   f"Live analysis of {field} — in progress",
        "date":           date.today().isoformat(),
        "workflow_type":  "impact-analysis",
        "target_field":   field,
        "status":         "running",
    })
    INDEX_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def update_index_on_completion(project_id: str, project_dir: Path) -> None:
    """
    After Bob finishes, the skill itself calls Phase 8 which rewrites
    projects-index.json with the full metadata.  This function is a
    safety net: if risk-score.json exists we update the index entry
    ourselves so the status field is accurate even if Bob's Phase 8
    partial-wrote the file.
    """
    try:
        existing = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        existing = []

    entry = next((p for p in existing if p.get("project_id") == project_id), None)
    if entry is None:
        return  # Bob's Phase 8 already replaced the whole entry — nothing to do

    # Pull risk score if available
    rs_path = project_dir / "risk-score.json"
    if rs_path.exists():
        try:
            rs = json.loads(rs_path.read_text(encoding="utf-8"))
            entry.update({
                "risk_score":   rs.get("final_score"),
                "risk_band":    rs.get("risk_band", ""),
                "files_affected": rs.get("score_breakdown", {}).get("files_referencing_field"),
            })
        except Exception:
            pass

    ef_path = project_dir / "effort-estimate.json"
    if ef_path.exists():
        try:
            ef = json.loads(ef_path.read_text(encoding="utf-8"))
            entry.update({
                "reference_count":    ef.get("reference_count"),
                "hours_saved_estimate": ef.get("hours_saved_estimate", ""),
            })
        except Exception:
            pass

    br_path = project_dir / "business-rules.md"
    if br_path.exists():
        # Count rule table rows as a rough rules_extracted number
        text  = br_path.read_text(encoding="utf-8", errors="replace")
        # Each rule row starts with "| <ID> |"
        count = len(re.findall(r"^\|\s+[A-Z]{2,6}-\d+\s+\|", text, re.MULTILINE))
        if count:
            entry["rules_extracted"] = count

    entry["status"] = "complete"
    entry["goal_summary"] = f"Impact & rules analysis of {entry.get('target_field', 'unknown field')}"

    # Write back
    INDEX_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Bob invocation
# ---------------------------------------------------------------------------
def build_bob_prompt(project_id: str, field: str) -> str:
    """
    Construct the prompt that tells Bob exactly what to do.

    We tell Bob to:
      1. Activate both skills in sequence (impact-analysis then business-rules)
      2. Read the goal.md we already wrote
      3. Run fully, writing all outputs to the project folder
      4. Update projects-index.json

    The --yolo flag means the Plan-mode approval gate is bypassed.
    Bob proceeds automatically from Plan → parallel subagents → Agent.
    """
    project_path = f".legacyflow/projects/{project_id}"
    return (
        f"Run a LegacyFlow workflow. "
        f"The project folder is `{project_path}/`. "
        f"Read `{project_path}/goal.md` to get the full goal. "
        f"First activate the impact-analysis skill and run the full workflow for field `{field}` "
        f"against sample-codebase/, writing all outputs to `{project_path}/`. "
        f"Then activate the business-rules-extraction skill and run the full workflow "
        f"for the same codebase, appending the business rules output to `{project_path}/`. "
        f"Finally update `dashboard/projects-index.json` with the completed project entry. "
        f"Do not pause for approval — proceed through all phases automatically."
    )


def run_bob_headless(project_id: str, field: str, project_dir: Path) -> None:
    """
    Called in a background thread.  Invokes `bob -p <prompt> --yolo` and
    tracks the result in status.json.

    Requirement: `bob` must be on PATH and authenticated with an API key.
    See: https://ibm.biz/bob-shell-install  (API key auth required for -p mode)
    """
    write_status(project_dir, "running", project_id=project_id, field=field,
                 started=datetime.utcnow().isoformat() + "Z")

    prompt = build_bob_prompt(project_id, field)

    cmd = [
        "bob",
        "--prompt", prompt,
        "--yolo",                    # auto-approve all tool calls (bypasses plan gate)
        "--chat-mode", "agent",      # start directly in Agent mode
        "--hide-intermediary-output",# suppress tool-call noise; emit only final message
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(ROOT),           # workspace root — bob resolves paths from here
            capture_output=True,
            text=True,
            timeout=600,             # 10-minute hard ceiling; adjust if runs are longer
        )

        if result.returncode == 0:
            update_index_on_completion(project_id, project_dir)
            write_status(
                project_dir, "complete",
                project_id=project_id, field=field,
                bob_output=result.stdout[-2000:] if result.stdout else "",
            )
        else:
            write_status(
                project_dir, "error",
                project_id=project_id, field=field,
                message=f"bob exited with code {result.returncode}",
                stderr=result.stderr[-2000:] if result.stderr else "",
                stdout=result.stdout[-2000:] if result.stdout else "",
            )

    except FileNotFoundError:
        write_status(
            project_dir, "error",
            project_id=project_id, field=field,
            message=(
                "`bob` was not found on PATH. "
                "Install Bob Shell and authenticate with an API key before using the live run feature. "
                "See: https://www.ibm.com/products/ibm-watsonx-code-assistant — Bob Shell docs."
            ),
        )
    except subprocess.TimeoutExpired:
        write_status(
            project_dir, "error",
            project_id=project_id, field=field,
            message="Bob Shell run timed out after 600 seconds.",
        )
    except Exception as exc:
        write_status(
            project_dir, "error",
            project_id=project_id, field=field,
            message=str(exc),
        )


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)


@app.route("/")
def root():
    return send_from_directory(DASHBOARD, "index.html")


@app.route("/<path:filename>")
def static_dashboard(filename):
    """Serve anything from the dashboard/ folder."""
    return send_from_directory(DASHBOARD, filename)


@app.route("/api/fields", methods=["GET"])
def api_fields():
    """Return the list of valid field names extracted from CUSTCP.rpgleinc."""
    return jsonify({"fields": VALID_FIELDS})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """
    Start a new live analysis run.

    Body: { "field": "CUST_STATUS" }

    Returns immediately with { "project_id": "...", "status_url": "..." }.
    Poll GET /api/status/<project_id> to track progress.
    """
    body  = request.get_json(force=True, silent=True) or {}
    field = (body.get("field") or "").strip()

    if not field:
        return jsonify({"error": "Missing required field: 'field'"}), 400

    if field not in VALID_FIELDS:
        return jsonify({
            "error":  f"'{field}' is not a known field in sample-codebase/CUSTCP.rpgleinc.",
            "valid":  VALID_FIELDS,
            "hint":   "Only fields defined in the copybook can be analysed.",
        }), 422

    project_id  = make_project_id(field)
    project_dir = scaffold_project(project_id, field)

    append_to_index(project_id, field)

    # Fire off the Bob run in a background thread so this endpoint returns immediately
    thread = threading.Thread(
        target=run_bob_headless,
        args=(project_id, field, project_dir),
        daemon=True,
        name=f"bob-{project_id}",
    )
    thread.start()

    return jsonify({
        "project_id":  project_id,
        "status_url":  f"/api/status/{project_id}",
        "viewer_url":  f"/viewer.html?project={project_id}",
        "message":     (
            f"Analysis of '{field}' started. "
            "Poll status_url every 2 seconds. "
            "NOTE: the Plan-mode approval gate is bypassed (--yolo). "
            "Bob will proceed automatically through all phases."
        ),
    }), 202


@app.route("/api/status/<project_id>", methods=["GET"])
def api_status(project_id: str):
    """
    Return the current status of a run.

    Reads status.json from the project folder.  Also merges the
    projects-index.json entry if the run is complete so the frontend
    can get the final metadata in a single call.
    """
    # Basic path-traversal guard
    if not re.match(r"^[A-Za-z0-9_-]+$", project_id):
        return jsonify({"error": "Invalid project_id"}), 400

    project_dir = PROJECTS / project_id
    status_file = project_dir / "status.json"

    if not status_file.exists():
        # Project folder doesn't exist at all
        if not project_dir.exists():
            return jsonify({"error": "Project not found"}), 404
        # Folder exists but status.json not yet written (race on startup)
        return jsonify({"state": "pending", "project_id": project_id})

    try:
        status = json.loads(status_file.read_text(encoding="utf-8"))
    except Exception as exc:
        return jsonify({"error": f"Could not read status.json: {exc}"}), 500

    # On completion, attach the index entry so the frontend can refresh metadata
    if status.get("state") == "complete":
        try:
            index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
            entry = next((p for p in index if p.get("project_id") == project_id), None)
            if entry:
                status["index_entry"] = entry
        except Exception:
            pass

    return jsonify(status)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    load_fields()

    if not VALID_FIELDS:
        print(f"WARNING: Could not extract fields from {COPYBOOK}")
        print("         Make sure the copybook path is correct.")

    # Ensure the projects directory exists
    PROJECTS.mkdir(parents=True, exist_ok=True)

    print()
    print("LegacyFlow local backend")
    print("=" * 40)
    print(f"Dashboard : http://localhost:5000/")
    print(f"Fields API: http://localhost:5000/api/fields")
    print(f"Copybook  : {COPYBOOK}")
    print(f"Fields    : {', '.join(VALID_FIELDS) or '(none found)'}")
    print()
    print("NOTE: Live analysis requires `bob` on PATH with API key authentication.")
    print("      Install Bob Shell: https://www.ibm.com/products/ibm-watsonx-code-assistant")
    print()

    app.run(host="127.0.0.1", port=5000, debug=False)
