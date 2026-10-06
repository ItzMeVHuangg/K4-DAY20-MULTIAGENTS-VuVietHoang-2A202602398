---
name: log-analysis-conventions
description: Use when parsing application log files and generating JSON triage reports or error summaries.
---
1. RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service).
2. RULE: `errors` is sorted by service, then by timestamp_utc, ascending.
3. RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage".
4. Re-read this checklist carefully before finishing your task.
