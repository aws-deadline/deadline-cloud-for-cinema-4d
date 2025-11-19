# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from pathlib import Path
import json
import subprocess
import os
from difflib import unified_diff
import re
from yaml import safe_load, dump
from unittest.mock import patch


import numpy as np
import PIL.Image


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """
    Runs a command and returns the output. Additionally, we also log the stdout/stderr
    in case of a test failures.
    """

    print(f"Args list: {args}")
    output = subprocess.run(args, capture_output=True)

    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")

    assert output.returncode == 0, f"Failed to run command {args}"

    return output


def assert_is_valid_job_bundle(template_location: Path) -> None:
    """
    Runs the `openjd check` command and asserts that the job bundle is valid.
    """
    output = run_command(["openjd", "check", str(template_location), "--output", "json"])

    output_json = json.loads(output.stdout)

    assert output_json["status"] == "success"


def create_c4d_job_bundle(
    cinema4d_location: Path, scene_script_location: Path, path_to_create_job_bundle: Path
) -> None:
    """
    Creates a job bundle by using 'c4dpy' to create a scene file and submit the job
    using internal integ helpers.
    """
    run_command(
        [str(cinema4d_location), str(scene_script_location), str(path_to_create_job_bundle)]
    )


def assert_openjd_run_with_cinema4d_successful(
    cinema4d_location: Path,
    template_path: Path,
    params_path: Path,
) -> None:
    """
    Runs the steps for template using Open JD run with Cinema 4D.
    Returns True if successful.
    """
    test_env = {
        # This will allow tests to know the path to run Cinema 4D Commandline.exe
        "C4D_COMMANDLINE_EXECUTABLE": str(cinema4d_location / "Commandline.exe"),
        # This is required for the Cinema 4D adaptor to work for tests.
        "CINEMA4D_ADAPTOR_TESTING": "True",
    }

    with patch.dict(os.environ, test_env):
        with open(template_path, encoding="utf-8") as f:
            template = safe_load(f)

        with open(params_path, encoding="utf-8") as f:
            parameter_values = safe_load(f)["parameterValues"]
            job_params = {item["name"]: item["value"] for item in parameter_values}

            # Remove the queue Env Parameters
            job_params.pop("CondaChannels", None)
            job_params.pop("CondaPackages", None)
            # Remove Deadline Cloud specific parameters
            job_params.pop("deadline:maxFailedTasksCount", None)
            job_params.pop("deadline:priority", None)
            job_params.pop("deadline:maxRetriesPerTask", None)
            job_params.pop("deadline:targetTaskRunStatus", None)

        for step in template["steps"]:
            output = run_command(
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

            assert output.returncode == 0


def replace_backslashes(content: str) -> str:
    """
    Replaces backslashes that are path separators.
    Note: This also preserves the backslashes in unicode characters.
    """
    content = re.sub(
        r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})", r"UNICODE_ESCAPE\1", content
    )  # To avoid unicode '\' getting replaced
    content = re.sub(r"\\+", "/", content)
    content = content.replace("UNICODE_ESCAPE", "\\")  # Add unicode escape back
    return content


def _strip_job_environments_from_template(content: str) -> str:
    """
    Strip the jobEnvironments section from a template.yaml file.
    """
    try:
        data = safe_load(content)
        if isinstance(data, dict) and "jobEnvironments" in data:
            del data["jobEnvironments"]
        return dump(data, default_flow_style=False, sort_keys=True)
    except Exception:
        # If parsing fails, return original content
        return content


def assert_expected_job_bundle_and_generated_job_bundle_are_equal(
    expected_job_bundle_dir_path: Path, generated_job_bundle_dir_path: Path
) -> None:
    """
    Assert that the generated job bundle matches with the expected job bundle.
    """

    results: dict[str, list[str]] = {
        "different_content": [],
        "identical_files": [],
    }

    # So that we can replace PATH_TO_BE_REPLACED in the expected job bundle.
    prefix_path = os.path.abspath(expected_job_bundle_dir_path).split(
        "deadline-cloud-for-cinema-4d"
    )[0]

    # Get list of files in both directories
    expected_job_bundle_files = set(
        f.name for f in expected_job_bundle_dir_path.glob("*") if f.is_file()
    )
    generated_job_bundle_files = set(
        f.name for f in generated_job_bundle_dir_path.glob("*") if f.is_file()
    )

    # Compare contents of files that exist in both directories
    common_files = expected_job_bundle_files.intersection(generated_job_bundle_files)

    for file in common_files:
        file1_path = expected_job_bundle_dir_path / file
        file2_path = generated_job_bundle_dir_path / file

        # Read files and compare their contents directly
        with (
            open(file1_path, "r", encoding="utf-8") as f1,
            open(file2_path, "r", encoding="utf-8") as f2,
        ):
            content1 = f1.read().strip()  # strip() removes trailing whitespace
            content2 = f2.read().strip()

            # Normalize line endings
            content1 = content1.replace("\r\n", "\n")
            content2 = content2.replace("\r\n", "\n")

            # Replace the prefix path in the generated job bundle files.
            content1 = content1.replace("PATH_TO_BE_REPLACED", prefix_path)
            content1 = replace_backslashes(content1)
            content2 = replace_backslashes(content2)

            # Special handling for parameter_values.yaml to normalize version differences
            if file == "parameter_values.yaml":
                content1 = _normalize_conda_packages_version(content1)
                content2 = _normalize_conda_packages_version(content2)

            # Special handling for template.yaml to strip job environments.
            # Job environments can contain code that changes frequently
            # We don't want to update all tests every time there's a
            # small change in the job environment code, so we strip it before comparison.
            # We check for the code comparison in our unit tests which should be sufficient.
            if file == "template.yaml":
                content1 = _strip_job_environments_from_template(content1)
                content2 = _strip_job_environments_from_template(content2)

            if content1 == content2:
                results["identical_files"].append(file)
            else:
                results["different_content"].append(file)
                diff = "\n".join(
                    unified_diff(content1.splitlines(), content2.splitlines(), lineterm="")
                )
                print(diff)

    assert len(results["different_content"]) == 0
    assert len(results["identical_files"]) == 3
    assert "template.yaml" in results["identical_files"]
    assert "parameter_values.yaml" in results["identical_files"]
    assert "asset_references.yaml" in results["identical_files"]


def _normalize_conda_packages_version(content: str) -> str:
    """
    Normalize the CondaPackages parameter to match the expected test format.
    This allows tests to pass regardless of the actual version numbers by
    normalizing the generated content to match the expected format.
    """

    content = re.sub(
        r"cinema4d=202[4-9].\* cinema4d-openjd=0.\d.\*",
        "cinema4d=2026.* cinema4d-openjd=0.8.*",
        content,
    )
    return content


def assert_all_images_close(expected_image_directory: Path, actual_image_directory: Path):
    for image in (expected_image_directory).iterdir():
        if not image.is_file():
            continue

        # Open the two image files with Pillow https://pillow.readthedocs.io/en/stable/index.html
        # and put them in numpy arrays. Pillow doesn't have a good built-in way to do image comparison
        # with tolerance.
        actual = np.asarray(PIL.Image.open(actual_image_directory / image.name))
        expected = np.asarray(PIL.Image.open(image))

        # Check that the two images are the same within a tolerance.
        # It's normal for there to be noise in an output image, so it is unlikely that two
        # renders will be exactly the same.
        assert np.allclose(actual, expected, atol=2)
