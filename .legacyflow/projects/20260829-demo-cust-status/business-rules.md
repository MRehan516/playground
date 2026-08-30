# Business Rules Catalogue

**Project:** 20260829-demo-cust-status  
**Codebase:** sample-codebase/  
**Extraction date:** 2026-08-29  
**Analyst:** IBM Bob 2.0 (LegacyFlow Orchestrator)

---

## Summary

| Category | Count | Duplicated | High Confidence | Medium | Low |
|---|---|---|---|---|---|
| Validation Rules (VALID) | 12 | 0 | 12 | 0 | 0 |
| Status Transitions (TRANS) | 11 | 3 | 10 | 1 | 0 |
| Boundary Conditions (BOUND) | 7 | 1 | 7 | 0 | 0 |
| Error Handling (ERROR) | 5 | 0 | 5 | 0 | 0 |
| Business Constants (CONST) | 14 | 0 | 11 | 3 | 0 |
| **Total** | **49** | **4** | **45** | **4** | **0** |

**Key finding:** The `CUST_STATUS` field drives a well-defined 4-state state machine with 12 permitted transition rules. However, the auto-suspension rule (balance > 110% of credit limit → Suspended) is **duplicated with inconsistent implementation** in `CUSTMAST.rpg` (inline, hardcoded `1.10`) and `ORDPROC.rpgle` (via `STATVLD.ShouldAutoSuspend`). This is the primary modernization risk in the codebase.

---

## Status Machine Map — CUST_STATUS

```
          +----------+
          |  ACTIVE  |──(balance > 110% limit, auto)──► SUSPENDED
          |    A     |──(manual deactivation)──────────► INACTIVE
          +────┬─────+
               │
           (reactivate)
               │
          +────┴─────+
          | INACTIVE |──(reactivate)──────────────────► ACTIVE
          |    I     |
          +──────────+

          +──────────+
          | SUSPENDED|──(management lift)──────────────► ACTIVE
          |    S     |──(management decision)──────────► CLOSED
          +──────────+

          +──────────+
          |  CLOSED  |   TERMINAL — no transitions out
          |    C     |
          +──────────+

  ✗ BLOCKED: Active → Closed (direct) — must pass through Suspended first
```

**Permitted transitions:**

| From | To | Trigger | Governing Rule | Source File |
|---|---|---|---|---|
| A | A | (no-op) | SV-012 | STATVLD.rpgle:71 |
| A | I | Manual deactivation | SV-013, CM-003 | STATVLD.rpgle:77, CUSTMAST.rpg:133 |
| A | S | Auto-suspend OR manual | SV-013, CM-003, CM-010, OP-007 | STATVLD.rpgle:77, CUSTMAST.rpg:173, ORDPROC.rpgle:141 |
| I | I | (no-op) | SV-012 | STATVLD.rpgle:71 |
| I | A | Reactivation | SV-015, CM-004 | STATVLD.rpgle:80, CUSTMAST.rpg:140 |
| S | S | (no-op) | SV-012 | STATVLD.rpgle:71 |
| S | A | Management lift | SV-016, CM-005 | STATVLD.rpgle:83, CUSTMAST.rpg:146 |
| S | C | Management close | SV-016, CM-005 | STATVLD.rpgle:83, CUSTMAST.rpg:146 |
| C | C | (no-op) | SV-012 | STATVLD.rpgle:71 |

**Blocked transitions:**

| From | To | Reason | Source File |
|---|---|---|---|
| A | C | Direct closure blocked — requires management review via Suspended | STATVLD.rpgle:61-62 |
| I | S | No path to Suspended from Inactive — must go via Active | STATVLD.rpgle:79-80 |
| I | C | No path to Closed from Inactive | STATVLD.rpgle:79-80 |
| S | I | No path to Inactive from Suspended | STATVLD.rpgle:82-83 |
| C | * | All transitions from Closed are terminal | STATVLD.rpgle:85-86 |

---

## Validation Rules (VALID)

