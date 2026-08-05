# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise common settings on the Shared job settings tab.

`test_cinema4d.py` loads the top-level ``configure(dialog)`` function below and
runs it against the submitter dialog after it loads and before Export bundle is
pressed.

This case deliberately changes no Job-specific settings. Those controls each
have a focused ``job_specific_*`` case.
"""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_job_name(dialog, "configured_shared_job_settings")
    ui.set_priority(dialog, 51)  # default 50 (one step; large jumps are slow)
    ui.set_max_failed_tasks(dialog, 22)  # default 20
    ui.set_max_retries(dialog, 3)  # default 5
