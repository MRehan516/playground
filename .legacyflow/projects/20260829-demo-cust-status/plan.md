# Analysis Plan

*Written by IBM Bob 2.0 (LegacyFlow Orchestrator) — Phase 1 (Plan Mode)*

---

## Impact Analysis Plan

### Target field: `CUST_STATUS`
### Change description: Assess full blast radius of any change to CUST_STATUS — values, format, or logic
### Codebase path: `sample-codebase/`
### Files to analyse: 7 (CUSTCP.rpgleinc, CUSTMAST.rpg, RPTGEN.rpg, STATVLD.rpgle, ORDPROC.rpgle, CRDALERT.rpgle, JOBCTL.clle)

### Subagent assignment

| Subagent | Files | Investigation focus |
|---|---|---|
| SA-1 | CUSTCP.rpgleinc | Field definition, ST_* constants, SUSPEND_THRESHOLD, credit tier constants |
| SA-2 | CUSTMAST.rpg | All read/write/conditional references; inline state machine; auto-suspend logic |
| SA-3 | STATVLD.rpgle | All 5 exported procedures; authoritative validation API |
| SA-4 | ORDPROC.rpgle | Order gates; auto-suspend write site; STATVLD delegation |
| SA-5 | CRDALERT.rpgle + RPTGEN.rpg + JOBCTL.clle | Alert rules; report filters; batch orchestration |

### Risk factors identified before deep analysis
- Field defined in shared copybook — change cascades to all consumers
- Multiple programs likely reference the same status values
- Batch job presence means interactive + batch paths must both be tested

---

## Business Rules Extraction Plan

### Codebase path: `sample-codebase/`
### Files to analyse: All 7 files
### Rule categories expected: VALID, TRANS, BOUND, ERROR, CONST

### Subagent assignment

| Subagent | File(s) | Rule categories expected |
|---|---|---|
| SA-1 | CUSTCP.rpgleinc | CONST — field codes and thresholds |
| SA-2 | CUSTMAST.rpg | VALID, TRANS, BOUND, ERROR |
| SA-3 | STATVLD.rpgle | VALID, TRANS — authoritative rule service |
| SA-4 | ORDPROC.rpgle | VALID, BOUND, ERROR |
| SA-5 | CRDALERT.rpgle + RPTGEN.rpg + JOBCTL.clle | BOUND, ERROR, CONST |

---

*Human approval gate passed. Agent mode execution commenced.*