| Rule ID | Description | Source File | Line | Code Evidence | Confidence |
|---|---|---|---|---|---|
| SV-007 | Active (A) is a valid status | STATVLD.rpgle | 30–31 | `when pStatus = ST_ACTIVE; return *ON` | High |
| SV-008 | Inactive (I) is a valid status | STATVLD.rpgle | 32–33 | `when pStatus = ST_INACTIVE; return *ON` | High |
| SV-009 | Suspended (S) is a valid status | STATVLD.rpgle | 34–35 | `when pStatus = ST_SUSPENDED; return *ON` | High |
| SV-010 | Closed (C) is a valid status | STATVLD.rpgle | 36–37 | `when pStatus = ST_CLOSED; return *ON` | High |
| SV-011 | Any status code not in {A,I,S,C} is invalid | STATVLD.rpgle | 38–40 | `other; return *OFF; // Unknown status code — reject` | High |
| SV-019 | Active description: "Active — customer can place orders" | STATVLD.rpgle | 106–107 | `return 'Active — customer can place orders'` | High |
| SV-020 | Inactive description: "Inactive — customer dormant, no orders" | STATVLD.rpgle | 108–109 | `return 'Inactive — customer dormant, no orders'` | High |
| SV-021 | Suspended description: "Suspended — blocked pending review" | STATVLD.rpgle | 110–111 | `return 'Suspended — blocked pending review'` | High |
| SV-022 | Closed description: "Closed — archived, no transactions" | STATVLD.rpgle | 112–113 | `return 'Closed — archived, no transactions'` | High |
| SV-024 | Only Active (A) customers may place orders | STATVLD.rpgle | 132 | `return (pStatus = ST_ACTIVE)` | High |
| SV-025 | Suspended customers cannot place orders even if balance is low | STATVLD.rpgle | 125 | Comment + line 132 logic | High |
| CM-002 | New customers at creation must be Active or Inactive only | CUSTMAST.rpg | 79–89 | `IF WK_STATUS <> 'A' AND WK_STATUS <> 'I'` | High |

---

## Status Transition Rules (TRANS)

| Rule ID | Description | From | To | Source File | Line | Code Evidence | Confidence |
|---|---|---|---|---|---|---|---|
| SV-012 | No-op transitions always allowed | Any | Same | STATVLD.rpgle | 71–73 | `if pOldStatus = pNewStatus; return *ON` | High |
| SV-013 | Active → Inactive or Suspended only | A | I, S | STATVLD.rpgle | 76–77 | `return (pNewStatus = ST_INACTIVE or pNewStatus = ST_SUSPENDED)` | High |
| SV-014 | Active → Closed direct is BLOCKED | A | C | STATVLD.rpgle | 61–62 | Comment + line 77 exclusion | High |
| SV-015 | Inactive → Active only | I | A | STATVLD.rpgle | 79–80 | `return (pNewStatus = ST_ACTIVE)` | High |
| SV-016 | Suspended → Active or Closed | S | A, C | STATVLD.rpgle | 82–83 | `return (pNewStatus = ST_ACTIVE or pNewStatus = ST_CLOSED)` | High |
| SV-017 | Closed is terminal — all transitions blocked | C | — | STATVLD.rpgle | 85–86 | `return *OFF; // Closed is terminal` | High |
| CM-003 | Active state machine (inline copy) | A | I, S | CUSTMAST.rpg | 133–138 | `IF WK_STATUS <> 'A' AND <> 'I' AND <> 'S'; EVAL WK_VALID = *OFF` | High |
| CM-004 | Inactive state machine (inline copy) | I | A | CUSTMAST.rpg | 140–144 | `IF WK_STATUS <> 'I' AND WK_STATUS <> 'A'; EVAL WK_VALID = *OFF` | High |
| CM-005 | Suspended state machine (inline copy) | S | A, C | CUSTMAST.rpg | 146–151 | `IF WK_STATUS <> 'S' AND <> 'A' AND <> 'C'; EVAL WK_VALID = *OFF` | High |
| CM-006 | Closed is terminal (inline copy) | C | — | CUSTMAST.rpg | 153–157 | `EVAL WK_VALID = *OFF; WK_MSG = 'Closed customers cannot be modified'` | High |
| CM-007 | A→C blocked via normal change; only via SR_DELETE or Suspended path | A | C | CUSTMAST.rpg | 127 (comment), 133–138 | Comment + transition block | Medium |

