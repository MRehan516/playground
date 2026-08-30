**FREE
// -----------------------------------------------------------------
// ORDPROC  -  Order Processing
// Type:        Free-format ILE RPGLE Program
// Purpose:     Validates and records new customer orders.
//              Checks customer status before accepting an order.
//              Updates customer balance after order is committed.
//              Triggers auto-suspend if balance threshold exceeded.
//
// Calls:       STATVLD service program for all status decisions.
//
// Files used:
//   CUSTMSTPF  - Customer master physical file (Update)
//   ORDERPF    - Order header physical file (Add)
//   ORDLINEPF  - Order line physical file (Add)
//
// Parameters:
//   pCustId    - Customer ID (input)
//   pOrderAmt  - Total order amount (input)
//   pOrderRef  - Order reference returned to caller (output)
//   pResult    - Result code: 'OK', 'NOSTATUS', 'BLOCKED',
//                             'NOTFOUND', 'AUTOSUSPEND', 'ERROR'
// -----------------------------------------------------------------

/COPY CUSTCP.rpgleinc

// Prototype for STATVLD service program procedures
dcl-pr CanPlaceOrder      ind extproc('CanPlaceOrder');
  pStatus char(1) const;
end-pr;

dcl-pr ShouldAutoSuspend  ind extproc('ShouldAutoSuspend');
  pBalance   packed(9:2) const;
  pCreditLmt packed(9:2) const;
end-pr;

dcl-pr IsTransitionAllowed ind extproc('IsTransitionAllowed');
  pOldStatus char(1) const;
  pNewStatus char(1) const;
end-pr;

dcl-pr GetStatusDescription varchar(40) extproc('GetStatusDescription');
  pStatus char(1) const;
end-pr;

// Entry parameter list
dcl-pi ORDPROC;
  pCustId    packed(7:0) const;
  pOrderAmt  packed(9:2) const;
  pOrderRef  char(10);
  pResult    char(12);
end-pi;

// Local variables
dcl-s lCustFound   ind;
dcl-s lOrderId     packed(10:0);
dcl-s lNewBalance  packed(9:2);
dcl-s lStatusDesc  varchar(40);
dcl-s lAutoSusp    ind;

// -----------------------------------------------------------------
// Look up customer record
// -----------------------------------------------------------------
chain pCustId CUSTMSTPF CUSTOMER_DS;
lCustFound = %found(CUSTMSTPF);

if not lCustFound;
  pResult   = 'NOTFOUND';
  pOrderRef = *blanks;
  return;
endif;

// -----------------------------------------------------------------
// Gate 1: customer must have a known, valid status
//         (belt-and-suspenders — CUSTMAST enforces on write,
//          but orders are highest-risk entry point)
// -----------------------------------------------------------------
if CUSTOMER_DS.CUST_STATUS = *blanks;
  pResult   = 'NOSTATUS';
  pOrderRef = *blanks;
  return;
endif;

// -----------------------------------------------------------------
// Gate 2: status must permit order placement
//         Only Active (A) customers may place orders.
// -----------------------------------------------------------------
if not CanPlaceOrder(CUSTOMER_DS.CUST_STATUS);
  lStatusDesc = GetStatusDescription(CUSTOMER_DS.CUST_STATUS);
  pResult     = 'BLOCKED';
  pOrderRef   = *blanks;
  // Log the blocked attempt (would write to audit log in production)
  return;
endif;

// -----------------------------------------------------------------
// Gate 3: order amount must be positive and within remaining credit
// -----------------------------------------------------------------
if pOrderAmt <= 0;
  pResult   = 'ERROR';
  pOrderRef = *blanks;
  return;
endif;

lNewBalance = CUSTOMER_DS.CUST_BALANCE + pOrderAmt;

if lNewBalance > CUSTOMER_DS.CUST_CREDIT_LMT;
  pResult   = 'BLOCKED';
  pOrderRef = *blanks;
  return;
endif;

// -----------------------------------------------------------------
// Write order header record
// (Simplified — real implementation would generate a sequence key)
// -----------------------------------------------------------------
lOrderId  = %timestamp();    // Synthetic key for demo
pOrderRef = %char(lOrderId);

write ORDERPF;

// -----------------------------------------------------------------
// Update customer balance
// -----------------------------------------------------------------
CUSTOMER_DS.CUST_BALANCE  = lNewBalance;
CUSTOMER_DS.CUST_LAST_ACT = %date();

// -----------------------------------------------------------------
// Auto-suspend check: if new balance exceeds SUSPEND_THRESHOLD %
// of credit limit, move status from Active -> Suspended.
// This mirrors the rule in CUSTMAST but is applied here too
// because order processing is the primary balance driver.
// -----------------------------------------------------------------
lAutoSusp = ShouldAutoSuspend(
              CUSTOMER_DS.CUST_BALANCE :
              CUSTOMER_DS.CUST_CREDIT_LMT);

if lAutoSusp;
  // Validate the transition before applying (S is always allowed from A)
  if IsTransitionAllowed(CUSTOMER_DS.CUST_STATUS : ST_SUSPENDED);
    CUSTOMER_DS.CUST_STATUS = ST_SUSPENDED;
    pResult = 'AUTOSUSPEND';
  else;
    pResult = 'OK';    // Transition blocked — leave status as-is
  endif;
else;
  pResult = 'OK';
endif;

update CUSTREC CUSTOMER_DS;

return;
