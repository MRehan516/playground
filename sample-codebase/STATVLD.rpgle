**FREE
// -----------------------------------------------------------------
// STATVLD  -  Customer Status Validation Service Program
// Type:        Free-format ILE RPGLE Service Program
// Purpose:     Provides a single, authoritative API for all
//              CUST_STATUS business rule enforcement.
//              All programs must call this service program rather
//              than duplicate status logic inline.
//
// Exported procedures:
//   IsStatusValid(status)           -> Boolean
//   IsTransitionAllowed(old, new)   -> Boolean
//   GetStatusDescription(status)    -> Varchar(40)
//   CanPlaceOrder(status)           -> Boolean
//   ShouldAutoSuspend(balance, limit) -> Boolean
// -----------------------------------------------------------------

/COPY CUSTCP.rpgleinc

// -----------------------------------------------------------------
// IsStatusValid
// Returns *ON if the given status code is a known valid value.
// -----------------------------------------------------------------
dcl-proc IsStatusValid export;
  dcl-pi *N ind;
    pStatus char(1) const;
  end-pi;

  select;
    when pStatus = ST_ACTIVE;
      return *ON;
    when pStatus = ST_INACTIVE;
      return *ON;
    when pStatus = ST_SUSPENDED;
      return *ON;
    when pStatus = ST_CLOSED;
      return *ON;
    other;
      return *OFF;    // Unknown status code — reject
  endsl;

end-proc;


// -----------------------------------------------------------------
// IsTransitionAllowed
// Enforces the status state machine.
//
// Allowed transitions:
//   A -> A  (no-op, allowed)
//   A -> I  (deactivate)
//   A -> S  (suspend — typically triggered by auto-suspend rule)
//   I -> I  (no-op, allowed)
//   I -> A  (reactivate)
//   S -> S  (no-op, allowed)
//   S -> A  (lift suspension)
//   S -> C  (close a suspended account)
//   C -> C  (no-op, allowed — idempotent)
//   All other transitions: BLOCKED
//
// Note: direct A -> C is intentionally blocked.
//       Must pass through S first (requires management review).
// -----------------------------------------------------------------
dcl-proc IsTransitionAllowed export;
  dcl-pi *N ind;
    pOldStatus char(1) const;
    pNewStatus char(1) const;
  end-pi;

  // No-op transitions always allowed
  if pOldStatus = pNewStatus;
    return *ON;
  endif;

  select;
    when pOldStatus = ST_ACTIVE;
      return (pNewStatus = ST_INACTIVE or pNewStatus = ST_SUSPENDED);

    when pOldStatus = ST_INACTIVE;
      return (pNewStatus = ST_ACTIVE);

    when pOldStatus = ST_SUSPENDED;
      return (pNewStatus = ST_ACTIVE or pNewStatus = ST_CLOSED);

    when pOldStatus = ST_CLOSED;
      return *OFF;    // Closed is terminal — no transitions out

    other;
      return *OFF;    // Unknown old status — block
  endsl;

end-proc;


// -----------------------------------------------------------------
// GetStatusDescription
// Returns a human-readable description of a status code.
// Used by report programs and error messages.
// -----------------------------------------------------------------
dcl-proc GetStatusDescription export;
  dcl-pi *N varchar(40);
    pStatus char(1) const;
  end-pi;

  select;
    when pStatus = ST_ACTIVE;
      return 'Active — customer can place orders';
    when pStatus = ST_INACTIVE;
      return 'Inactive — customer dormant, no orders';
    when pStatus = ST_SUSPENDED;
      return 'Suspended — blocked pending review';
    when pStatus = ST_CLOSED;
      return 'Closed — archived, no transactions';
    other;
      return 'Unknown status: ' + pStatus;
  endsl;

end-proc;


// -----------------------------------------------------------------
// CanPlaceOrder
// Returns *ON only if the customer's status permits order entry.
// Only Active customers may place new orders.
// Suspended customers cannot place orders even if balance is low.
// -----------------------------------------------------------------
dcl-proc CanPlaceOrder export;
  dcl-pi *N ind;
    pStatus char(1) const;
  end-pi;

  return (pStatus = ST_ACTIVE);

end-proc;


// -----------------------------------------------------------------
// ShouldAutoSuspend
// Returns *ON if the customer's balance has exceeded the
// auto-suspension threshold (SUSPEND_THRESHOLD % of credit limit).
// Called after every balance update in ORDPROC.
// -----------------------------------------------------------------
dcl-proc ShouldAutoSuspend export;
  dcl-pi *N ind;
    pBalance   packed(9:2) const;
    pCreditLmt packed(9:2) const;
  end-pi;

  dcl-s lThreshold packed(9:2);

  // Avoid division by zero — if no credit limit, do not auto-suspend
  if pCreditLmt <= 0;
    return *OFF;
  endif;

  lThreshold = pCreditLmt * (SUSPEND_THRESHOLD / 100);
  return (pBalance > lThreshold);

end-proc;
