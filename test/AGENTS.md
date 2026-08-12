# AGENTS.md — test/

Test suite for deadline-cloud-for-cinema-4d. Three categories of tests.

## Directory Layout

```
test/
├── unit/                    # Unit tests (always runnable, no Cinema 4D required)
│   ├── deadline_adaptor_for_cinema4d/
│   └── deadline_submitter_for_cinema4d/
├── integ/                   # xa11y-driven submitter test, offline mock backend
│   ├── test_cases/          # Self-contained cases: input/ expected/ actual/
│   ├── test_cinema4d.py     # Drives the real submitter dialog via xa11y
│   ├── submitter_ui.py      # C4D-specific controls; re-exports shared controls
│   ├── conftest.py          # Fixtures, incl. deadline_farm (starts the mock)
│   ├── utils.py             # Test utilities
│   └── fixtures/            # Test-only sidecar plugin (auto-opens submitter)
└── installer/               # Installer tests
```

## Running Tests

Always use `hatch run` — do NOT invoke `pytest` directly.

```bash
hatch run test                                    # All unit tests
hatch run test test/unit/<path>                   # One test file or directory
hatch run test -k "test_name"                     # One test by name
hatch run all:test                                # All supported Python versions
hatch run integ:test                              # xa11y integration tests
hatch run test-installer                          # Installer tests
```

## Unit Tests

Unit tests do NOT require Cinema 4D installed. They should use mocks for the `c4d` module and other external dependencies. These are the primary tests run in CI and during development.

When adding new features or fixing bugs, always add unit tests.

## xa11y Integration Tests (`test/integ/`)