---

## Boundary Conditions (BOUND)

| Rule ID | Description | Threshold | Field Governed | Source File | Line | Code Evidence | Confidence |
|---|---|---|---|---|---|---|---|
| SV-026 | Auto-suspend triggered when balance > 110% of credit limit | 110% | CUST_STATUS → S | STATVLD.rpgle | 156–157 | `lThreshold = pCreditLmt * (SUSPEND_THRESHOLD/100); return (pBalance > lThreshold)` | High |
| SV-027 | Credit limit ≤ 0 disables auto-suspend | 0 | CUST_CREDIT_LMT | STATVLD.rpgle | 151–154 | `if pCreditLmt <= 0; return *OFF` | High |
| CM-009 | Customer balance must be zero to close | 0 | CUST_BALANCE → Closed | CUSTMAST.rpg | 195–202 | `IF CUST_BALANCE > 0; error: 'Cannot close customer with outstanding balance'` | High |
| CM-010 | Auto-suspend inline: balance > 110% triggers S (**DUPLICATE ALERT**) | 110% (hardcoded `1.10`) | CUST_STATUS → S | CUSTMAST.rpg | 169–177 | `IF CUST_BALANCE > CUST_CREDIT_LMT * 1.10 AND WK_STATUS = 'A'` | High |
| OP-003 | Order amount must be positive | > 0 | pOrderAmt | ORDPROC.rpgle | 99–103 | `if pOrderAmt <= 0; pResult = 'ERROR'` | High |
| OP-004 | New balance cannot exceed credit limit | CUST_CREDIT_LMT | CUST_BALANCE | ORDPROC.rpgle | 105–111 | `if lNewBalance > CUSTOMER_DS.CUST_CREDIT_LMT; pResult = 'BLOCKED'` | High |
| CA-002 | Active customers ≥ 80% credit usage get CREDITWARN alert | 80% | CUST_BALANCE/CUST_CREDIT_LMT | CRDALERT.rpgle | 52–63 | `if lCreditPct >= 80; lAlertType = 'CREDITWARN'` | High |

---

## Error Handling Rules (ERROR)

| Rule ID | Description | Trigger | System Response | Source File | Line | Code Evidence | Confidence |
|---|---|---|---|---|---|---|---|
| CM-008 | Invalid status transition rejected with message | `WK_VALID = *OFF` | Error displayed: "Invalid status transition: X -> Y"; no DB update | CUSTMAST.rpg | 160–166 | `EVAL WK_MSG = 'Invalid status transition: ' + WK_OLD + ' -> ' + WK_NEW; EXFMT MSGSCR; GOTO END_CHG` | High |
| OP-001 | Blank status blocks order entry | `CUST_STATUS = *blanks` | `pResult = 'NOSTATUS'; return` | ORDPROC.rpgle | 78–82 | `if CUST_STATUS = *blanks; pResult = 'NOSTATUS'` | High |
| OP-009 | Customer not found returns NOTFOUND | CHAIN failure | `pResult = 'NOTFOUND'; return` | ORDPROC.rpgle | 64–71 | `if not lCustFound; pResult = 'NOTFOUND'` | High |
| OP-010 | Blocked order returns BLOCKED code | `CanPlaceOrder = *OFF` or credit limit exceeded | `pResult = 'BLOCKED'` | ORDPROC.rpgle | 88–94, 107–111 | Two blocking gates share same result code | High |
| OP-011 | Auto-suspend acknowledged with AUTOSUSPEND code | Successful auto-suspend | `pResult = 'AUTOSUSPEND'` | ORDPROC.rpgle | 142 | `CUSTOMER_DS.CUST_STATUS = ST_SUSPENDED; pResult = 'AUTOSUSPEND'` | High |

---

## Business Constants (CONST)

