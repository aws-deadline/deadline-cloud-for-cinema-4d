# AWS Deadline Cloud for Cinema4D Development

## Get started

Cinema4D does not support PYTHONPATH. We set DEADLINE_CLOUD_PYTHONPATH which the
submitter uses to set sys.path explictly and load deadline modules.

- install deadline-cloud with pyside
- set env below

```
# deadline-cloud lib with pyside
export DEADLINE_CLOUD_PYTHONPATH="/path/to/deadline-cloud/site-packages"
# configure cinema4d to find extension entry point
export g_additionalModulePath="/path/to/deadline-cloud-for-cinema4d/deadline_cloud_extension"
```

- run cinema4d
- Extensions > Deadline Cloud Submitter

## Worker environment

Cinema4D does not support PYTHONPATH. We set DEADLINE_CLOUD_PYTHONPATH which the
adaptor uses to set sys.path explictly and load deadline modules.

Linux also requires the setup_c4d_env sourced first, we can override the exe
path with a c4d wrapper script that sources it then call the Commandline
client.

Example linux env below:

```
export DEADLINE_CLOUD_PYTHONPATH="/tmp/lib/python3.11/site-packages"
export DEADLINE_CINEMA4D_EXE="/opt/maxon/cinema4dr2024.200/bin/c4d"
```
