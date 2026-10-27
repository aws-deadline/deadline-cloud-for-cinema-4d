# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Cinema 4D launch/render helpers and local normalization policy."""

import contextlib
import json
import os
import site
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from deadline_test_fixtures.images import assert_images_close
from deadline_test_fixtures.job_bundle import (
    BundleNormalization,
    assert_job_bundles_equal,
)
from yaml import safe_load

_T0 = time.monotonic()


def log(msg: str) -> None:
    elapsed = time.monotonic() - _T0
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%H:%M:%S")
    print(f"[integ {timestamp} +{elapsed:6.2f}s] {msg}", flush=True)


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    print(f"Args list: {args}")
    output = subprocess.run(args, capture_output=True, stdin=subprocess.DEVNULL, check=False)
    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")
    assert output.returncode == 0, f"Failed to run command {args}"
    return output


def assert_openjd_run_with_cinema4d_successful(
    cinema4d_location: Path,
    template_path: Path,
    params_path: Path,
) -> None:
    c4d_exe = resolve_c4d_exe(cinema4d_location, "Commandline")
    test_env = {
        "C4D_COMMANDLINE_EXECUTABLE": str(c4d_exe),
        "CINEMA4D_ADAPTOR_TESTING": "True",
    }

    with patch.dict(os.environ, test_env):
        with open(template_path, encoding="utf-8") as file:
            template = safe_load(file)
        with open(params_path, encoding="utf-8") as file:
            parameter_values = safe_load(file)["parameterValues"]

        job_params = {item["name"]: item["value"] for item in parameter_values}
        for name in (
            "CondaChannels",
            "CondaPackages",
            "deadline:maxFailedTasksCount",
            "deadline:priority",
            "deadline:maxRetriesPerTask",
            "deadline:targetTaskRunStatus",
        ):
            job_params.pop(name, None)

        for step in template["steps"]:
            run_command(
                [
                    "openjd",
                    "run",
                    str(template_path),
                    "--step",
                    step["name"],
                    "--job-param",
                    json.dumps(job_params),
                ]
            )


def resolve_c4d_exe(cinema4d_location: Path, name: str) -> Path:
    if sys.platform == "win32":
        executable = cinema4d_location / f"{name}.exe"
    elif sys.platform == "darwin":
        executable = cinema4d_location / f"{name}.app" / "Contents" / "MacOS" / name
    else:
        executable = cinema4d_location / name
    if not executable.exists():
        raise FileNotFoundError(f"{name} executable not found at {executable}")
    log(f"resolved {name}: {executable}")
    return executable


def c4d_extra_python_paths(repo_root: Path) -> list[str]:
    parts = [str(repo_root / "src"), *site.getsitepackages()]
    if sys.platform == "win32":
        for site_packages in site.getsitepackages():
            for subdirectory in ("win32", "win32/lib"):
                path = Path(site_packages) / subdirectory
                if path.exists():
                    parts.append(str(path))
    return list(dict.fromkeys(path for path in parts if path))


def build_submitter_pythonpath(repo_root: Path) -> str:
    return os.pathsep.join(c4d_extra_python_paths(repo_root))


def build_cinema4d_scene(
    c4dpy_location: Path,
    scene_script_location: Path,
    scene_dir: Path,
    scene_name: str,
    scene_args: tuple[str, ...] = (),
) -> Path:
    command = [
        str(c4dpy_location),
        str(scene_script_location),
        str(scene_dir),
        *scene_args,
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    # c4dpy can exit nonzero during shutdown after successfully running the script.
    # The generated scene is the reliable success signal.
    scene = scene_dir / scene_name
    if not scene.is_file():
        log(f"c4dpy scene generation failed: command={command!r}")
        log(f"c4dpy exit code: {result.returncode}")
        print(f"c4dpy stdout:\n{result.stdout}", flush=True)
        print(f"c4dpy stderr:\n{result.stderr}", flush=True)
    assert scene.is_file(), (
        f"scene.py did not save expected file at {scene} " f"(c4dpy exit code {result.returncode})"
    )
    return scene


def kill_proc(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        log(f"C4D process pid={proc.pid} already exited (rc={proc.returncode})")
        return
    log(f"terminating C4D process pid={proc.pid}")
    try:
        proc.terminate()
        proc.wait(timeout=10)
        log(f"C4D process pid={proc.pid} terminated cleanly")
    except subprocess.TimeoutExpired:
        log(f"C4D process pid={proc.pid} did not respond to terminate, killing")
        proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)
    except (ProcessLookupError, OSError) as error:
        log(f"C4D process pid={proc.pid} already gone before terminate ({error!r})")


def assert_expected_job_bundle_and_generated_job_bundle_are_equal(
    expected_job_bundle_dir_path: Path,
    generated_job_bundle_dir_path: Path,
) -> None:
    repo_parent = (
        os.path.abspath(expected_job_bundle_dir_path)
        .rsplit("deadline-cloud-for-cinema-4d", 1)[0]
        .rstrip("/\\")
    )
    assert_job_bundles_equal(
        expected_job_bundle_dir_path,
        generated_job_bundle_dir_path,
        normalization=BundleNormalization(
            replacements={"PATH_TO_BE_REPLACED": repo_parent},
            regex_replacements=(
                (
                    r"cinema4d=202[4-9]\.\* cinema4d-openjd=0\.\d+\.\*",
                    "cinema4d=2026.* cinema4d-openjd=0.8.*",
                ),
                (
                    r"scene_with_assets_[^/\\]+",
                    "scene_with_assets_NORMALIZED",
                ),
            ),
            normalized_parameter_values={
                "SubmitterIntegrationVersion": "NORMALIZED",
            },
            ignored_template_keys=("jobEnvironments",),
        ),
    )


def assert_all_images_close(
    expected_image_directory: Path,
    actual_image_directory: Path,
) -> None:
    assert_images_close(
        expected_image_directory,
        actual_image_directory,
        collapse_underscores=True,
        allow_extra=True,
    )


def resolve_expected_render_directory(
    expected_directory: Path,
    cinema4d_version: str | None,
) -> Path:
    """Resolve the render baseline for the selected Cinema 4D version."""
    if not cinema4d_version:
        raise ValueError("Cinema 4D version is required to resolve render baselines")
    return expected_directory / "renders" / cinema4d_version
