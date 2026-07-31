# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest
import os
import site
import sys

from pathlib import Path

from deadline_test_fixtures.deadline_mock import (
    MockDeadlineScenario,
    MockDeadlineServerProcess,
    build_mock_environment,
    write_deadline_config,
)

from .utils import c4d_extra_python_paths

# Default install paths per version and platform.
_DEFAULT_C4D_VERSION = "2026"
_C4D_DEFAULT_PATHS = {
    "2026": {
        "win32": Path(r"C:\Program Files\Maxon Cinema 4D 2026"),
        "darwin": Path("/Applications/Maxon Cinema 4D 2026"),
    },
    "2025": {
        "win32": Path(r"C:\Program Files\Maxon Cinema 4D 2025"),
        "darwin": Path("/Applications/Maxon Cinema 4D 2025"),
    },
    "2024": {
        "win32": Path(r"C:\Program Files\Maxon Cinema 4D 2024"),
        "darwin": Path("/Applications/Maxon Cinema 4D 2024"),
    },
}


@pytest.fixture
def cinema4d_location() -> Path:
    """Resolve the Cinema 4D install location.

    C4D_VERSION selects both the executable version and render baseline, and
    defaults to 2026. C4D_LOCATION optionally overrides that version's default
    install path.

    Only Windows and macOS are supported (sys.platform "win32"/"darwin").
    Any other platform has no entry in _C4D_DEFAULT_PATHS and falls through
    to the EnvironmentError below.
    """
    version = os.environ.setdefault("C4D_VERSION", _DEFAULT_C4D_VERSION)
    if version not in _C4D_DEFAULT_PATHS:
        supported_versions = ", ".join(_C4D_DEFAULT_PATHS)
        raise EnvironmentError(
            f"Unsupported Cinema 4D version {version!r}. "
            f"Supported versions: {supported_versions}."
        )

    if "C4D_LOCATION" in os.environ:
        return Path(os.environ["C4D_LOCATION"])

    default_path = _C4D_DEFAULT_PATHS[version].get(sys.platform)
    if default_path and default_path.exists():
        print(f"Using Cinema 4D {version} at: {default_path}")
        os.environ["C4D_LOCATION"] = str(default_path)
        return default_path

    raise EnvironmentError(
        f"Cinema 4D {version} location not found. "
        "This test runs on Windows and macOS only. "
        "Set C4D_LOCATION to override the install directory."
    )


@pytest.fixture(autouse=True)
def _set_c4d_python_path():
    """Set C4DPYTHONPATH311 so c4dpy can find packages installed in the hatch venv."""
    # Same path recipe (src + site-packages + win32 subdirs) the GUI launch env
    # uses; shared via c4d_extra_python_paths so the two stay in lockstep.
    repo_root = Path(__file__).parent.parent.parent
    all_paths = c4d_extra_python_paths(repo_root)
    existing = os.environ.get("C4DPYTHONPATH311", "")
    new_paths = os.pathsep.join(p for p in all_paths if p and p not in existing)
    os.environ["C4DPYTHONPATH311"] = f"{new_paths}{os.pathsep}{existing}" if existing else new_paths
    print(f"C4DPYTHONPATH311={os.environ.get('C4DPYTHONPATH311')}")

    # pywin32 DLLs (pywintypes311.dll, pythoncom311.dll) live in site-packages/pywin32_system32/
    # and must be on PATH for win32file.pyd to load
    for p in site.getsitepackages():
        pywin32_sys = Path(p) / "pywin32_system32"
        if pywin32_sys.exists():
            os.environ["PATH"] = str(pywin32_sys) + os.pathsep + os.environ.get("PATH", "")
            break


@pytest.fixture
def test_cases_folder_location() -> Path:
    return Path(__file__).parent / "test_cases"


@pytest.fixture
def deadline_farm(tmp_path):
    """Start the mock Deadline Cloud backend and wire the C4D subprocess to it.

    The submitter no longer talks to real AWS. This fixture:

    1. starts the mock backend in a SEPARATE PROCESS (not a thread): the test
       blocks in xa11y's native ``wait_hidden``, which holds the GIL and would
       starve an in-process server thread, so the server needs its own GIL to
       keep serving the C4D subprocess. Its observability (call_counts,
       request_log, unmatched_requests) is read back over an admin endpoint via
       a RemoteDeadlineBackend proxy,
    2. writes a temp deadline config naming the mock's farm/queue,
    3. builds the env overlay (endpoint override + dummy creds + telemetry opt-out
       + isolated HOME + config path + mock-mode flag) that the launch env applies
       to the subprocess.

    The matching ``management.`` getaddrinfo redirect is installed inside the
    subprocess by the sidecar plugin when it sees ``DEADLINE_CLOUD_MOCK_MODE=1``.

    Yields a dict consumed by the test:
        backend, env_overlay, farm_id, queue_id, job_history_dir
    """
    # Per-response latency (seconds), approximating the real farm's observed
    # 200-600ms. Override via env var to experiment.
    delay = float(os.environ.get("MOCK_DEADLINE_RESPONSE_DELAY_S", "0.3"))

    server = MockDeadlineServerProcess(MockDeadlineScenario(response_delay_s=delay)).start()
    # start() has populated these; assert so the types narrow from Optional.
    assert server.backend is not None and server.base_url is not None
    backend = server.backend
    print(f"mock Deadline backend (separate process) listening at {server.base_url}")

    config_path = tmp_path / "deadline.config"
    home_dir = tmp_path / "home"
    job_history_dir = tmp_path / "job_history"

    write_deadline_config(
        config_path,
        farm_id=backend.farm_id,
        queue_id=backend.queue_id,
        job_history_dir=job_history_dir,
    )
    env_overlay = build_mock_environment(
        dict(os.environ),
        deadline_endpoint_url=server.base_url,
        config_path=config_path,
        home_dir=home_dir,
    )

    try:
        yield {
            "backend": backend,
            "env_overlay": env_overlay,
            "farm_id": backend.farm_id,
            "queue_id": backend.queue_id,
            "job_history_dir": job_history_dir,
        }
    finally:
        server.stop()
