# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from pathlib import Path
from typing import Any


def get_detailed_logging_environment() -> dict[str, Any]:
    """
    Returns the DetailedLogging job environment definition.

    Returns:
        dict[str, Any]: The DetailedLogging job environment configuration
    """

    # Read the setup_logging script from file
    setup_logging_path = Path(__file__).parent / "detailed_logging_scripts" / "setup_logging.py"
    with open(setup_logging_path, "r", encoding="utf-8") as f:
        setup_logging_script = f.read()

    # Read the print_logs script from file
    print_logs_path = Path(__file__).parent / "detailed_logging_scripts" / "print_logs.py"
    with open(print_logs_path, "r", encoding="utf-8") as f:
        print_logs_script = f.read()

    return {
        "name": "DetailedLogging",
        "description": "Captures and outputs debug logs for troubleshooting when enabled.",
        "variables": {
            "REDSHIFT_DEBUGCAPTURE": "{{Param.DetailedLogging}}",
        },
        "script": {
            "embeddedFiles": [
                {
                    "name": "setupLogging",
                    "filename": "setup_logging.py",
                    "type": "TEXT",
                    "data": setup_logging_script,
                },
                {
                    "name": "printLogs",
                    "filename": "print_logs.py",
                    "type": "TEXT",
                    "data": print_logs_script,
                },
            ],
            "actions": {
                "onEnter": {
                    "command": "python",
                    "args": [
                        "{{Env.File.setupLogging}}",
                        "{{Param.DetailedLogging}}",
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
                "onExit": {
                    "command": "python",
                    "args": [
                        "{{Env.File.printLogs}}",
                        "{{Param.DetailedLogging}}",
                    ],
                    "cancelation": {"mode": "NOTIFY_THEN_TERMINATE"},
                },
            },
        },
    }
