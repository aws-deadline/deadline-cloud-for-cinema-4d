# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Exercise all three timeout rows and the timeout activation control."""

from test.integ import submitter_ui as ui


def configure(dialog):
    ui.set_timeout(dialog, "Task Run", enabled=True, days=1, hours=2, minutes=3)
    ui.set_timeout(dialog, "Cinema 4D launch", enabled=False)
    ui.set_timeout(dialog, "Cinema 4D shutdown", enabled=True, hours=1, minutes=4)
