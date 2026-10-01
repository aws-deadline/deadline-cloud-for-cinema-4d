# Build and Test Workflow

Complete build and test workflow for deadline-cloud-for-cinema-4d.

## Step 1: Apply Code Changes

### Quick iteration (Recommended for submitter changes)

For fast iteration on submitter code, copy the source files directly from the repo into your Cinema 4D submitter installation. This avoids rebuilding wheels each time.

**Windows (PowerShell):**
```powershell
Copy-Item -Path "src\deadline\cinema4d_submitter\*" -Destination "$env:APPDATA\DeadlineCloudSubmitter\deadline\cinema4d_submitter\" -Recurse -Force
```

**macOS:**
```bash
cp -R src/deadline/cinema4d_submitter/* ~/DeadlineCloudSubmitter/deadline/cinema4d_submitter/
```

Restart Cinema 4D after copying to pick up the changes.

For adaptor changes, you'll need to build a new conda package and deploy it to your workers. Follow the public [cinema4d-openjd conda recipe](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-openjd) to create a patched package with your changes.

### Full build (for releases, installers, or farm testing)

```bash
hatch build
```

## Step 2: Run Linting and Formatting

Before committing, ensure code passes all checks:

```bash
# Format code (black + ruff)
hatch run fmt

# Run linter (ruff check + black check + mypy)
hatch run lint

# Type checking only
hatch run typing
```

## Step 3: Run Unit Tests

Run the full unit test suite:

```bash
hatch run test
```

For faster iteration, run specific tests:

```bash
# Run tests for a specific module
hatch run test test/unit/deadline_adaptor_for_cinema4d/

# Run a single test file
hatch run test test/unit/deadline_submitter_for_cinema4d/test_scene.py

# Run tests matching a pattern
hatch run test -k "test_redshift"
```

Run against all supported Python versions:

```bash
hatch run all:test
```

## Step 4: Run Integration Tests

Integration tests require Cinema 4D installed with proper licensing. Bundle
validation runs on Windows and macOS; rendering assertions run on Windows. See
`integration-testing.md` for full setup.

### Set Cinema 4D location

```powershell
$env:C4D_LOCATION = "C:\Program Files\Maxon Cinema 4D 2026\"
```

If `C4D_LOCATION` is not set, the default Windows path `C:\Program Files\Maxon Cinema 4D 2026\` is used automatically.

### Run all integration tests

```bash
hatch run integ:test
```

## Step 5: Build the Installer

Build a local submitter installer (requires InstallBuilder):

```bash
# Windows
hatch run installer:build-installer --local-dev --platform windows

# macOS
hatch run installer:build-installer --local-dev --platform macos
```

### Test the installer

```bash
hatch run test-installer
```

## Common Issues

### Wrong Python Version
Cinema 4D 2026 uses Python 3.11, Cinema 4D 2024-2025 uses Python 3.10. Ensure your hatch environment matches.

### Wheel Not Found
Only needed for full builds. Run `hatch build` if you need wheel packages for installers or farm testing.

### Hatch Environment Issues
If builds or tests behave unexpectedly, prune all environments:
```bash
hatch env prune
```

### Coverage Threshold
The project requires minimum 23% code coverage. If tests fail on coverage, check `pyproject.toml` `[tool.coverage.report]` settings.

### Import Errors in Tests
Install test dependencies:
```bash
pip install -r requirements-testing.txt
```
