/**
 * LegacyFlow — Run Panel
 * ======================
 * Two entry points:
 *
 *  1. Legacy panel on projects.html — mounts after .page-hero when Flask is running.
 *     Unchanged behaviour for backwards-compatibility.
 *
 *  2. OrchestratePanel — mounts on orchestrate.html.
 *     Richer phase display, direct DOM target, richer sub-labels.
 *
 * Both are no-ops when the Flask backend is not reachable.
 */
(function () {
  'use strict';

  const FIELDS_URL  = '/api/fields';
  const ANALYZE_URL = '/api/analyze';
  const STATUS_BASE = '/api/status/';

  // ── Shared helpers ──────────────────────────────────────────────────────────

  function esc(s) {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  async function fetchFields() {
    const res = await fetch(FIELDS_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const { fields } = await res.json();
    if (!fields || fields.length === 0) throw new Error('No fields returned');
    return fields;
  }

  // ── ─────────────────────────────────────────────────────────────────────────
  //  LEGACY PANEL  (projects.html / .page-hero)
  // ── ─────────────────────────────────────────────────────────────────────────

  const PHASES = [
    { label: 'Plan',          cls: 'tl-phase-plan',     sub: 'Bob reads codebase, creates execution plan' },
    { label: 'Approval Gate', cls: 'tl-phase-synthesis', sub: 'Bypassed via --yolo (auto-approved)' },
    { label: 'Explore',       cls: 'tl-phase-explore',  sub: 'Agent 1: Impact Analysis  ·  Agent 2: Rules Extraction' },
    { label: 'Synthesis',     cls: 'tl-phase-synthesis', sub: 'Risk scoring + effort estimation' },
    { label: 'Write Reports', cls: 'tl-phase-output',   sub: '6 structured files written to project directory' },
  ];

  let pollTimer    = null;
  let elapsedTimer = null;
  let startTime    = null;
  let currentPhase = 0;

  function mountLegacyPanel(fields) {
    const hero = document.querySelector('.page-hero');
    if (!hero) return;

    const panel = document.createElement('div');
    panel.id        = 'run-panel';
    panel.className = 'run-panel';
    panel.innerHTML = `
      <div class="run-panel-inner">

        <div class="run-panel-form">
          <label class="run-label" for="field-select">Run new analysis</label>
          <div class="run-controls">
            <select id="field-select" class="run-select">
              ${fields.map(f =>
                `<option value="${esc(f)}"${f === 'CUST_STATUS' ? ' selected' : ''}>${esc(f)}</option>`
              ).join('')}
            </select>
            <button id="run-btn" class="run-btn">
              <span id="run-btn-label">Run Analysis</span>
            </button>
          </div>
          <p class="run-hint">
            Triggers a live <code>bob -p … --yolo</code> run — Impact Analysis + Business
            Rules Extraction. The Plan-mode approval gate is bypassed; Bob proceeds
            automatically through all phases.
          </p>
        </div>

        <div id="run-progress" class="run-progress" style="display:none">
          <div class="run-progress-header">
            <span class="run-progress-title" id="run-progress-title">Starting…</span>
            <span class="run-elapsed" id="run-elapsed"></span>
          </div>
          <div class="run-progress-bar-track">
            <div class="run-progress-bar-fill" id="run-bar"></div>
          </div>
          <div class="run-phases" id="run-phases"></div>
          <div class="run-error-box" id="run-error-box" style="display:none"></div>
        </div>

      </div>`;

    hero.insertAdjacentElement('afterend', panel);
    document.getElementById('run-btn').addEventListener('click', onLegacyRun);
  }

  function onLegacyRun() {
    const field = document.getElementById('field-select')?.value;
    if (!field) return;

    legacyStopAll();
    legacyResetProgress(field);
    legacySetFormDisabled(true);

    fetch(ANALYZE_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ field }),
    })
      .then(res => res.json().then(data => ({ res, data })))
      .then(({ res, data }) => {
        if (!res.ok) {
          legacyShowError(data.error || `HTTP ${res.status}`, data.hint || '');
          legacySetFormDisabled(false);
          return;
        }
        startTime = Date.now();
        legacyStartElapsed();
        legacyStartPolling(data.project_id);
      })
      .catch(() => {
        legacyShowError('Could not reach the backend.', 'Make sure server.py is running: python server.py');
        legacySetFormDisabled(false);
      });
  }

  function legacyResetProgress(field) {
    currentPhase = 0;
    document.getElementById('run-progress').style.display = '';
    document.getElementById('run-progress-title').textContent = `Analysing ${field}…`;
    document.getElementById('run-error-box').style.display   = 'none';
    document.getElementById('run-error-box').innerHTML       = '';
    legacySetBar(0);
    document.getElementById('run-phases').innerHTML = '';
    legacyRenderPhase(0, 'running');
  }

  function legacySetBar(pct) {
    const bar = document.getElementById('run-bar');
    if (bar) bar.style.width = Math.min(100, Math.max(0, pct)) + '%';
  }

  function legacyRenderPhase(idx, state) {
    const container = document.getElementById('run-phases');
    if (!container) return;
    const cfg = PHASES[idx];
    if (!cfg) return;

    const id  = `rp-ph-${idx}`;
    let row   = document.getElementById(id);
    if (!row) {
      row    = document.createElement('div');
      row.id = id;
      row.className = 'rp-phase';
      container.appendChild(row);
    }

    const dotCls     = state === 'done' ? 'rp-dot-done' : state === 'running' ? 'rp-dot-running' : 'rp-dot-pending';
    const stateLabel = state === 'done' ? '✓' : state === 'running' ? 'running…' : '';

    row.innerHTML =
      `<span class="rp-dot ${dotCls}"></span>` +
      `<span class="tl-phase-badge ${cfg.cls}" style="font-size:0.65rem">${cfg.label}</span>` +
      `<span class="rp-phase-sublabel" style="font-size:0.72rem;color:var(--text-muted);flex:1">${esc(cfg.sub)}</span>` +
      `<span class="rp-phase-label">${stateLabel}</span>`;
  }

  function legacyAdvancePhase() {
    if (currentPhase >= PHASES.length) return;
    legacyRenderPhase(currentPhase, 'done');
    currentPhase += 1;
    legacySetBar(Math.round((currentPhase / PHASES.length) * 88));
    if (currentPhase < PHASES.length) legacyRenderPhase(currentPhase, 'running');
  }

  function legacyShowError(msg, hint) {
    legacyStopAll();
    const box = document.getElementById('run-error-box');
    if (!box) return;
    box.style.display = '';
    box.innerHTML =
      `<strong>Error:</strong> ${esc(msg)}` +
      (hint ? `<br><span style="font-size:0.8rem;color:var(--text-muted)">${esc(hint.slice(0, 400))}</span>` : '');
    document.getElementById('run-progress').style.display = '';
  }

  function legacyMarkComplete(projectId) {
    legacyStopAll();
    legacySetBar(100);
    for (let i = currentPhase; i < PHASES.length; i++) legacyRenderPhase(i, 'done');
    document.getElementById('run-progress-title').innerHTML =
      `Analysis complete — ` +
      `<a href="viewer.html?project=${encodeURIComponent(projectId)}" style="color:var(--accent)">View results &rarr;</a>`;
    legacySetFormDisabled(false);
    if (typeof window.reloadProjectList === 'function') window.reloadProjectList();
  }

  function legacyStartElapsed() {
    elapsedTimer = setInterval(() => {
      const el = document.getElementById('run-elapsed');
      if (!el || !startTime) return;
      const s = Math.floor((Date.now() - startTime) / 1000);
      el.textContent = s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`;
    }, 1000);
  }

  function legacyStartPolling(projectId) {
    legacyDoPoll(projectId);
    pollTimer = setInterval(() => legacyDoPoll(projectId), 2000);
  }

  async function legacyDoPoll(projectId) {
    try {
      const res  = await fetch(`${STATUS_BASE}${encodeURIComponent(projectId)}`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.state === 'running' && currentPhase < PHASES.length - 1) legacyAdvancePhase();
      if (data.state === 'complete') legacyMarkComplete(projectId);
      if (data.state === 'error') {
        legacySetFormDisabled(false);
        legacyShowError(data.message || 'Unknown error', (data.stderr || data.stdout || '').slice(0, 400));
      }
    } catch (_) {}
  }

  function legacyStopAll() {
    if (pollTimer)    { clearInterval(pollTimer);    pollTimer    = null; }
    if (elapsedTimer) { clearInterval(elapsedTimer); elapsedTimer = null; }
  }

  function legacySetFormDisabled(disabled) {
    const btn    = document.getElementById('run-btn');
    const select = document.getElementById('field-select');
    const lbl    = document.getElementById('run-btn-label');
    if (btn)    { btn.disabled    = disabled; btn.classList.toggle('run-btn-loading', disabled); }
    if (select) { select.disabled = disabled; }
    if (lbl)    { lbl.textContent = disabled ? 'Running…' : 'Run Analysis'; }
  }

  // ── ─────────────────────────────────────────────────────────────────────────
  //  ORCHESTRATE PANEL  (orchestrate.html)
  //  Richer phases, direct DOM wiring, mounted by orchestrate.html's inline
  //  script — this module just exposes OrchestratePanel on window for use there.
  // ── ─────────────────────────────────────────────────────────────────────────

  const ORCH_PHASES = [
    {
      name: 'Plan Mode',
      sub:  'Bob reads INSTRUCTIONS.md + codebase structure, writes execution plan',
      pipeIdx: 0,
    },
    {
      name: 'Approval Gate',
      sub:  'Bypassed via --yolo — plan auto-approved, written to plan.md for audit',
      pipeIdx: 1,
    },
    {
      name: 'Parallel Subagents',
      sub:  'Agent 1: Impact Analysis · Agent 2: Business Rules Extraction (concurrent)',
      pipeIdx: 2,
    },
    {
      name: 'Synthesis',
      sub:  'Risk score (7 factors) computed + per-file effort estimate calculated',
      pipeIdx: 3,
    },
    {
      name: 'Write Outputs',
      sub:  '6 structured files written to .legacyflow/projects/<id>/',
      pipeIdx: 4,
    },
  ];

  window.OrchestratePanel = {
    phases:      ORCH_PHASES,
    fetchFields: fetchFields,
  };

  // ── ─────────────────────────────────────────────────────────────────────────
  //  BOOTSTRAP — activates only when on the projects page (has .page-hero)
  // ── ─────────────────────────────────────────────────────────────────────────

  async function boot() {
    // Only mount the legacy panel if .page-hero exists (projects.html)
    if (!document.querySelector('.page-hero')) return;

    try {
      const fields = await fetchFields();
      mountLegacyPanel(fields);
    } catch (_) {
      // Backend not running — silent no-op
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
