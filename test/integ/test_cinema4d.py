from pathlib import Path
import os
from .utils import (
    create_c4d_job_bundle,
    assert_is_valid_job_bundle,
    assert_expected_job_bundle_and_generated_job_bundle_are_equal,
    assert_openjd_run_with_cinema4d_successful,
    assert_all_images_close,
)

from shutil import rmtree


def test_integ(
    cinema4d_location: Path,
    test_scenes_folder_location: Path,
) -> None:
    """
    Performs integration testing for Cinema 4D rendering.

    This function tests the complete workflow of creating, validating, and executing a Cinema 4D job bundle,
    followed by comparing the rendered output with expected results. It includes the following steps:
    1. Creates a job bundle from a test scene
    2. Validates the generated job bundle
    3. Compares generated bundle with expected bundle
    4. Executes the rendering job using OpenJD with Cinema 4D
    5. Compares rendered images with expected output
    6. Cleans up generated files on successful completion

    Args:
        cinema4d_location (Path): Path to the Cinema 4D installation directory
        test_scenes_folder_location (Path): Path to the root directory containing test scenes

    Raises:
        AssertionError: If any validation step fails, including:
            - non valid job bundle structure
            - Mismatch between generated and expected job bundles
            - Rendering job execution failure
            - Rendered image differences exceed tolerance

    """

    c4dpy_location = cinema4d_location / "c4dpy"
    test_scene_folder_location = (
        test_scenes_folder_location / "redshift_textured_with_nonascii_characters"
    )

    test_scene_script_location = test_scene_folder_location / "scene" / "scene.py"
    job_bundle_generated = test_scene_folder_location / "generated_bundle"
    os.makedirs(job_bundle_generated, exist_ok=True)

    create_c4d_job_bundle(c4dpy_location, test_scene_script_location, job_bundle_generated)

    assert_is_valid_job_bundle(job_bundle_generated / "template.yaml")

    expected_job_bundle = test_scene_folder_location / "expected_job_bundle"
    assert_expected_job_bundle_and_generated_job_bundle_are_equal(
        expected_job_bundle, job_bundle_generated
    )

    assert_openjd_run_with_cinema4d_successful(
        cinema4d_location,
        job_bundle_generated / "template.yaml",
        job_bundle_generated / "parameter_values.yaml",
    )

    expected_job_output = test_scene_folder_location / "expected_job_output"

    assert_all_images_close(
        job_bundle_generated / "renders",
        expected_job_output / "renders",
    )

    # Clean up if the test was successful
    rmtree(job_bundle_generated, ignore_errors=True)