| Rule ID | Constant Name | Value | Business Meaning | Source File | Line | Confidence |
|---|---|---|---|---|---|---|
| CP-001 | `ST_ACTIVE` | `'A'` | Active — customer can place orders | CUSTCP.rpgleinc | 22 | High |
| CP-002 | `ST_INACTIVE` | `'I'` | Inactive — customer dormant, no orders | CUSTCP.rpgleinc | 23 | High |
| CP-003 | `ST_SUSPENDED` | `'S'` | Suspended — blocked pending review | CUSTCP.rpgleinc | 24 | High |
| CP-004 | `ST_CLOSED` | `'C'` | Closed — archived, no transactions | CUSTCP.rpgleinc | 25 | High |
| CP-011 | `SUSPEND_THRESHOLD` | `110` | Auto-suspension triggers at 110% of credit limit | CUSTCP.rpgleinc | 33 | High |
| CP-012 | `CREDIT_STD` | `5000.00` | Standard tier credit limit ($5,000) | CUSTCP.rpgleinc | 28 | Medium |
| CP-013 | `CREDIT_PREMIUM` | `25000.00` | Premium tier credit limit ($25,000) | CUSTCP.rpgleinc | 29 | Medium |
| CP-014 | `CREDIT_INTL` | `50000.00` | International tier credit limit ($50,000) | CUSTCP.rpgleinc | 30 | Medium |
| CA-003 | *(threshold)* | `30` days | Stale suspension SLA — review required after 30 days | CRDALERT.rpgle | 70 | High |
| CA-004 | *(threshold)* | `180` days | Dormancy threshold — inactive customer review after 180 days | CRDALERT.rpgle | 82 | High |
| CA-002 | *(threshold)* | `80`% | Credit warning threshold — alert at 80% utilisation | CRDALERT.rpgle | 58 | High |
| RG-003 | *(format rule)* | `RPTDET_S` | Suspended customers printed with asterisk marker on report | RPTGEN.rpg | 134 | High |
| JC-002 | *(parameter)* | `'S'` | RPTGEN called with 'S' for suspended-only management report | JOBCTL.clle | 48 | High |
| CM-010 | *(literal)* | `1.10` | Auto-suspend hardcoded literal in CUSTMAST (**should use SUSPEND_THRESHOLD**) | CUSTMAST.rpg | 171 | High |

---

## ⚠️ Duplicated Rules (Modernization Risk)

| Global Rule ID | Description | Files | Risk if Diverged |
|---|---|---|---|
| DUP-001 | Auto-suspension rule (balance > 110% of limit → Suspended) | CUSTMAST.rpg (inline, literal `1.10`) vs ORDPROC.rpgle (via STATVLD using `SUSPEND_THRESHOLD`) | **CRITICAL**: If threshold changes in CUSTCP.rpgleinc, CUSTMAST will silently apply the wrong threshold. Customers could be suspended at the wrong balance point in interactive maintenance but correctly in order processing. |
| DUP-002 | Status state machine transition rules | CUSTMAST.rpg (inline, lines 133–157) vs STATVLD.rpgle (IsTransitionAllowed, lines 71–90) | **HIGH**: New status values or transition rule changes must be applied in both places. CUSTMAST does not call STATVLD for validation — it implements independently. Divergence creates inconsistent enforcement between interactive and programmatic paths. |
| DUP-003 | Valid status values enumerated | CUSTCP.rpgleinc (constants) vs RPTGEN.rpg (hardcoded literals `'A','I','S','C'`) | **MEDIUM**: Adding a new status requires manual edit to RPTGEN. Compiler will not detect mismatches because RPTGEN uses literals instead of constants. |
| DUP-004 | CUST_STATUS valid values documented in code | CUSTCP.rpgleinc (comment lines 4–8) + all programs that branch on status | **LOW**: Documentation-level duplication. No runtime risk, but maintenance cost to update all comments. |

### Duplication Detail

#### DUP-001: Auto-Suspension Threshold

**CUSTMAST.rpg lines 169–177 (interactive maintenance):**
```rpgle
C IF CUST_BALANCE > CUST_CREDIT_LMT * 1.10
C              AND WK_STATUS = 'A'
C    EVAL CUST_STATUS = 'S'
C    EVAL WK_MSG = 'Balance exceeds limit. Status auto-set to Suspended.'
C    EXFMT MSGSCR
C END
```

