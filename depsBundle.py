from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

SUPPORTED_PYTHON_VERSIONS = ["3.9", "3.10", "3.11"]
SUPPORTED_PLATFORMS = [
    "win_amd64",
    "manylinux2014_x86_64",
    "macosx_10_9_x86_64",
    "macosx_11_0_arm64",
]
NATIVE_DEPENDENCIES = ["xxhash"]


def _get_project_dict() -> dict[str, Any]:
    if sys.version_info < (3, 11):
        with TemporaryDirectory() as toml_env:
            toml_install_pip_args = ["pip", "install", "--target", toml_env, "toml"]
            subprocess.run(toml_install_pip_args, check=True)
            sys.path.insert(0, toml_env)
            import toml
        mode = "r"
    else:
        import tomllib as toml

        mode = "rb"

    with open("pyproject.toml", mode) as pyproject_toml:
        return toml.load(pyproject_toml)


def _get_dependencies(pyproject_dict: dict[str, Any]) -> list[str]:
    if "project" not in pyproject_dict:
        raise Exception("pyproject.toml is missing project section")
    if "dependencies" not in pyproject_dict["project"]:
        raise Exception("pyproject.toml is missing dependencies section")

    dependencies = pyproject_dict["project"]["dependencies"]
    deps_noopenjd = filter(lambda dep: not dep.startswith("openjd"), dependencies)
    return list(map(lambda dep: dep.replace(" ", ""), deps_noopenjd))


def _get_package_version_regex(package: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(package)} *(.*)$")


def _get_package_version(package: str, install_path: Path) -> str:
    version_regex = _get_package_version_regex(package)
    pip_args = ["pip", "list", "--path", str(install_path)]
    output = subprocess.run(pip_args, check=True, capture_output=True).stdout.decode("utf-8")
    for line in output.split("\n"):
        match = version_regex.match(line)
        if match:
            return match.group(1)
    raise Exception(f"Could not find version for package {package}")


def _build_base_environment(working_directory: Path, dependencies: list[str]) -> Path:
    (working_directory / "base_env").mkdir()
    base_env_path = working_directory / "base_env"
    base_env_pip_args = [
        "pip",
        "install",
        "--target",
        str(base_env_path),
        "--only-binary=:all:",
        *dependencies,
    ]
    subprocess.run(base_env_pip_args, check=True)
    return base_env_path


def _get_zip_path(working_directory: Path, project_dict: dict[str, Any], platform: str) -> Path:
    if "project" not in project_dict:
        raise Exception("pyproject.toml is missing project section")
    if "name" not in project_dict["project"]:
        raise Exception("pyproject.toml is missing name section")
    base_name = project_dict["project"]["name"].replace("-", "_")
    zip_name = f"{base_name}_submitter-deps_{platform}.zip"
    return working_directory / zip_name


def _download_and_zip_for_platform(
    working_directory: Path, base_env: Path, project_dict: dict[str, Any], platform: str
) -> Path:
    print(f"Processing platform: {platform}")

    # Clear pip cache
    subprocess.run(["pip", "cache", "purge"], check=True)
    print("Cleared pip cache")

    native_dependency_paths = []
    for version in SUPPORTED_PYTHON_VERSIONS:
        native_dependency_path = (
            working_directory / "native" / f"{version.replace('.', '_')}_{platform}"
        )
        native_dependency_paths.append(native_dependency_path)
        native_dependency_path.mkdir(parents=True)

        versioned_native_dependencies = [
            f"{package_name}=={_get_package_version(package_name, base_env)}"
            for package_name in NATIVE_DEPENDENCIES
        ]

        native_dependency_pip_args = [
            "pip",
            "install",
            "--target",
            str(native_dependency_path),
            "--platform",
            platform,
            "--python-version",
            version,
            "--only-binary=:all:",
            *versioned_native_dependencies,
        ]
        subprocess.run(native_dependency_pip_args, check=True)
        print(f"Installed dependencies for Python {version} on {platform}")

    # Create zip for this platform
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Copy base environment first
        shutil.copytree(str(base_env), str(temp_path), dirs_exist_ok=True)

        # Copy platform-specific files, merging with base environment
        for native_path in native_dependency_paths:
            for file in native_path.rglob("*"):
                if file.is_file():
                    relative = file.relative_to(native_path)
                    dest_path = temp_path / relative
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(file), str(dest_path))

        zip_path = _get_zip_path(working_directory, project_dict, platform)
        shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(temp_path))
        print(f"Created zip bundle for {platform}: {zip_path}")

    return zip_path


def build_deps_bundle() -> None:
    with TemporaryDirectory() as working_directory:
        working_directory = Path(working_directory)
        project_dict = _get_project_dict()
        dependencies = _get_dependencies(project_dict)
        base_env = _build_base_environment(working_directory, dependencies)

        dependency_bundle_dir = Path.cwd() / "dependency_bundle"
        dependency_bundle_dir.mkdir(exist_ok=True)

        for platform in SUPPORTED_PLATFORMS:
            zip_path = _download_and_zip_for_platform(
                working_directory, base_env, project_dict, platform
            )

            # Copy zip to destination
            zip_destination = dependency_bundle_dir / zip_path.name
            if zip_destination.exists():
                zip_destination.unlink()
            shutil.copy(str(zip_path), str(zip_destination))
            print(f"Copied {platform} bundle to {zip_destination}")

        print("All platforms processed and zipped.")


if __name__ == "__main__":
    build_deps_bundle()
