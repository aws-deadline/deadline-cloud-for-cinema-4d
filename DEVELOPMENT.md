# AWS Deadline Cloud for Cinema4D Development

This package has two active branches:

- `mainline` -- For active development. This branch is not intended to be consumed by other packages. Any commit to this branch may break APIs, dependencies, and so on, and thus break any consumer without notice.
- `release` -- The official release of the package intended for consumers. Any breaking releases will be accompanied with an increase to this package's interface version.
## Build / Test / Release

### Build the package

```bash
hatch build
```

### Run tests

```bash
hatch run test
```

### Run linting

```bash
hatch run lint
```

### Run formatting

```bash
hatch run fmt
```

## Run tests for all supported Python versions

```bash
hatch run all:test
```

## Submitter environment

### Submitter Python environment 
The submitter requires the following modules to be installed:

```sh
pip install deadline-cloud-for-cinema-4d
pip install deadline[gui]
```

### Cinema 4D Plugin Extension Setup 

The Cinema 4D plugin extension can be downloaded from the git repo:

https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/mainline/deadline_cloud_extension/DeadlineCloud.pyp

Place this in a location accessible by C4D instances.

Add the `g_additionalModulePath` environment variable to point to the above location, so that Cinema 4D can load the plugin.

By default, Cinema4D does not see **PYTHON_PATH** and as a result **deadline-cloud-for-cinema-4d** - the extension is programmed to look for an environment variable called `DEADLINE_CLOUD_PYTHONPATH`. Setup this variable to point to the location of your **Python > Lib > site-packages**  - e.g.

```
C:\Program Files\Python311\Lib\site-packages
```

If you load a scene, click on **Extensions > Deadline Cloud Submitter** to view the submitter.

### Additional Python Libraries

Some specific versions of Cinema 4d ( e.g. `Cinema 4D 2024.1.0`) have been found to be missing some libraries key to Deadline requirements ; in later versions such as `2024.4.0` this has been resolved. 

A missing library error will manifest in errors that can be visible from the **Python** section of the **Extensions > Console** UI. These typically look like:

```
PySide6/__init__.py: Unable to import Shiboken from  ...
```

To remedy these errors, you can switch to a later version of Cinema 4D which resolves the missing libraries, or you can manually add them specifically to the Cinema 4D python module, e.g.

```
& "C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m ensurepip   
& "C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m pip install MISSING_MODULE
```       



## Worker adaptor environment

Cinema4D does not support PYTHONPATH. We set DEADLINE_CLOUD_PYTHONPATH which the
adaptor uses to set sys.path explictly and load deadline modules.

### Linux

Linux also requires the setup_c4d_env sourced first, we can override the exe
path with a c4d wrapper script that sources it then call the Commandline
client.

Example linux env below:

```
export DEADLINE_CLOUD_PYTHONPATH="/tmp/lib/python3.11/site-packages"
export DEADLINE_CINEMA4D_EXE="/opt/maxon/cinema4dr2024.200/bin/c4d"
```

### Windows

To run the adaptor on Windows, you'll have to configure the environment variable `DEADLINE_CLOUD_PYTHONPATH` (like the submitter above) and install pywin32 into Cinema4D's python. Example:

```
set DEADLINE_CLOUD_PYTHONPATH="C:\path\to\deadline-cloud\site-packages"
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe" -m ensurepip   
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe" -m pip install pywin32  
```
