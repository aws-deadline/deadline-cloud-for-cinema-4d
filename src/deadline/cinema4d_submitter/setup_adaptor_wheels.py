# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Set up locally built adaptor wheels on a Deadline Cloud worker."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from importlib.metadata import distributions
from pathlib import Path

_EXPECTED_WHEEL_PREFIXES = (
    "openjd_adaptor_runtime-",
    "deadline-",
    "deadline_cloud_for_cinema_4d-",
)


def _find_wheels(wheels_dir: Path) -> list[Path]:
    wheels = sorted(wheels_dir.glob("*.whl"))
    selected: list[Path] = []

    for prefix in _EXPECTED_WHEEL_PREFIXES:
        matches = [wheel for wheel in wheels if wheel.name.startswith(prefix)]
        if len(matches) != 1:
            raise RuntimeError(
                f"Expected exactly one wheel matching '{prefix}*.whl' in {wheels_dir}, "
                f"found {[wheel.name for wheel in matches]}"
            )
        selected.append(matches[0])

    if len(wheels) != len(selected):
        unexpected = sorted(set(wheels) - set(selected))
        raise RuntimeError(
            "The adaptor wheels directory contains unexpected wheels: "
            + ", ".join(wheel.name for wheel in unexpected)
        )

    return selected


def _get_venv_paths(venv_dir: Path, adaptor_name: str) -> tuple[Path, Path, Path]:
    if os.name == "nt":
        bin_dir = venv_dir / "Scripts"
        return bin_dir, bin_dir / "python.exe", bin_dir / f"{adaptor_name}.exe"

    bin_dir = venv_dir / "bin"
    return bin_dir, bin_dir / "python", bin_dir / adaptor_name


def _get_site_packages(venv_python: Path) -> Path:
    result = subprocess.run(
        [
            str(venv_python),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def _get_distribution_version(site_packages: Path, distribution_name: str) -> str:
    canonical_name = re.sub(r"[-_.]+", "-", distribution_name).lower()
    for distribution in distributions(path=[str(site_packages)]):
        installed_name = distribution.metadata["Name"]
        if installed_name and re.sub(r"[-_.]+", "-", installed_name).lower() == canonical_name:
            return distribution.version
    raise RuntimeError(f"Could not find '{distribution_name}' in {site_packages}")


def _install_wheels(venv_python: Path, wheels: list[Path]) -> None:
    # The active Conda environment supplies transitive dependencies. Development
    # wheels use generated versions that may not satisfy each other's release ranges.
    subprocess.run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--force-reinstall",
            "--no-deps",
            *[str(wheel) for wheel in wheels],
        ],
        check=True,
    )


def _prioritize_site_packages(site_packages: Path) -> None:
    # Queue dependencies may be exposed through PYTHONPATH. Keep that environment
    # unchanged for Cinema 4D, but make the attached wheels win module resolution.
    (site_packages / "_deadline_adaptor_override.pth").write_text(
        f"import sys; sys.path.insert(0, {str(site_packages)!r})\n",
        encoding="utf8",
    )


def _emit_environment_changes(
    before: dict[str, str],
    *,
    venv_dir: Path,
    venv_bin: Path,
) -> None:
    after = dict(before)
    after["PATH"] = os.pathsep.join(filter(None, (str(venv_bin), before.get("PATH", ""))))
    after["VIRTUAL_ENV"] = str(venv_dir)
    after.pop("PYTHONHOME", None)

    for key, value in sorted(after.items()):
        if value != before.get(key):
            print(f"openjd_env: {key}={value}")

    for key in sorted(before):
        if key not in after:
            print(f"openjd_unset_env: {key}")


def _parse_args(argv: Sequence[str] | None = None) -> tuple[Path, Path, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("working_directory")
    parser.add_argument("wheels_directory")
    parser.add_argument("adaptor_name")
    args = parser.parse_args(argv)
    return Path(args.working_directory), Path(args.wheels_directory), args.adaptor_name


def main(argv: Sequence[str] | None = None) -> None:
    working_dir, wheels_dir, adaptor_name = _parse_args(argv)
    before_environment = dict(os.environ)

    print(f"Setting up {adaptor_name} from attached wheels on {sys.platform}")
    wheels = _find_wheels(wheels_dir)
    for wheel in wheels:
        print(f"  {wheel.name}")

    venv_dir = working_dir / "adaptor-venv"
    print(f"Creating adaptor virtual environment at {venv_dir}")
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
        check=True,
    )

    venv_bin, venv_python, adaptor_executable = _get_venv_paths(venv_dir, adaptor_name)
    _install_wheels(venv_python, wheels)

    if not adaptor_executable.is_file():
        raise RuntimeError(
            f"The override adaptor '{adaptor_name}' was not installed at {adaptor_executable}"
        )

    site_packages = _get_site_packages(venv_python)
    _prioritize_site_packages(site_packages)
    adaptor_version = _get_distribution_version(site_packages, "deadline-cloud-for-cinema-4d")
    print(
        "ADAPTOR_OVERRIDE_READY "
        f"executable={adaptor_executable} "
        f"package=deadline-cloud-for-cinema-4d version={adaptor_version}"
    )

    _emit_environment_changes(
        before_environment,
        venv_dir=venv_dir,
        venv_bin=venv_bin,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ADAPTOR_OVERRIDE_FAILED: {exc}", file=sys.stderr)
        raise
