**FREE
// -----------------------------------------------------------------
// CRDALERT  -  Credit and Status Alert Notifier
// Type:        Free-format ILE RPGLE Program
// Purpose:     Scans the customer master daily and generates
//              alert messages for:
//                1. Active customers within 20% of credit limit
//                2. Suspended customers pending > 30 days
//                3. Inactive customers with no activity > 180 days
//              Results are written to ALERTPF for downstream
//              notification processing (email/SMS gateway).
//
// Calls:       STATVLD for status descriptions
// Files used:
//   CUSTMSTPF  - Customer master physical file (Input)
//   ALERTPF    - Alert output physical file (Add)
// -----------------------------------------------------------------

/COPY CUSTCP.rpgleinc

// Prototype for STATVLD
dcl-pr GetStatusDescription varchar(40) extproc('GetStatusDescription');
  pStatus char(1) const;
end-pr;

// Local variables
dcl-s lDaysSuspended int(5);
dcl-s lDaysInactive  int(5);
dcl-s lCreditPct     packed(5:2);
dcl-s lAlertType     char(10);
dcl-s lAlertMsg      varchar(120);
dcl-s lToday         date;
dcl-s lEOF           ind;

lToday = %date();
lEOF   = *OFF;

// -----------------------------------------------------------------
// Sequential scan — read all customers
// -----------------------------------------------------------------
read CUSTMSTPF CUSTOMER_DS;
lEOF = %eof(CUSTMSTPF);

dow not lEOF;

  lAlertType = *blanks;
  lAlertMsg  = *blanks;

  select;

    // ----- Rule 1: Active customer approaching credit limit -----
    when CUSTOMER_DS.CUST_STATUS = ST_ACTIVE
      and CUSTOMER_DS.CUST_CREDIT_LMT > 0;

      lCreditPct = (CUSTOMER_DS.CUST_BALANCE
                    / CUSTOMER_DS.CUST_CREDIT_LMT) * 100;

      if lCreditPct >= 80;    // 80% threshold for credit warning
        lAlertType = 'CREDITWARN';
        lAlertMsg  = 'Customer ' + %char(CUSTOMER_DS.CUST_ID)
                     + ' (' + CUSTOMER_DS.CUST_NAME + ') is at '
                     + %char(lCreditPct) + '% of credit limit.';
      endif;

    // ----- Rule 2: Suspended customer stale for > 30 days -----
    when CUSTOMER_DS.CUST_STATUS = ST_SUSPENDED;

      lDaysSuspended = %diff(lToday : CUSTOMER_DS.CUST_LAST_ACT : *days);

      if lDaysSuspended > 30;
        lAlertType = 'STALSUSP';
        lAlertMsg  = 'Customer ' + %char(CUSTOMER_DS.CUST_ID)
                     + ' has been Suspended for '
                     + %char(lDaysSuspended) + ' days. Review required.';
      endif;

    // ----- Rule 3: Inactive customer with no activity > 180 days -----
    when CUSTOMER_DS.CUST_STATUS = ST_INACTIVE;

      lDaysInactive = %diff(lToday : CUSTOMER_DS.CUST_LAST_ACT : *days);

      if lDaysInactive > 180;
        lAlertType = 'DORMANT';
        lAlertMsg  = 'Customer ' + %char(CUSTOMER_DS.CUST_ID)
                     + ' has been Inactive for '
                     + %char(lDaysInactive) + ' days. Consider closing.';
      endif;

  endsl;

  // Write alert if one was generated
  if lAlertType <> *blanks;
    write ALERTREC;
  endif;

  read CUSTMSTPF CUSTOMER_DS;
  lEOF = %eof(CUSTMSTPF);

enddo;

*inlr = *on;
return;
