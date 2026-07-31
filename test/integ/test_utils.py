# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import pytest

from test.integ.utils import resolve_expected_render_directory


def test_resolve_expected_render_directory_uses_versioned_baseline(tmp_path) -> None:
    expected_directory = tmp_path / "expected"
    versioned_render_directory = expected_directory / "renders" / "2025"
    versioned_render_directory.mkdir(parents=True)

    assert (
        resolve_expected_render_directory(expected_directory, "2025") == versioned_render_directory
    )


def test_resolve_expected_render_directory_requires_version(tmp_path) -> None:
    expected_directory = tmp_path / "expected"

    with pytest.raises(ValueError, match="Cinema 4D version is required"):
        resolve_expected_render_directory(expected_directory, None)
