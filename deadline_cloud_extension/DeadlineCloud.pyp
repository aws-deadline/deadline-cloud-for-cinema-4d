import os
import sys

root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root, 'modules'))

if 'deadline.cinema4d_submitter' not in sys.modules.keys():
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
