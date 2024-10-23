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

Install deadline in a [supported search path](https://developers.maxon.net/docs/py/2024_0_0a/manuals/manual_py_libraries.html#python-interpreter-bound-search-paths) or set a [custom interpreter path](https://developers.maxon.net/docs/py/2024_0_0a/manuals/manual_py_libraries.html#custom-interpreter-bound-search-paths) to the deadline install location.

- install deadline-cloud with pyside
- set env below

```
# deadline-cloud lib with pyside
export C4DPYTHONPATH311 "/path/to/deadline-cloud/site-packages"
# configure cinema4d to find extension entry point
export g_additionalModulePath="/path/to/deadline-cloud-for-cinema4d/deadline_cloud_extension"
```

- run cinema4d
- Extensions > Deadline Cloud Submitter

## Worker adaptor environment

Install deadline in a [supported search path](https://developers.maxon.net/docs/py/2024_0_0a/manuals/manual_py_libraries.html#python-interpreter-bound-search-paths) or set a [custom interpreter path](https://developers.maxon.net/docs/py/2024_0_0a/manuals/manual_py_libraries.html#custom-interpreter-bound-search-paths) to the deadline install location.

### Linux

Linux also requires the setup_c4d_env sourced first, we can override the exe
path with a c4d wrapper script that sources it then call the Commandline
client.

Example linux env below:

```
export C4DPYTHONPATH311 "/path/to/deadline-cloud/site-packages"
export DEADLINE_CINEMA4D_EXE="/opt/maxon/cinema4dr2024.200/bin/c4d"
```