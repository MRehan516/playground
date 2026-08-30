## Goal

Assess the impact of changing field CUST_STATUS in the customer master.
I want to know: every program that references this field, what each one does with it,
the risk score for making a change, the effort estimate, and the top recommended actions
before touching this field.

Additionally, extract all business rules governing CUST_STATUS and the customer master system.
Produce a structured catalogue with citations to source files and line numbers.
Flag any duplicated rules across files.

## Codebase Path

sample-codebase/

## Workflow

impact-analysis
business-rules-extraction

## Target Field

CUST_STATUS

## Scope

All files in sample-codebase/
