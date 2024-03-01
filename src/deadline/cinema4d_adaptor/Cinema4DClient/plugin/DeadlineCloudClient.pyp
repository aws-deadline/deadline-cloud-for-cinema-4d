# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys
import traceback

import c4d

print('c4d python version: %s' % sys.version)
print('system paths:')
for n in sys.path:
    print(n)

# cinema4d doesn't use PYTHONPATH so explicitly load modules
if 'openjd' not in sys.modules.keys():
    python_path = os.getenv('DEADLINE_CLOUD_PYTHONPATH')
    python_paths = python_path.split(os.pathsep)
    for p in python_paths:
        if sys.platform == 'win32':
            try:
                os.add_dll_directory(p)
            except Exception:
                print('add_dll_directory failed: %s' % p)
        sys.path.append(p)

try:
    from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client import main
except Exception as e:
    print(e)
    traceback.print_exc()


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