Drives the **real Deadline Cloud submitter dialog** with
[xa11y](https://xa11y.dev). It launches the real Cinema 4D GUI with
the real, unmodified plugin, opens the submitter as a user does, drives it via
the OS accessibility tree, clicks **Export bundle**, and runs the same bundle/
render assertions as the previous suite.

This file is the single source of truth for the suite — there is no separate
README.

#### The big picture

```
pytest (parent process)
  │
  ├─ deadline_farm fixture
  │     ├─ starts the mock Deadline backend in a SEPARATE process
  │     │     (own GIL — see "Why a separate process" below)
  │     ├─ writes a temp deadline config naming the mock's fake farm/queue
  │     └─ builds the subprocess env overlay (endpoint override, dummy creds,
  │           telemetry opt-out, isolated HOME, DEADLINE_CLOUD_MOCK_MODE=1)
  │
  ├─ build_cinema4d_scene()  ── runs c4dpy input/scene.py ──▶ <case>.c4d (in actual/)
  │
  └─ launches Cinema 4D GUI (child process)
         │   env: overlay above + two plugin dirs + python path
         │
         ├─ loads DeadlineCloud.pyp           (real, shipped plugin)
         ├─ loads AutoOpenSubmitter.pyp       (test-only sidecar)
         │      on C4DPL_PROGRAM_STARTED (mock mode):
         │        1. patch socket.getaddrinfo (management.* → 127.0.0.1)
         │        2. patch os.startfile → no-op (no Explorer popup)
         │        3. LoadDocument(<case>.c4d)
         │        4. CallCommand(SUBMITTER_PLUGIN_ID)  ◀─ opens real submitter
         │
         └─ Qt submitter dialog appears ──── AWS_ENDPOINT_URL_DEADLINE ───▶ mock
                ▲                                                          (parent)
                │ xa11y drives it via the OS accessibility tree
                │   - wait for dialog, wait for queue-env loading
                │   - run the case's configure(dialog) (optional)
                │   - press "Export bundle"
                ▼
         bundle written to <job_history_dir>/<YYYY-mm>/<bundle-name>/
                │
   parent ◀────┘ copies bundle flat into <case>/actual/
         │
         ├─ assert the mock saw exactly the expected calls (no unmatched routes)
         ├─ openjd check
         ├─ compare against expected/job_bundle/ (golden files)
         ├─ openjd run  (Windows only)
         └─ compare renders against expected/renders/ (Windows only)
```

#### Files

| File | Role |
|------|------|
| `test_cinema4d.py` | The test. Orchestrates scene build → launch → UI drive → assertions. Holds the `_CASES` registry. |
| `conftest.py` | Fixtures: locate Cinema 4D, set `C4DPYTHONPATH`, and `deadline_farm` (starts the mock + builds the subprocess env). |
| `submitter_ui.py` | C4D-specific controls plus re-exports of shared controls from `deadline_test_fixtures.xa11y.controls`. |
| `utils.py` | C4D executable/scene/render helpers and C4D's bundle normalization policy. Generic assertions come from `deadline-cloud-test-fixtures`. |
| `deadline_test_fixtures.deadline_mock` | Scenario-driven Deadline REST-JSON mock, out-of-process lifecycle, observability, config, and environment wiring. |
| `deadline_test_fixtures.job_bundle` | Shared case layout, bundle discovery, validation, and structural comparison. |
| `deadline_test_fixtures.images` | Shared render-image comparison. |
| `fixtures/auto_open_submitter/AutoOpenSubmitter.pyp` | Test-only C4D plugin: auto-opens the real submitter and (mock mode) applies the getaddrinfo / `os.startfile` patches. Never shipped. |
| `test_cases/<name>/` | A self-contained case (see *Anatomy of a test case*). |

#### Anatomy of a test case

Each case is a self-contained folder under `test_cases/<name>/`:

```
test_cases/<name>/
├── input/                 # what you author
│   ├── scene.py           #   required — builds <name>.c4d (runs in c4dpy)
│   └── configure.py       #   OPTIONAL — configure(dialog) drives the dialog
│                          #              before Export (runs in pytest + xa11y)
├── expected/              # what we compare against
│   ├── job_bundle/        #   golden template/parameter_values/asset_references
│   └── renders/           #   version-specific golden PNGs (Windows-only compare)
│       └── <C4D_VERSION>/ #   required baseline for each tested C4D version
└── actual/                # gitignored — runtime output; kept on failure
```

Cases are **registered explicitly** in `test_cinema4d.py`, either in `_CASES` or
in a dedicated parametrized test — adding the folder is not enough. Most cases
use `expected/{job_bundle,renders}/`; a parametrized case can keep one scene and
configurator while storing each variant under
`expected/<variant>/{job_bundle,renders}/`. The expected bundle works on every
platform and is **not** farm-specific (the mock provides fake, stable farm/queue
IDs and no queue environments), so the expected files are portable and don't
need per-farm regeneration.

`input/scene.py` runs inside **c4dpy** (Cinema 4D's headless Python) and is saved
into `actual/` (not `input/`), so render paths under `renders/` resolve into
`actual/renders/`. Cases may override the output filename, but keep this
directory stable for render comparison. Render comparison requires a baseline
under `expected/renders/<C4D_VERSION>/`. Failed Windows CI cases
retain their generated images and upload them in the
`cinema4d-<version>-render-outputs` workflow artifact for seven days.

#### Downloading render outputs from CI

Use the versioned Windows CI jobs when render goldens cannot be generated
locally:

1. Push the changes to the `feature/ci-tests` branch in this repository.
2. Wait for the **Cinema 4D xa11y Integration Tests** workflow to finish.
3. Open the workflow run and download the
   `cinema4d-<C4D_VERSION>-render-outputs` artifact for each required version.
4. Extract the artifact and review every PNG under
   `<case>/actual/renders/`.
5. Copy approved images into
   `test/integ/test_cases/<case>/expected/renders/<C4D_VERSION>/`, or
   `expected/<variant>/renders/<C4D_VERSION>/` for a parametrized case.

The artifact step always runs, but successful cases remove their `actual/`
directory before upload. Missing or mismatched goldens leave render output
behind for collection. Never commit the extracted `actual/` directories.

#### Focused settings coverage

Each settings case changes only the named setting group before exporting:

| Case | Covered controls |
|------|------------------|
| `shared_job_settings` | Job name, priority, maximum failed tasks, maximum retries |
| `job_specific_output_path` | Override Output Path and path value |
| `job_specific_multi_pass_path` | Override Multi-Pass Path and path value |
| `job_specific_take_selection` | Current, Main, Marked, and All Takes modes and their generated steps |
| `physical_multi_takes` | All Takes naming, truncation, and deduplication edge cases |
| `job_specific_frame_range` | Override Frame Range and frame expression |
| `job_specific_detailed_logging` | Detailed logging |
| `job_specific_timeouts` | Task Run, Cinema 4D launch, and Cinema 4D shutdown timeouts |
| `job_specific_save_project_with_assets` | Save project with assets |
| `job_specific_task_chunking` | Frames per chunk and target chunk duration |
| `job_specific_tile_rendering` | Tile rendering, columns, and rows |

Unit tests in
`test/unit/deadline_submitter_for_cinema4d/test_cinema4d_render_submitter.py`
also cover take-name truncation, OpenJD parameter-name collisions, and `$take`
path sanitization.

The environment-gated **Include Adaptor Wheels** developer option is excluded
because it is not present in the customer-facing dialog.

#### Finding selectors (harvesting locators for a `configure.py`)

A `configure.py` drives widgets by their accessibility **role + name** (e.g.
`dialog.descendant("check_box[name='Activate detailed logging']")`). You cannot
guess these names — and they differ between macOS (AX) and Windows (UIA), so a
configurator must be verified on both. Harvest the live names with the built-in
dump mode, which prints both settings tabs' accessibility trees and then stops
(no Export):

```bash
# macOS
DIALOG_DUMP=1 hatch -e integ run pytest --no-cov \
    test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>
```
```powershell
# Windows PowerShell
$env:DIALOG_DUMP=1; hatch -e integ run pytest --no-cov `
    test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>; $env:DIALOG_DUMP=$null
```

Each line is `<role> "<name>" value="<value>"`. Match on role + name. Shared
cross-platform widget behavior and selector gotchas are documented in
`deadline_test_fixtures.xa11y.controls`; Cinema 4D-specific selectors remain in
`submitter_ui.py`. Prefer the reusable helpers exposed by `submitter_ui.py` over
raw `descendant(...)` calls.

#### Watching a run manually (observation delays)

Two env vars slow a run down so a human can follow it. Both default to `0`
(off) — never leave them set for normal runs:

- `DIALOG_CONFIG_OBSERVE_DELAY_S=<seconds>` — pause after **every dialog
  interaction** (tab switch, checkbox, text field, each spin-button step).
  Implemented by `_observe_pause()` in `deadline_test_fixtures.xa11y.controls`,
  so every `submitter_ui.py` helper inherits it.
- `ARTIFACT_REVIEW_DELAY_S=<seconds>` — pause in `_run_integ_case` after all
  assertions pass but **before `actual/` is cleaned up**, so the exported
  bundle and renders can be inspected. The log prints the directory to look in.

```powershell
# Windows PowerShell: 5s per interaction, 60s artifact review
$env:DIALOG_CONFIG_OBSERVE_DELAY_S=5; $env:ARTIFACT_REVIEW_DELAY_S=60
hatch -e integ run python -m pytest --no-cov test/integ/test_cinema4d.py --numprocesses=0 -s -k <case>
$env:DIALOG_CONFIG_OBSERVE_DELAY_S=$null; $env:ARTIFACT_REVIEW_DELAY_S=$null
```

Related: `MOCK_DEADLINE_RESPONSE_DELAY_S` (default `0.3`) sets the mock
backend's per-response latency to approximate the real farm.

#### Offline mock architecture

The suite runs **fully offline** — no real AWS, no login, no farm. The test hook
lives in the **sidecar** plugin, not the shipped `DeadlineCloud.pyp`, so the real
plugin is exercised exactly as a customer would and no test-only code reaches
production.

- **Mock backend** (`deadline_test_fixtures.deadline_mock`): an in-memory
  Deadline Cloud simulator serving the resource-read operations used by
  submitters, with an empty queue-environment list by default. It records
  `call_counts` / `request_log` / `unmatched_requests` so the
  test can assert exactly which calls reached it and that nothing hit an unmocked
  route. Its default scenario provides stable fake farm and queue resources.
- **Separate process** (`MockDeadlineServerProcess`): the mock runs in its own
  process, NOT a thread. xa11y's native `wait_*` calls hold the CPython GIL for
  most of their duration, which would starve an in-process server thread and
  hang the test for the full 60s timeout. The out-of-process server keeps
  serving; the test reads its observability over the package's admin endpoint
  via a `RemoteDeadlineBackend` proxy.
- **Subprocess wiring** (`build_mock_environment` + the `deadline_farm` fixture):
  a temp `deadline config` names the mock's farm/queue, and the C4D subprocess
  env gets `AWS_ENDPOINT_URL_DEADLINE` → mock, dummy AWS creds, telemetry
  opt-out (so no STS call fires), an isolated `HOME`, and
  `DEADLINE_CLOUD_MOCK_MODE=1`.
- **Sidecar mock-mode patches** (gated on `DEADLINE_CLOUD_MOCK_MODE=1`, so the
  shipped plugin behaviour is untouched for real users):
  - `management.` → `127.0.0.1` `socket.getaddrinfo` redirect — the Deadline
    service model injects a `management.` host prefix, which wouldn't resolve to
    the loopback mock otherwise.
  - `os.startfile` no-op — stops the submitter popping a File Explorer window at
    the bundle folder on Windows (it would linger/pile up across runs).
- **Empty queue environments**: the mock returns an empty `ListQueueEnvironments`,
  so there are no Conda parameter widgets for `OpenJDParametersWidget.rebuild_ui`
  to recreate mid-Export and thus no reload race. Consequence: the exported
  bundle carries no `CondaPackages` / `CondaChannels`, and the expected bundles
  omit them too.

```bash
hatch run integ:test                              # all xa11y integ tests
```

CI runs this suite against Cinema 4D 2024, 2025, and 2026 on Windows and
macOS. All six jobs run in parallel. Local runs default to Cinema 4D 2026.
Set `C4D_VERSION` for an older version and set `C4D_LOCATION` only when its
installation is outside that version's default path.

The `integ:test` script hardcodes the `test/integ` path and
`--numprocesses=1`. Beware: any args you pass *replace* the path (hatch
`{args:test/integ}` falls back to the global `testpaths = ["test"]`), so
`hatch run integ:test -k physical` would scan the whole `test/` tree. To
filter or run in-process (e.g. to see C4D/xa11y stdout, which xdist hides), call
pytest directly with an explicit path — the test spawns its own subprocesses
regardless of `--numprocesses`:

```bash
hatch -e integ run pytest --no-cov test/integ/test_cinema4d.py \
    --numprocesses=0 -s -k physical
```

#### Platform support matrix

| Stage | Windows | macOS |
|-------|:-------:|:-----:|
| Scene build (`c4dpy`) | ✅ | ✅ |
| Launch + drive UI (xa11y) | ✅ | ✅ |
| Bundle comparison | ✅ | ✅ |
| `openjd run` + render compare | ✅ | ❌ skipped |

macOS stops after bundle comparison — the render path needs Conda-managed
`cinema4d-openjd`, which isn't shipped for darwin yet.

Caveats:
- Windows SMF workers run in Session 0 with no interactive desktop, so UI
  Automation returns nothing there. Local interactive sessions only.
- Accessibility roles/names differ between macOS AX and Windows UIA, so any new
  `configure.py` selector must be verified on both platforms (the page-object
  helpers in `submitter_ui.py` already are).

#### Golden-bundle comparison

Direct byte comparison would be too brittle, so before comparing, the helper
(`BundleNormalization` through the local comparison wrapper) normalizes a
fixed set of moving parts: `PATH_TO_BE_REPLACED` → the local repo prefix;
backslashes → forward slashes (preserving unicode escapes);
`SubmitterIntegrationVersion` (changes every build) → a fixed placeholder; and
`jobEnvironments` is stripped from `template.yaml`. The final assertion requires
exactly the three files (`template.yaml`, `parameter_values.yaml`,
`asset_references.yaml`) to match.

#### Adding / changing a case

**Plain case (no UI interaction):**
1. Create `test/integ/test_cases/<name>/input/scene.py`, using the nearest
   existing case as the model. The script receives the `actual/` directory as
   `sys.argv[1]` and must save `<name>.c4d` there.
2. Add `"<name>"` to `_CASES` in `test/integ/test_cinema4d.py`.
3. Run the focused case. The missing expected bundle should fail after leaving
   generated files in `actual/`.
4. Capture the golden bundle, then rerun the focused case.

**Configured case (drive the dialog before Export):** same, plus an
`input/configure.py` with a top-level `configure(dialog)` using the
`submitter_ui` page-object:

```python
from test.integ import submitter_ui as ui

def configure(dialog):
    ui.set_priority(dialog, 51)
    ui.set_detailed_logging(dialog, True)
```

It runs after the dialog settles and before Export. Reuse helpers from
`submitter_ui.py`; add a C4D-specific helper there, plus a focused unit test in
`test_submitter_ui.py`, when no helper exists. Do not guess accessibility
selectors. Use `DIALOG_DUMP=1`, then verify new selectors on Windows and macOS.
See `shared_job_settings/input/configure.py` for a worked example.

**Capturing the golden bundle:** after a run, the generated bundle is in the
case's `actual/`. Parse the three bundle files as YAML, recursively replace the
machine-specific path preceding `deadline-cloud-for-cinema-4d` with
`PATH_TO_BE_REPLACED`, normalize path separators to `/`, and remove
`jobEnvironments` from `template.yaml`. Serialize the result as block YAML
under `expected/job_bundle/`, or `expected/<variant>/job_bundle/` for a
parametrized case. On Windows, copy reviewed render PNGs from `actual/renders/`
to the matching expected directory.

Use structured YAML operations rather than text substitutions. Review every
golden diff; do not accept generated output without checking that it represents
the intended behavior.

**New mocked operation:** if a submitter change calls a Deadline operation the
mock doesn't implement, the test fails its `unmatched_requests` assertion (and
the mock logs `404 NO ROUTE`). Add a `@route`-decorated handler in
`deadline_test_fixtures.deadline_mock.MockDeadlineBackend`. If it returns
resource data, extend `MockDeadlineScenario` there. Keep DCC-specific launch
behavior in this repository.

**Pre-GUI hook case (`test_pre_gui_hook`):** this one does *not* use the `_CASES`
/ golden-bundle model — it's a standalone test asserting only the fields a
pre-GUI hook owns. The hook script `fixtures/pregui_hooks/pregui_hook.py` reads
the job metadata on stdin and emits `name` / `description` / `parameters` as JSON
on stdout. Its `hooks.yaml` (version `"1.0"`) is *not* committed: the test
generates it per-run (`_materialize_pregui_hooks_dir`) with `command` set to
`sys.executable`, because deadline-cloud resolves a hook `command` via absolute
path / hooks-dir / `shutil.which` with no env-var expansion, so a static `python`
isn't a portable interpreter (absent on macOS; PATH-dependent everywhere) and the
hook would silently not run. The test enables `settings.allow_environment_hooks`
(so the submitter sources `DEADLINE_HOOKS_DIR`) and `settings.auto_accept` (so
hooks run without the Qt confirmation prompt) in the config the `deadline_farm`
fixture wrote, points `DEADLINE_HOOKS_DIR` at that generated dir via the launch
env, Exports, then asserts a marker file proves the hook actually ran before
asserting the emitted `name`/`description` reached `template.yaml` and
`deadline:priority` reached `parameter_values.yaml` (the marker separates "hook
never launched" from "hook ran but output wasn't wired in"). To change what the
hook injects, edit `pregui_hook.py` and the `_HOOK_*` constants in
`test_cinema4d.py` together (they're the paired source of truth). It has no
`expected/job_bundle/` and never renders, so it needs no golden capture and runs
on macOS too.

## Installer Tests

Test the built installer. Requires having run `hatch run installer:build-installer` first.

```bash
hatch run test-installer
```

## Coverage

The project requires minimum 23% code coverage. Coverage settings are in `pyproject.toml` under `[tool.coverage.report]`.
