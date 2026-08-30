# Sample Codebase — Fictional "Acme Distribution" IBM i System

This is a **synthetic IBM i codebase** used as the demo corpus for the LegacyFlow Orchestrator.
It simulates a real-world legacy customer master system with deliberate complexity to showcase
Impact Analysis and Business Rules Extraction workflows.

---

## Fictional Business Domain

**Acme Distribution Ltd.** runs their order management on an IBM i (AS/400) system.
The customer master is the core of the system. Every order, report, and notification
depends on a single field: **`CUST_STATUS`**.

---

## File Inventory

| File | Type | Purpose |
|---|---|---|
| `CUSTCP.rpgleinc` | Copybook / Include | Shared data structure and constants for all programs |
| `CUSTMAST.rpg` | Fixed-format OPM RPG/400 | Interactive customer master maintenance (add/change/delete) |
| `RPTGEN.rpg` | Fixed-format OPM RPG/400 | Nightly customer status report generator |
| `STATVLD.rpgle` | Free-format ILE RPGLE Service Program | Authoritative status validation API |
| `ORDPROC.rpgle` | Free-format ILE RPGLE Program | Order processing — validates status before accepting orders |
| `CRDALERT.rpgle` | Free-format ILE RPGLE Program | Daily credit and status alert scanner |
| `JOBCTL.clle` | ILE CL Program | Batch job controller — orchestrates the nightly job stream |

---

## The Pivot Field: `CUST_STATUS`

`CUST_STATUS` (1-character alphanumeric) is defined in the copybook `CUSTCP.rpgleinc`
and referenced in every program in this codebase.

### Valid Values

| Code | Meaning | Business Effect |
|---|---|---|
| `A` | **Active** | Customer can place orders; included in all reports |
| `I` | **Inactive** | Customer exists but is dormant; cannot place orders |
| `S` | **Suspended** | Blocked pending management review; no orders; alert generated if pending > 30 days |
| `C` | **Closed** | Archived; no transactions; record is read-only |

### Status State Machine

```
          +----------+
          |  Active  |----(balance > 110% limit)---> Suspended
          |    A     |----(manual deactivation)-----> Inactive
          +----------+
               ^
               |
          (reactivate)
               |
          +----------+
          | Inactive |
          |    I     |
          +----------+

          +----------+
          | Suspended|----(management lift)----------> Active
          |    S     |----(management decision)-------> Closed
          +----------+

          +----------+
          |  Closed  |   (TERMINAL — no transitions out)
          |    C     |
          +----------+
```

**Key rule:** Active → Closed directly is **blocked**. Must pass through Suspended first
(forces a management review step).

---

## Business Rules Embedded in Source

### CUSTMAST.rpg (fixed-format, interactive)
- New customers may only be created with status `A` or `I` (not `S` or `C`)
- Status transition table enforced on every update (see state machine above)
- Customers with a positive balance cannot be closed (SR_DELETE)
- Auto-suspend triggered if balance exceeds 110% of credit limit on update

### STATVLD.rpgle (free-format, service program)
- Single authoritative source for: `IsStatusValid`, `IsTransitionAllowed`, `CanPlaceOrder`, `ShouldAutoSuspend`, `GetStatusDescription`
- `SUSPEND_THRESHOLD` constant = 110 (percent of credit limit)
- Closed status is terminal — `IsTransitionAllowed` returns `*OFF` for all transitions from `C`

### ORDPROC.rpgle (free-format, order entry)
- `CanPlaceOrder` gate: only `A` (Active) customers may place orders
- Balance check: order amount must not push balance over credit limit
- Auto-suspend triggered via `ShouldAutoSuspend` after every balance update
- Result codes: `OK`, `NOSTATUS`, `BLOCKED`, `NOTFOUND`, `AUTOSUSPEND`, `ERROR`

### CRDALERT.rpgle (free-format, alert scanner)
- **Credit warning**: Active customers at ≥ 80% of credit limit → `CREDITWARN` alert
- **Stale suspension**: Suspended customers pending > 30 days → `STALSUSP` alert
- **Dormant customer**: Inactive customers with no activity > 180 days → `DORMANT` alert

### RPTGEN.rpg (fixed-format, reporting)
- Accepts a status filter parameter: `'A'`, `'I'`, `'S'`, `'C'`, or `'*'` (all)
- Suspended customers flagged with asterisk on printed report (`RPTDET_S` format)
- Counters broken down by status and region for management summary

### JOBCTL.clle (CL, batch orchestration)
- Calls `RPTGEN` twice: once for all statuses, once for suspended-only
- Calls `CRDALERT` for nightly alert generation
- Any failure triggers an escape message to `QSYSOPR` operator queue

---

## Codebase Complexity Notes (for LegacyFlow demo)

### Mix of styles
- **Fixed-format** (CUSTMAST, RPTGEN): column-sensitive, op-code based — typical RPG/400 legacy style
- **Free-format** (STATVLD, ORDPROC, CRDALERT): modern ILE RPGLE — `**FREE` header, `dcl-*`, `select/when/endsl`

### Cross-file dependencies
`CUST_STATUS` is read or written in **6 out of 7 files**:

```
CUSTCP.rpgleinc   defines  CUST_STATUS + ST_* constants
      |
      +---> CUSTMAST.rpg      read + write (interactive maintenance)
      +---> RPTGEN.rpg        read (filter + counter)
      +---> STATVLD.rpgle     logic (transition/validation API)
      +---> ORDPROC.rpgle     read + conditional write (auto-suspend)
      +---> CRDALERT.rpgle    read (alert rules)
      +---> JOBCTL.clle       indirect (calls programs that use it)
```

### Duplicated rule risk
The **auto-suspend rule** (`balance > 110% of limit → set status to S`) appears in **two places**:
- `CUSTMAST.rpg` (SR_CHANGE subroutine) — applied on interactive update
- `ORDPROC.rpgle` (after order commit) — applied on balance update via order

This duplication is a real modernization risk flagged in the Business Rules Extraction workflow.

---

## How to Use with LegacyFlow Orchestrator

1. Create a new project under `.legacyflow/projects/`
2. In `goal.md`, reference this directory: `../../../sample-codebase/`
3. Choose **Impact Analysis** or **Business Rules Extraction** workflow
4. Bob will use explore subagents to read these files in isolation and produce structured outputs

The canonical demo goal:
> *"Assess the impact of changing field `CUST_STATUS` in the customer master —
> what programs are affected, what business rules govern its values,
> and what is the risk and effort of changing it?"*
