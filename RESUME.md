# MetricTrust | Data Quality & Payment Reconciliation

SQL, Python, DuckDB, Data Validation, Automated Testing

- Implemented 22 SQL checks for key integrity, invalid amounts, chronology, and reconciliation, with severity-based quality gates and record-level exception exports.
- Identified 26.86% payment-total inflation in a naive item/payment join; reconciled BRL 20.31 million to BRL 16.01 million using correct payment grain.
- Automated fault-injection validation for 6 defect classes, detecting every injected class and preserving source records for reproducible investigation.

Measured offline benchmark results, not production business impact. Review README and reproduce the experiment before presenting the work in an interview.
