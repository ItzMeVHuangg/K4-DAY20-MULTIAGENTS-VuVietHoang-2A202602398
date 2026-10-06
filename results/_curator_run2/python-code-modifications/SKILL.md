---
name: python-code-modifications
description: Use when modifying existing Python code packages, adding tests, and documenting changes.
---
1. Never modify existing test files in `tests/`; only add new test files if needed.
2. `rule_type_hints`: RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value.
3. `rule_regression_tests`: RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass.
4. `rule_changelog`: RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets).
5. Re-read this checklist before finishing the task.
