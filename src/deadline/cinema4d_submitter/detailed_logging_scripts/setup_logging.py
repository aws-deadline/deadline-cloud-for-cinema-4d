# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Verify Redshift debug logging environment variable is enabled."""
import os
import sys


def verify_debug_environment_variables(enabled: str):
    """Verify that debug logging is enabled and environment variable is set."""
    if enabled != "1":
        print("Detailed logging is disabled, skipping setup.")
        return

    redshift_debug = os.environ.get("REDSHIFT_DEBUGCAPTURE")
    if redshift_debug == "1":
        print("Redshift debug logging is enabled (REDSHIFT_DEBUGCAPTURE=1)")
    else:
        print("Warning: Detailed logging requested but REDSHIFT_DEBUGCAPTURE is not set to '1'")


if __name__ == "__main__":
    enabled = sys.argv[1] if len(sys.argv) > 1 else "0"
    # Currently, this EnvEnter is not particularly useful
    # But is a required field.
    # Although, we can add more logic if necessary in the future
    verify_debug_environment_variables(enabled)
