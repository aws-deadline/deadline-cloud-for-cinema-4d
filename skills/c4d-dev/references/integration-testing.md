# xa11y Integration Testing

Use this guide to create and run cases in `test/integ/`. Read
[`test/AGENTS.md`](../../../test/AGENTS.md) for the complete suite contract and
mock architecture.

## Understand the Execution Boundary

The suite:

1. Runs `input/scene.py` with Cinema 4D's `c4dpy`.
2. Launches the real Cinema 4D GUI and shipped submitter plugin.
3. Uses xa11y to drive the accessibility tree.
4. Exports a bundle against an offline mock Deadline backend.
5. Compares the bundle on Windows and macOS.
6. Runs the bundle and compares renders on Windows only.

Do not call `internal_create_job_bundle()` from a new integration case. The
purpose of this suite is to cover the customer-visible plugin and UI path.

## Prepare the Host

- Install and license Cinema 4D. CI targets Cinema 4D 2026.
- Install Hatch.
- Grant the terminal or Hatch Python accessibility permission on macOS.
- Run Windows tests in an interactive desktop session; UI Automation does not
  work in Session 0.
- Configure renderer licensing for renderer-specific cases.
- Set `C4D_LOCATION` when Cinema 4D is outside a known default path.

```powershell
$env:C4D_LOCATION = "C:\Program Files\Maxon Cinema 4D 2026\"
$env:redshift_LICENSE = "<port>@<license-server>"
```

The suite uses a mock Deadline service. Do not add AWS credentials, a real
farm, or real queue IDs to a case.

## Choose the Case Shape

Use a standard `_CASES` entry for one scene and one expected result:

```text
test/integ/test_cases/<case>/
├── input/
│   ├── scene.py
│   └── configure.py        # optional
└── expected/
    ├── job_bundle/
    └── renders/
```

Use a dedicated parametrized test when one scene and configurator intentionally
produce multiple variants. Follow `job_specific_take_selection`, including its
`expected/<variant>/` layout and `configure_kwargs`.

## Author `scene.py`

Start from the closest renderer or behavior case. Keep the scene deterministic
and small.

- Read the output directory from `sys.argv[1]`.
- Save `<case>.c4d` under that directory.
- Put render output under `renders/` relative to the document.
- Add only the objects, takes, materials, and render settings needed by the
  behavior under test.
- Add a `_SCENE_RELATIVE_PATHS` entry only when path handling itself is under
  test.

Do not copy a scene from deleted test directories; current cases are the source
of truth.

## Author `configure.py`

Omit this file when default dialog settings are sufficient. Otherwise expose a
top-level `configure(dialog, ...)`:

```python
from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_detailed_logging(dialog, True)
```

Prefer helpers re-exported by `test.integ.submitter_ui`. If a C4D-specific
control has no helper:

1. Run the case with `DIALOG_DUMP=1`.
2. Record the live role and accessible name on Windows and macOS.
3. Add the cross-platform interaction to `submitter_ui.py`.
4. Add focused tests to `test_submitter_ui.py`.
5. Keep raw selectors out of case configurators.

```bash
DIALOG_DUMP=1 hatch -e integ run pytest --no-cov \
    test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>
```

## Register and Run the Case

Add ordinary cases to `_CASES` in `test/integ/test_cinema4d.py`. A directory by
itself is not collected.

Run with an explicit path because arguments to `hatch run integ:test` replace
its default `test/integ` argument:

```bash
hatch -e integ run pytest --no-cov \
    test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>
```

The first complete run should fail on the missing expected bundle and retain
`actual/`. Investigate earlier failures instead of capturing their output.

## Capture and Review Goldens

After the missing-golden failure leaves output in `actual/`:

1. Select `expected/job_bundle/`, or `expected/<variant>/job_bundle/` for a
   parametrized case.
2. Parse `template.yaml`, `parameter_values.yaml`, and
   `asset_references.yaml` with a YAML parser.
3. Recursively replace the absolute path preceding
   `deadline-cloud-for-cinema-4d` with `PATH_TO_BE_REPLACED` and normalize path
   separators to `/`.
4. Remove `jobEnvironments` from `template.yaml`; comparison intentionally
   ignores it.
5. Serialize all three documents as block YAML.
6. On Windows, copy the reviewed files from `actual/renders/` into the matching
   `expected/renders/` directory.

Use structured YAML operations rather than text substitutions. Review every
golden diff before accepting it; generated output is not automatically correct.

Never commit `actual/`.

## Verify

Run focused checks first, then the full applicable suite:

```bash
hatch run test --no-cov test/integ/test_submitter_ui.py
hatch -e integ run pytest --no-cov \
    test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>
hatch run integ:test
```

Verify new selectors and bundle output on Windows and macOS. Verify render
output on Windows. Run `hatch run lint` for Python changes.

## Diagnose Failures

- **No dialog:** inspect the sidecar diagnostic log printed by the test and
  confirm accessibility permission.
- **Selector timeout:** dump the live tree; role/name pairs differ by platform.
- **No bundle:** inspect the submitter popup and mock `unmatched_requests`.
- **Bundle mismatch:** review normalized YAML rather than refreshing blindly.
- **Render mismatch:** verify renderer version, license, output naming, and
  expected images.
- **Hang:** check for a license dialog or stale Cinema 4D process.
