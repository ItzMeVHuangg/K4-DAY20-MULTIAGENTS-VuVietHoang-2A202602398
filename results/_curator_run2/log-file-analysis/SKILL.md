---
name: log-file-analysis
description: Use when parsing log files and outputting structured triage JSON reports.
---
1. `rule_service_names`: RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service).
2. `rule_sorted_errors`: RULE: `errors` is sorted by service, then by timestamp_utc, ascending.
3. `rule_schema_header`: RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage".
4. Re-read this checklist before finishing the task.
