# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
import sys
import traceback

print('c4d python version: %s' % sys.version)
print('system paths:')
for n in sys.path:
    print(n)

import c4d
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client import main

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
