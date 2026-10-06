---
name: python-code-fixing-conventions
description: Use when fixing bugs, writing tests, or adding features in a Python codebase with specific verification rules.
---
1. Do not modify any existing files inside the `tests/` directory (add new test files instead if needed).
2. RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value.
3. RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass.
4. RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets).
5. Re-read this checklist carefully before finishing your task.
