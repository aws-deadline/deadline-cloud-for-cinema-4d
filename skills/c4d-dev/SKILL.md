---
name: c4d-dev
description: Develop deadline-cloud-for-cinema-4d, including building, linting, debugging, unit testing, and creating or running xa11y integration tests for Cinema 4D, Redshift, Arnold, and V-Ray. Use when changing the submitter or adaptor, generating a new integration test case, driving the submitter UI with xa11y, capturing golden job bundles or renders, or troubleshooting project tests.
---

# Cinema 4D Dev

## Start With Repository Context

Read the instructions that own the work before editing:

- Repository overview: [`AGENTS.md`](../../AGENTS.md)
- Submitter: [`src/deadline/cinema4d_submitter/AGENTS.md`](../../src/deadline/cinema4d_submitter/AGENTS.md)
- Adaptor/client: [`src/deadline/cinema4d_adaptor/AGENTS.md`](../../src/deadline/cinema4d_adaptor/AGENTS.md)
- Tests and xa11y case contract: [`test/AGENTS.md`](../../test/AGENTS.md)

Use existing patterns from the closest implementation and current test case.
Do not reconstruct behavior from deleted integration-test directories.

## Quick Commands

```bash
hatch build
hatch run fmt
hatch run lint
hatch run test
hatch run test test/unit/path/to/test.py
hatch run all:test
hatch run integ:test
```

Always run tests through Hatch.

## Create an xa11y Integration Test

Read [references/integration-testing.md](references/integration-testing.md)
before creating or changing a case, then:

1. Select the nearest case under `test/integ/test_cases/`.
2. Create a focused `input/scene.py` that saves `<case>.c4d` in the supplied
   `actual/` directory.
3. Add `input/configure.py` only when the case must change visible submitter
   controls. Import `test.integ.submitter_ui` and reuse its helpers.
4. Add a helper to `test/integ/submitter_ui.py` when necessary. Harvest live
   selectors with `DIALOG_DUMP=1`; do not guess role/name pairs.
5. Register ordinary cases in `_CASES` in `test/integ/test_cinema4d.py`. Use a
   dedicated parametrized test only when one scene intentionally covers
   multiple expected variants.
6. Run the focused case with an explicit test path. Confirm it reaches the
   expected missing-golden failure and leaves `actual/`.
7. Normalize the generated bundle into the case's `expected/` directory,
   review every golden diff, then rerun the focused case.
8. Verify new UI selectors on both Windows and macOS. Verify renders on Windows.

Never commit `actual/`. Keep a case focused on one behavior and pair it with
unit tests for logic that does not require the real Cinema 4D UI.

## Detailed Guides

- [references/build-and-test.md](references/build-and-test.md)
- [references/dev-guide.md](references/dev-guide.md)
- [references/integration-testing.md](references/integration-testing.md)
- [references/troubleshooting.md](references/troubleshooting.md)
