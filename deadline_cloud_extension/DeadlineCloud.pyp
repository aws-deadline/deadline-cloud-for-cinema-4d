import functools
import glob
import os
import sys


def glob_add_path(base, pattern):
    matches = list(glob.iglob(os.path.join(base, pattern)))
    if matches:
        return os.path.join(base, matches[0])
    return base

if "win" in sys.platform:
    paths = [
        "resource",
        "modules",
        "python",
        "libs",
        "*win64*",
        "dlls"
    ]
    dll_path = functools.reduce(glob_add_path, paths, os.path.dirname(sys.executable))
    # Required due to a longstanding bug in C4D to not include the python dll library path required by many compiled libs
    #   Read more here: https://github.com/danbradham/wheels/issues/4#issuecomment-1772721170
    os.add_dll_directory(dll_path)

root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root, 'modules'))

if 'cinema4d_submitter' not in sys.modules.keys():
    python_path = os.environ.get('CINEMA4D_DEADLINE_CLOUD_PYTHONPATH', '')
    python_paths = python_path.split(os.pathsep)
    for n in python_paths:
        if n not in sys.path:
            sys.path.append(n)
    import deadline.cinema4d_submitter
else:
    import importlib
    importlib.reload(deadline.cinema4d_submitter)

import c4d

# This is the ID generated from Maxon's PluginCafe 
# Plugin ID generator for DeadlineCloudSubmitter.
PLUGIN_ID = 1064358

class DeadlineCloudRenderCommand(c4d.plugins.CommandData):

    def Execute(self, doc):
        deadline.cinema4d_submitter.show_submitter()
        return True


if __name__ == '__main__':

    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="Deadline Cloud Submitter",
        info=0,
        help="Submit to Deadline Cloud",
        dat=DeadlineCloudRenderCommand(),
        icon=None
    )
