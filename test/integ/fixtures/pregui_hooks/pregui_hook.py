# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
"""Pre-GUI hook fixture for the Cinema 4D xa11y integ test.

deadline-cloud runs this as a subprocess before the submitter dialog is built (see
``deadline.client.ui.pre_gui_hooks.run_pre_gui_hooks``). It receives the job metadata as JSON on
stdin and returns the merged pre-GUI output as JSON on stdout: ``name`` / ``description`` land on
the submitter's settings object, and every key under ``parameters`` flows into the dialog's shared
parameter values (``deadline:priority`` sets the Priority field).

The test asserts the exported job bundle reflects exactly these values, proving the C4D submitter
wires ``run_pre_gui_hooks`` + ``apply_pre_gui_output`` correctly (PR #480). This case has no
``expected/job_bundle/`` golden dir; the assertions compare against the ``_HOOK_*`` constants in
``test/integ/test_cinema4d.py`` instead, so keep the emitted values in sync with those constants.

The test also sets ``DEADLINE_CLOUD_PREGUI_MARKER``; when present this script writes that file, so
the test can assert the hook actually ran (separately from asserting its output was applied).
"""

import json
import os
import sys

# Consume the metadata C4D passes on stdin (jobName, parameters, submitterName, ...). We do not
# branch on it here — the point of the fixture is a deterministic, asserted output — but reading it
# keeps the subprocess contract honest (a real hook would use it). A malformed/empty stdin is not a
# failure for this fixture: it still emits the fixed output below, so we deliberately ignore a
# decode error rather than abort.
try:
    json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    # No usable metadata on stdin; the fixture's output does not depend on it, so continue.
    pass

# Signal that this hook actually executed. The integ test points DEADLINE_CLOUD_PREGUI_MARKER at a
# path it checks after export, so a run that yields the wrong bundle can be told apart as "the hook
# never launched" (discovery / interpreter resolution failure) rather than "the hook ran but its
# output wasn't wired in". Best-effort: marker I/O must never break the hook's stdout contract.
_marker = os.environ.get("DEADLINE_CLOUD_PREGUI_MARKER")
if _marker:
    try:
        with open(_marker, "w", encoding="utf-8") as _fh:
            _fh.write("ran")
    except OSError:
        # The marker is best-effort diagnostics; a filesystem error writing it must not change the
        # hook's stdout contract, so the failure is intentionally ignored.
        pass

output = {
    "name": "PREGUI RAN",
    "description": "populated by pre-GUI hook",
    "parameters": {
        "deadline:priority": 88,
    },
}

json.dump(output, sys.stdout)
