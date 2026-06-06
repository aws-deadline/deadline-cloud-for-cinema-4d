# Cinema 4D Dev Setup — Agent Workflow

Step-by-step workflow the agent follows to automate environment setup. Execute each step, validate, and only prompt the user when required.

> **Source of truth:** The canonical setup instructions live in [DEVELOPMENT.md](../../../DEVELOPMENT.md) and [README.md](../../../README.md). This guide tells the agent *how to automate* those steps — refer to the source docs for full details.

## Step 1: Detect Operating System

Check the current OS and warn about platform limitations:
- **Windows**: Full support (submitter + adaptor development)
- **macOS**: Submitter development only
- **Linux**: Adaptor development only (no submitter UI)

If the OS doesn't support the user's intended workflow, inform them of limitations.

## Step 2: Prompt for Cinema 4D Version

Ask the user which version of Cinema 4D to set up for:
- Default: 2026
- Supported: 2024, 2025, 2026

Example prompt:
```
Which version of Cinema 4D would you like to set up for? (default: 2026)
```

## Step 3: Verify Cinema 4D Installation

**Windows:**
```powershell
Test-Path "C:\Program Files\Maxon Cinema 4D {VERSION}"
Test-Path "C:\Program Files\Maxon Cinema 4D {VERSION}\Commandline.exe"
Test-Path "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\python.exe"
```

**macOS:**
```bash
test -d "/Applications/Maxon Cinema 4D {VERSION}"
test -f "/Applications/Maxon Cinema 4D {VERSION}/Cinema 4D.app/Contents/MacOS/Cinema 4D"
```

**If Cinema 4D is NOT found:** Abort and instruct the user to install Cinema 4D from the [Maxon website](https://www.maxon.net/en/cinema-4d).

**If Cinema 4D IS found:** Display confirmation and continue.

## Step 4: Verify Python 3.10+

```bash
python3 --version
```

If not installed or version < 3.10, instruct user to install Python 3.10+.

## Step 5: Read Project Documentation

Read and summarize key information from:
1. `README.md` — Project overview, compatibility, requirements
2. `DEVELOPMENT.md` — Development workflow, build instructions
3. `docs/software_arch.md` — Architecture overview

## Step 6: Install Hatch

```bash
hatch --version
```

If not installed:
```bash
pip install hatch
```

## Step 7: Build the Package

```bash
hatch build
```

Expected output:
- `dist/deadline_cloud_for_cinema_4d-{VERSION}-py3-none-any.whl`
- `dist/deadline_cloud_for_cinema_4d-{VERSION}.tar.gz`

Verify build artifacts exist.

## Step 8: Build the Installer (Optional)

If InstallBuilder is available:

```bash
hatch run installer:build-installer --local-dev --platform <windows|macos>
```

If InstallBuilder is not found, skip this step and note it in the summary.

## Step 9: Install the Submitter

### Using the Installer (if built in Step 8)
Run the installer to set up Cinema 4D automatically.

### Manual Installation (Windows)

```cmd
set SUBMITTER_LOCATION=%APPDATA%\DeadlineCloudSubmitter

"C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\python.exe" -m ensurepip
"C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\python.exe" -m pip install "deadline-cloud-for-cinema-4d[gui]" -t %SUBMITTER_LOCATION%

md %SUBMITTER_LOCATION%\cinema_4d_plugins
curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o %SUBMITTER_LOCATION%\cinema_4d_plugins\DeadlineCloud.pyp
```

Set environment variables:
```cmd
setx C4DPYTHONPATH311 %SUBMITTER_LOCATION%
setx g_additionalModulePath %SUBMITTER_LOCATION%\cinema_4d_plugins
```

### Manual Installation (macOS)

```bash
export SUBMITTER_LOCATION="/Users/$USER/DeadlineCloudSubmitter"
mkdir -p $SUBMITTER_LOCATION/cinema_4d_plugins

python3 -m ensurepip
python3 -m pip install "deadline-cloud-for-cinema-4d[gui]" -t $SUBMITTER_LOCATION

curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o $SUBMITTER_LOCATION/cinema_4d_plugins/DeadlineCloud.pyp
```

Create a launch script on the desktop:
```bash
echo '#!/bin/zsh' > ~/Desktop/Cinema4D.command
echo "export C4DPYTHONPATH311=$SUBMITTER_LOCATION" >> ~/Desktop/Cinema4D.command
echo "export g_additionalModulePath=$SUBMITTER_LOCATION/cinema_4d_plugins" >> ~/Desktop/Cinema4D.command
echo '"/Applications/Maxon Cinema 4D {VERSION}/Cinema 4D.app/Contents/MacOS/Cinema 4D"' >> ~/Desktop/Cinema4D.command
chmod +x ~/Desktop/Cinema4D.command
```

## Step 10: Set Up Integration Test Environment (Windows Only)

Integration tests are currently only supported on Windows.

> **Important:** The Python version used for installing pywin32 must match Cinema 4D's bundled Python (3.11 for Cinema 4D 2026). Using a different version (e.g., 3.13) causes DLL conflicts at runtime. You can verify Cinema 4D's Python version by checking the `resource/modules/python/libs/` folder inside the Cinema 4D installation directory.

Install pywin32 to Cinema 4D's Python:
```powershell
pip install pywin32==308 -t "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\lib\site-packages"
```

Copy PyWin32 DLLs:
```powershell
Copy-Item "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\Lib\site-packages\pywin32_system32\pythoncom311.dll" "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\dlls\"
Copy-Item "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\Lib\site-packages\pywin32_system32\pywintypes311.dll" "C:\Program Files\Maxon Cinema 4D {VERSION}\resource\modules\python\libs\win64\dlls\"
```

Set environment variables:
```powershell
$env:C4D_LOCATION = "C:\Program Files\Maxon Cinema 4D {VERSION}\"
$env:PYTHONIOENCODING = "utf-8"
$env:g_licenseServerURL = "<your-license-server>:<port>"
$env:redshift_LICENSE = "<port>@<your-license-server>"
```

## Step 11: Display Setup Summary

```
=== Cinema 4D {VERSION} Dev Setup Complete ===

✅ Python verified
✅ Hatch installed
✅ Package built
✅ Submitter installed to Cinema 4D
✅ Environment variables set

Quick Commands:
- Build:          hatch build
- Unit tests:     hatch run test
- Lint:           hatch run lint
- Format:         hatch run fmt
- Integ tests:    hatch run integ:test (Windows only)

Next Steps:
1. Configure Cinema 4D licensing for your environment
2. Launch Cinema 4D
3. Verify submitter: Extensions > AWS Deadline Cloud Submitter
4. Run unit tests: hatch run test
```

## Important Notes

- Always verify Cinema 4D installation before proceeding
- macOS requires launching Cinema 4D via the generated script (for env vars)
- pywin32 is only needed on Windows for adaptor integration tests
- InstallBuilder is optional — setup continues without it
