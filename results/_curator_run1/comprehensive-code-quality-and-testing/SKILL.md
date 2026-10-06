---
name: comprehensive-code-quality-and-testing
description: Use when modifying codebases, fixing bugs, or implementing packages that require full type annotations, regression tests, and untouched test suites.
---
1. Never modify existing files in test directories unless explicitly instructed; only add new test files if needed.
2. Add explicit type annotations (parameters and return values) for every public function (names not starting with an underscore).
3. Add regression tests for every bug fixed (at least one test function per bug in a regression test file).
4. Record every bug fix in the changelog under the designated heading and format.
5. Run the entire test suite and verify all tests pass successfully before concluding.
