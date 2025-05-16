import functools
import glob
import os
import sys


def glob_add_path(base, pattern):
    matches = list(glob.iglob(os.path.join(base, pattern)))
    if matches:
        return os.path.join(base, matches[0])
    return base

if sys.platform in ["win32", "cygwin"]:
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

import c4d

# This is the ID generated from Maxon's PluginCafe 
# Plugin ID generator for DeadlineCloudSubmitter.
PLUGIN_ID = 1064358

if sys.platform == "darwin":
    try:
        # This command opens the RS renderview panel at
        # Cinema 4D startup until Maxon fixes the issue 
        # of Cinema 4D crashing due to PyQt errors on their end.
        c4d.CallCommand(1038666)
    except Exception as e:
        print(f"Failed to open RS renderview panel: {e}")

class DeadlineCloudRenderCommand(c4d.plugins.CommandData):

    def _import_and_show_submitter(self):
        import deadline.cinema4d_submitter
        deadline.cinema4d_submitter.show_submitter()
    
    def _execute_for_mac(self):
        # This variable will be replaced to a path when the installer is running
        C4D_MAC_INSTALLATION_PATH = "C4D_Submitter_Installation_Dir_To_Replace"
        sys.path.append(C4D_MAC_INSTALLATION_PATH)
        try:
            self._import_and_show_submitter()
        finally:
            sys.path.remove(C4D_MAC_INSTALLATION_PATH)

    def Execute(self, doc):
        if sys.platform == "darwin":
            self._execute_for_mac()
        else:
            self._import_and_show_submitter()
        return True


if __name__ == '__main__':

    c4d.plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="AWS Deadline Cloud Submitter",
        info=0,
        help="Submit to AWS Deadline Cloud",
        dat=DeadlineCloudRenderCommand(),
        icon=None
    )
