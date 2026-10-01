# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise fixed and target-duration task chunking controls."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_chunking(dialog, frames_per_chunk=3, target_duration_seconds=5)
