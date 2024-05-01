import os
import sys

root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root, 'modules'))

if 'cinema4d_submitter' not in sys.modules.keys():
    python_path = os.getenv('DEADLINE_CLOUD_PYTHONPATH')
    python_paths = python_path.split(os.pathsep)
    for n in python_paths:
        if n not in sys.path:
            sys.path.append(n)
    import deadline.cinema4d_submitter
else:
    import importlib
    importlib.reload(deadline.cinema4d_submitter)

import c4d

# TODO: replace with real id, 1062029 is a dev id
PLUGIN_ID = 1062029

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
