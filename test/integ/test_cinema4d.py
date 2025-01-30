from pathlib import Path
import json
import subprocess
import os
import shutil
from difflib import unified_diff
import re


def run_command(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """
    Runs a command and returns the output. Additionally, we also log the stdout/stderr
    in case of a test failures.
    """

    print(f"Args list: {args}")
    output = subprocess.run(args, capture_output=True)

    print(f"\nstdout:\n\n{output.stdout.decode('utf-8', errors='replace')}")
    print(f"\nstderr:\n\n{output.stderr.decode('utf-8', errors='replace')}")

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


def test_submitter(
    cinema4d_location: Path,
    test_scenes_folder_location: Path,
) -> None:
    """
    Test the submitter code.
    """
    test_scene_folder_location = (
        test_scenes_folder_location / "redshift_textured_with_nonascii_characters"
    )

    test_scene_script_location = test_scene_folder_location / "scene" / "scene.py"
    job_bundle_generated = test_scene_folder_location / "generated_bundle"
    os.makedirs(job_bundle_generated, exist_ok=True)

    create_c4d_job_bundle(cinema4d_location, test_scene_script_location, job_bundle_generated)

    assert_is_valid_job_bundle(job_bundle_generated / "template.yaml")

    expected_job_bundle = test_scene_folder_location / "expected_job_bundle"
    assert_expected_job_bundle_and_generated_job_bundle_are_equal(
        expected_job_bundle, job_bundle_generated
    )

    # Clean up if the test was successful
    shutil.rmtree(job_bundle_generated, ignore_errors=True)