**ORDPROC.rpgle lines 134–148 (order processing):**
```rpgle
lAutoSusp = ShouldAutoSuspend(
              CUSTOMER_DS.CUST_BALANCE :
              CUSTOMER_DS.CUST_CREDIT_LMT);
if lAutoSusp;
  if IsTransitionAllowed(CUSTOMER_DS.CUST_STATUS : ST_SUSPENDED);
    CUSTOMER_DS.CUST_STATUS = ST_SUSPENDED;
```
*(STATVLD.ShouldAutoSuspend uses: `lThreshold = pCreditLmt * (SUSPEND_THRESHOLD / 100)`)*

**Recommendation:** Refactor `CUSTMAST.rpg` SR_CHANGE to call `ShouldAutoSuspend()` from STATVLD. Remove the inline `* 1.10` literal.

---

#### DUP-002: State Machine Enforcement

**CUSTMAST.rpg lines 133–157 (inline SELECT/WHEN):**
```rpgle
C SELECT
C WHEN WK_OLD_STATUS = 'A'
C   IF WK_STATUS <> 'A' AND WK_STATUS <> 'I' AND WK_STATUS <> 'S'
C     EVAL WK_VALID = *OFF ...
```

**STATVLD.rpgle lines 71–90 (authoritative API):**
```rpgle
select;
  when pOldStatus = ST_ACTIVE;
    return (pNewStatus = ST_INACTIVE or pNewStatus = ST_SUSPENDED);
  when pOldStatus = ST_INACTIVE;
    return (pNewStatus = ST_ACTIVE);
...
```

**Recommendation:** Refactor `CUSTMAST.rpg` SR_CHANGE to call `IsTransitionAllowed(WK_OLD_STATUS : WK_STATUS)` and replace the entire SELECT/WHEN block (lines 132–161).

---

## Modernization Observations

1. **STATVLD is the right pattern** — ORDPROC correctly delegates all status decisions to STATVLD. This should be the model for all programs. CUSTMAST is the outlier.

2. **RPTGEN is the highest technical debt file** — All 6 status references use hardcoded character literals instead of named constants. This is a maintenance trap.

3. **Threshold constants are in the copybook but not universally used** — `SUSPEND_THRESHOLD`, `CREDIT_STD`, `CREDIT_PREMIUM`, `CREDIT_INTL` are defined but CUSTMAST ignores `SUSPEND_THRESHOLD`. A convention requiring constant usage should be enforced.

4. **Alert thresholds are undocumented business decisions** — The values `80%` (credit warning), `30 days` (stale suspension), and `180 days` (dormancy) are hardcoded in CRDALERT with no named constants and no business documentation. They cannot be changed without a code edit and full retest.

5. **No unit tests exist for STATVLD procedures** — The `IsStatusValid`, `IsTransitionAllowed`, and `CanPlaceOrder` procedures are critical but have no tests. This should be the first modernization deliverable.

---

## Appendix: Per-File Subagent Summaries

**CUSTCP.rpgleinc:** 10 constant definitions. Single source of truth for field definition and ST_* constants. High risk — changes cascade to all 6 consumers.

**CUSTMAST.rpg:** 12 references (4 read, 2 write, 6 conditional). Contains inline state machine (duplication of STATVLD) and inline auto-suspend threshold (inconsistency with SUSPEND_THRESHOLD constant). Highest technical debt in codebase.

**STATVLD.rpgle:** 25+ conditional references. Authoritative validation API. Correctly implements all business rules. `ShouldAutoSuspend` correctly uses `SUSPEND_THRESHOLD` constant. `CanPlaceOrder` is clean single-condition check.

**ORDPROC.rpgle:** 5 direct references. Correctly delegates to STATVLD for all decisions. Double-gates auto-suspend (ShouldAutoSuspend + IsTransitionAllowed). Best-practice implementation.

**CRDALERT.rpgle:** 3 conditional references. Alert thresholds (80%, 30 days, 180 days) are hardcoded — no named constants. `GetStatusDescription` is declared in prototype but not called.

**RPTGEN.rpg:** 6 references, all hardcoded literals. No copybook constant usage. Status counter logic would break silently if a new status value is added.

**JOBCTL.clle:** 0 direct references. Indirect exposure through RPTGEN and CRDALERT. Passes `'S'` literal as parameter to RPTGEN for suspended-only report.
