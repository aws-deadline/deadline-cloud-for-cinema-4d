# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys
import traceback

print('c4d python version: %s' % sys.version)
print('system paths:')
for n in sys.path:
    print(n)

import c4d

# The Cinema4D Adaptor adds the `deadline` namespace directory to PYTHONPATH,
# so that importing just the cinema4d_adaptor should work.
try:
    from cinema4d_adaptor.Cinema4DClient.cinema4d_client import main # type: ignore[import]
except (ImportError, ModuleNotFoundError):
    from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client import main # type: ignore[import]

def parse_argv(argv):
    for arg in argv:
        if arg.find("-DeadlineCloudClient") == 0:
            main()
            return True
    return False


def PluginMessage(id, data):
    if id == c4d.C4DPL_COMMANDLINEARGS:
        return parse_argv(sys.argv)
    return False

# TODO: Investigate if this file is still needed. 
# Currently, PluginMessage function is not called when the plugin is loaded in adaptor tests.
# To unblock for tests, we check if the environment variable is set and if so, run the main function.
if os.environ.get("CINEMA4D_ADAPTOR_TESTING", "false").lower() == "true":
    main()