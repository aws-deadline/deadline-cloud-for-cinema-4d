# Dev Guide

Day-to-day development workflows. For architecture details, see the relevant AGENTS.md:
- [`AGENTS.md`](../../../AGENTS.md) — Repo overview
- [`src/deadline/cinema4d_submitter/AGENTS.md`](../../../src/deadline/cinema4d_submitter/AGENTS.md) — Submitter
- [`src/deadline/cinema4d_adaptor/AGENTS.md`](../../../src/deadline/cinema4d_adaptor/AGENTS.md) — Adaptor and client

## Python Environment

**IMPORTANT**: Use the correct Python version for your Cinema 4D version:
- Cinema 4D 2026: Python 3.11
- Cinema 4D 2024-2025: Python 3.10

For development, Python 3.10+ on your system is sufficient for unit tests.
Integration tests require Windows or macOS and Cinema 4D's bundled Python;
render assertions run only on Windows.

## Build & Install Workflow

### Build

```bash
hatch build
```

### Code Quality

```bash
hatch run fmt      # Format code (black + ruff)
hatch run lint     # Lint + type check
hatch run typing   # Type checking only (mypy)
```

### Unit Tests

```bash
hatch run test                                    # All tests
hatch run test test/unit/path/to/test.py          # Specific file
hatch run test -k "test_redshift"                 # Pattern match
hatch run all:test                                # All Python versions
```

## Submitter Development Workflow

### Quick iteration (Recommended)

Copy source files directly over the installed submitter:

**Windows (PowerShell):**
```powershell
Copy-Item -Path "src\deadline\cinema4d_submitter\*" -Destination "$env:APPDATA\DeadlineCloudSubmitter\deadline\cinema4d_submitter\" -Recurse -Force
```

**macOS:**
```bash
cp -R src/deadline/cinema4d_submitter/* ~/DeadlineCloudSubmitter/deadline/cinema4d_submitter/
```

Restart Cinema 4D to pick up the changes.

### Using the Installer

1. Build the package: `hatch build`
2. Build the installer: `hatch run installer:build-installer --local-dev --platform <windows|macos>`
3. Run the installer to set up Cinema 4D
4. Restart Cinema 4D after installation

### Manual Installation (Windows)

```cmd
set SUBMITTER_LOCATION=%APPDATA%\DeadlineCloudSubmitter
"C:\Program Files\Maxon Cinema 4D 2026\resource\modules\python\libs\win64\python.exe" -m ensurepip
"C:\Program Files\Maxon Cinema 4D 2026\resource\modules\python\libs\win64\python.exe" -m pip install "deadline-cloud-for-cinema-4d[gui]" -t %SUBMITTER_LOCATION%
md %SUBMITTER_LOCATION%\cinema_4d_plugins
curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o %SUBMITTER_LOCATION%\cinema_4d_plugins\DeadlineCloud.pyp
```

Set environment variables:
- `C4DPYTHONPATH311` → `%SUBMITTER_LOCATION%`
- `g_additionalModulePath` → `%SUBMITTER_LOCATION%\cinema_4d_plugins`

### Manual Installation (macOS)

```bash
export SUBMITTER_LOCATION="/Users/$USER/DeadlineCloudSubmitter"
mkdir -p $SUBMITTER_LOCATION/cinema_4d_plugins
python3 -m pip install "deadline-cloud-for-cinema-4d[gui]" -t $SUBMITTER_LOCATION
curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o $SUBMITTER_LOCATION/cinema_4d_plugins/DeadlineCloud.pyp
```

On macOS, launch Cinema 4D via a script that sets `C4DPYTHONPATH311` and `g_additionalModulePath`.

## Adaptor Development Workflow

For adaptor architecture, action model, and schema versioning, see [`src/deadline/cinema4d_adaptor/AGENTS.md`](../../../src/deadline/cinema4d_adaptor/AGENTS.md).

### Running the Adaptor Locally

Create two files:
1. `init-data.yaml` — Schema at `src/deadline/cinema4d_adaptor/Cinema4DAdaptor/schemas/init_data.schema.json`
2. `run-data.yaml` — Schema at `src/deadline/cinema4d_adaptor/Cinema4DAdaptor/schemas/run_data.schema.json`

Ensure Cinema 4D's command-line executable is on your PATH.

**Direct run mode** (simpler, for rapid iteration):
```bash
cinema4d-openjd run \
  --init-data file://<path-to-init-data.yaml> \
  --run-data file://<path-to-run-data.yaml>
```

**Daemon mode** (for testing sticky rendering):
```bash
cinema4d-openjd daemon start \
  --init-data file://<path-to-init-data.yaml> \
  --connection-file file://connection-info.json

cinema4d-openjd daemon run \
  --run-data file://<path-to-run-data.yaml> \
  --connection-file file://connection-info.json

cinema4d-openjd daemon stop \
  --connection-file file://connection-info.json
```

When testing daemon mode, do multiple `daemon run` commands with different inputs before `daemon stop` to catch data carryover issues.

### Running the Adaptor on a Farm

For testing on a live Deadline Cloud farm with Service Managed Fleets:

1. Create a patch for the `cinema4d-openjd` conda recipe following [these instructions](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes#create-a-patch-for-a-recipe)
2. Build a new conda package using the patch
3. Submit jobs and verify renders

## Job Template Files

Two job template variants:
- `adaptor_cinema4d_job_template.yaml` — Used when submitting with the adaptor (default)
- `default_cinema4d_job_template.yaml` — Used for direct Cinema 4D command-line rendering

## Key Data Flow

```
User fills submitter dialog
    → Submitter creates job bundle (template.yaml + parameter_values.yaml + assets)
    → Submit to Deadline Cloud
    → Worker receives task
    → Adaptor starts Cinema 4D with Cinema4DClient
    → Adaptor sends actions to Cinema4DClient via named pipes
    → Cinema4DClient executes actions (load scene, set frame, render)
    → Results reported back to Deadline Cloud
```

## Troubleshooting Quick Reference

| Issue | Fix |
|-------|-----|
| No wheel found | `hatch build` |
| Hatch not found | `pip install hatch` |
| Import errors | `pip install -r requirements-testing.txt` |
| Hatch env issues | `hatch env prune` |
| Submitter not visible | Check `C4DPYTHONPATH311` and `g_additionalModulePath` env vars |
| Adaptor not found | Ensure `cinema4d-openjd` is on PATH |
| License issues | Verify Cinema 4D and renderer licensing is configured |
