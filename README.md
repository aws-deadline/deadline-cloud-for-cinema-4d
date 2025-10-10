# AWS Deadline Cloud for Cinema 4D

[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-cinema-4d.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-cinema-4d)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-cinema-4d.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-cinema-4d)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-cinema-4d.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/mainline/LICENSE)

AWS Deadline Cloud for Cinema 4D is a python package that allows users to create [Deadline Cloud][deadline-cloud] jobs from within Cinema 4D. It provides both the implementation of a Cinema 4D extension for your workstation that helps you offload the computation for your rendering workloads
to Deadline Cloud to free up your workstation's compute for other tasks, and the implementation of a command-line
adaptor application based on the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] that improves Deadline Cloud's
ability to run Cinema 4D efficiently on your render farm.

For instructions on installing and using this integration, visit the [user guide](https://aws-deadline.github.io/deadline-cloud-for-cinema-4d).

[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd-template]: https://github.com/OpenJobDescription/openjd-specifications/wiki/2023-09-Template-Schemas
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle
[service-managed-fleets]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html
[default-queue-environment]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html#conda-queue-environment
[deadline-cloud-submitter]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/submitter.html
[deadline-cloud-monitor]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/monitor-onboarding.html
[usage-based-licensing]: https://aws.amazon.com/deadline-cloud/features/

## Compatibility

This library requires:

1. Cinema 4D 2024 - 2025
   * Redshift is supported but not required
2. Python 3.9 or higher; but Python 3.11 is recommended as this is the version Cinema 4D uses natively.
3. Windows or macOS operating system for job submission and Windows operating system for job rendering. There are some instructions below on how to setup the adaptors for job rendering on Linux but they are experimental.
4. When rendering using Redshift with Cinema 4D on NVIDIA GPUs, NVIDIA GRID driver version 551.78 or later is required. Using older drivers can result in job failures.

**Important:** Workers hosts with GPUs that run the Cinema 4D adaptor must have sufficient RAM (at least 2x the amount of VRAM) to run Cinema 4D correctly. For example, if your GPU has 16GB VRAM, your system should have at least 32GB RAM. Insufficient memory can lead to [unstable rendering behavior](https://help.maxon.net/c4d/s26/de-de/Content/_REDSHIFT_/html/Dealing+with+Out-Of-RAM+situations.html).

## Getting Started

The Cinema 4D integration for Deadline Cloud has two components that you will need to install:

1. The Cinema 4D submitter extension must be installed on the workstation that you will use to submit jobs; and
2. The Cinema 4D adaptor must be installed on all of your Deadline Cloud worker hosts that will be running the Cinema 4D jobs that you submit.

Before submitting any large, complex, or otherwise compute-heavy Cinema 4D render jobs to your farm using the submitter and adaptor that you
set up, we strongly recommend that you construct a simple test scene that can be rendered quickly and submit renders of that scene to your farm to ensure that your setup is functioning correctly.

## Submitter

The Cinema 4D submitter extension creates a button in Cinema 4D (`Extensions` > `AWS Deadline Cloud Submitter`) that can be used to submit jobs to Deadline Cloud.
Clicking this button reveals an interface to submit a job to Deadline Cloud.
It automatically determines the files required based on the loaded scene, allows the user to specify render options, builds an
[Open Job Description template][openjd-template] that defines the workflow, and submits the job to the farm and queue of your choosing.
The submitter includes your settings, such as Redshift plugin settings and multi-pass paths, in the submission to Deadline Cloud.

There are two installation options:
1. The [official Deadline Cloud submitter installer][deadline-cloud-submitter] (Recommended)
2. Manual installation

After installing, you can access the submitter in the Cinema 4D interface via `Extensions` > `AWS Deadline Cloud Submitter`.

For most setups, you will also want to install the [Deadline Cloud monitor][deadline-cloud-monitor].

### Manually installing the submitter

#### Windows

In Windows `cmd`
```
:: Set installation location in AppData folder
set SUBMITTER_LOCATION=%APPDATA%\DeadlineCloudSubmitter

:: Install pip using Cinema 4D's bundled Python
"C:\Program Files\Maxon Cinema 4D 2025\resource\modules\python\libs\win64\python.exe" -m ensurepip

:: Install required Python packages to our custom location
"C:\Program Files\Maxon Cinema 4D 2025\resource\modules\python\libs\win64\python.exe" -m pip install deadline-cloud-for-cinema-4d "deadline[gui]" -t %SUBMITTER_LOCATION%

:: Create plugins directory
md %SUBMITTER_LOCATION%\cinema_4d_plugins

:: Download the Deadline Cloud plugin from GitHub
curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o %SUBMITTER_LOCATION%\cinema_4d_plugins\DeadlineCloud.pyp

:: Set C4DPYTHONPATH311 environment variable - if it doesn't exist, create it; if it exists, append to it
if not defined C4DPYTHONPATH311 (setx C4DPYTHONPATH311 %SUBMITTER_LOCATION%) else (setx C4DPYTHONPATH311 %SUBMITTER_LOCATION%;%C4DPYTHONPATH311%)

:: Set g_additionalModulePath environment variable for plugins - if it doesn't exist, create it; if it exists, append to it
if not defined g_additionalModulePath (setx g_additionalModulePath %SUBMITTER_LOCATION%\cinema_4d_plugins) else (setx g_additionalModulePath %SUBMITTER_LOCATION%\cinema_4d_plugins;%g_additionalModulePath%)

```

#### Mac

In a Mac terminal:
```
# Set the base location
export SUBMITTER_LOCATION="/Users/$USER/DeadlineCloudSubmitter"

# Create directory
mkdir -p $SUBMITTER_LOCATION

# Install Python packages
python3 -m ensurepip
python3 -m pip install deadline-cloud-for-cinema-4d "deadline[gui]" -t $SUBMITTER_LOCATION

# Create plugins directory
mkdir -p $SUBMITTER_LOCATION/cinema_4d_plugins

# Download the plugin
curl https://raw.githubusercontent.com/aws-deadline/deadline-cloud-for-cinema-4d/refs/heads/mainline/deadline_cloud_extension/DeadlineCloud.pyp -o $SUBMITTER_LOCATION/cinema_4d_plugins/DeadlineCloud.pyp

# Create the launch script
echo "#!/bin/zsh" > ~/Desktop/Cinema4D.command
eval echo "export C4DPYTHONPATH311=${SUBMITTER_LOCATION}\${C4DPYTHONPATH311:+:\$C4DPYTHONPATH311}" >> ~/Desktop/Cinema4D.command
eval echo "export g_additionalModulePath=${SUBMITTER_LOCATION}/cinema_4d_plugins\${g_additionalModulePath:+:\$g_additionalModulePath}" >> ~/Desktop/Cinema4D.command
echo '"/Applications/Maxon Cinema 4D 2025/Cinema 4D.app/Contents/MacOS/Cinema 4D"' >> ~/Desktop/Cinema4D.command

# Make the launch script executable
chmod +x ~/Desktop/Cinema4D.command
```

To open Cinema 4D on Mac, click `Cinema4D.command` on your desktop. After you load a scene, click on `Extensions` > `AWS Deadline Cloud Submitter` to view the submitter.

## Adaptor

Jobs created by the Cinema 4D submitter require the adaptor to be installed on your worker hosts.

The adaptor application is a command-line Python-based application that enhances the functionality of Cinema 4D for running within a render farm like Deadline Cloud. Its primary purpose for existing is to add a "sticky rendering" functionality where a single process instance of Cinema 4D is able to load the scene file and then dynamically be instructed to perform desired renders without needing to close and re-launch Cinema 4D between them. It also has additional benefits such as support for path mapping, and reporting the progress of your render to Deadline Cloud. The alternative to "sticky rendering" is that Cinema 4D would need to be run separately for each render that is done, and close afterwards.
Some scenes can take 10's of minutes just to load for rendering, so being able to keep the application open and loaded between
renders can be a significant time-saving optimization; particularly when the render itself is quick.

**Important:** Workers hosts with GPUs must have sufficient RAM (at least 2x the amount of VRAM) to run Cinema 4D correctly. For example, if your GPU has 16GB VRAM, your system should have at least 32GB RAM. Insufficient memory can lead to [unstable rendering behavior](https://help.maxon.net/c4d/s26/de-de/Content/_REDSHIFT_/html/Dealing+with+Out-Of-RAM+situations.html).

**Note for Redshift users:** When rendering with Redshift on NVIDIA GPUs, NVIDIA GRID driver version 551.78 or later is required. Using older drivers can result in job failures.

Both fleet types in Deadline Cloud support the Cinema 4D adaptor:
1. Service managed fleets
2. Customer managed fleets

The Cinema 4D integration for Deadline Cloud is supported on Windows fleets (service managed and customer managed).
Linux support is experimental and can only be done on customer managed fleets.

### Service managed fleets

On [service managed fleets][service-managed-fleets], the Cinema 4D adaptor is automatically available via the `deadline-cloud` Conda channel with the [default Queue Environment][default-queue-environment].

### Customer managed fleets

There are two options for setting up the Cinema 4D adaptor on customer managed fleets:
1. Manually installing on worker hosts
2. Using customer-managed Conda packages

#### Manually installing on worker hosts

Both the installed adaptor and the Cinema 4D executable must be available on the PATH of the user that will be running your jobs.

You can also set the `C4D_COMMANDLINE_EXECUTABLE` to point to the Cinema 4D executable. The adaptor must still be on the PATH.

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-cinema-4d
```

After installation and adding it to the PATH it can then be used as a command line tool:
```sh
$ cinema4d-openjd --help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

#### Using customer-managed Conda packages

Cinema 4D Conda packages are available in the "deadline-cloud" Conda channel on service managed Windows fleets.

However, if you prefer, you can build the Cinema 4D Conda packages yourself. There are conda recipes in our samples Github repository for [`cinema4d-2025` on Windows](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-2025) and
[`cinema4d-openjd` on Windows and Linux](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-openjd).

For instructions on building conda recipes on Deadline Cloud, see [this article](https://aws.amazon.com/blogs/media/create-a-conda-package-and-channel-for-aws-deadline-cloud/).
Though it refers to Blender, the process applies to Cinema 4D recipes as well.

## Worker Licensing for Cinema 4D

### Service Managed Fleets

[Usage based licensing][usage-based-licensing] for Cinema 4D 2024 and 2025 is available on Deadline Cloud service managed fleets with no additional setup.

If you prefer to use your own licensing for service managed fleets, you can also [connect service-managed fleets to a custom license server](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/smf-byol.html).

### Customer Managed Fleets

You can use usage based licensing on customer managed fleets by [connecting them to a license endpoint](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/cmf-ubl.html).

You can also use your own licensing for customer managed fleets.

## Viewing the Job Bundle that will be submitted

To submit a job, the submitter first generates a [Job Bundle][job-bundle], and then uses functionality from the
[Deadline client library][deadline-cloud-client] package to submit the Job Bundle to your render farm to run. If you would like to see
the job that will be submitted to your farm, then you can use the "Export Bundle" button in the submitter to export the
Job Bundle to a location of your choice. If you want to submit the job from the export, rather than through the
submitter plug-in then you can use the [Deadline Cloud application][deadline-cloud-client] to submit that bundle to your farm.

[job-bundle]: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development.
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API.
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API.

## Security

We take all security reports seriously. When we receive such reports, we will
investigate and subsequently address any potential vulnerabilities as quickly
as possible. If you discover a potential security issue in this project, please
notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/)
or directly via email to [AWS Security](mailto:aws-security@amazon.com). Please do not
create a public GitHub issue in this project.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/release/docs/telemetry.md) for more information.

## Troubleshooting

### Additional Python Libraries in the submitter

Some versions of Cinema 4D ( e.g. `Cinema 4D 2024.1.0`) have been found to be missing some libraries key to Deadline Cloud requirements ; in later versions such as `2024.4.0` this has been resolved.

A missing library error will manifest in errors that can be visible from the **Python** section of the **Extensions > Console** UI. These typically look like:

```
PySide6/__init__.py: Unable to import Shiboken from  ...
```

To remedy these errors, you can switch to a later version of Cinema 4D which resolves the missing libraries, or you can manually add them specifically to the Cinema 4D python module, e.g in Windows it will be something like:

```
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m ensurepip
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m pip install MISSING_MODULE
```

## 3rd party plugins

Cinema 4D for Deadline Cloud works with several common 3rd party plugins. Many
plugins can be installed on Service Managed Fleets using a [conda recipe](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/README.md)
from the [deadline-cloud-samples repository](https://github.com/aws-deadline/deadline-cloud-samples).



### Autodesk Arnold

Follow [these instructions](https://github.com/aws-deadline/deadline-cloud-samples/blob/main/conda_recipes/cinema4d-c4dtoa-2025/README.md) to build the C4DtoA conda package. This recipe supports both Windows and Linux fleets.

#### Installation instructions for workstations

1. Install the Cinema 4D to Arnold plugin by following [instructions here](https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_cinema_4d_ci_Installation_ci_Installing_Arnold_for_Cinema_4D_on_Windows_html).
2. [Optional] Verify that "Arnold" works with Cinema 4D locally. You can test this using any of the sample scenes available [here](https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_cinema_4d_ci_Tutorials_ci_Learning_Scenes_html)
3. Submit to Deadline Cloud from Cinema 4D by using menu command **Extensions > AWS Deadline Cloud Submitter** with `cinema4d-c4dtoa` in the Conda Packages parameter.

#### Licensing instructions

Arnold licensing is available by default on service managed fleets. To setup licensing on a customer managed fleet, follow the licensing instructions [here](https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_cinema_4d_ci_Getting_Started_ci_Licensing_Arnold_html)

#### Version compatibility

We ran C4dtoA v4.8.3.1 on Cinema 4D 2025. But more recent versions should still be compatible with latest versions of Cinema 4D, etc. For more information on compatibility refer to the [C4dtoA release notes](https://help.autodesk.com/view/ARNOL/ENU/?guid=arnold_for_cinema_4d_481_html).

### Chaos Group V-Ray

Follow [these instructions](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/cinema4d-vray-2025/README.md) to build the V-Ray for Cinema 4D conda package.

#### Installation instructions for workstations

1. Install the V-Ray for Cinema 4D plugin by [following instructions here](https://docs.chaos.com/display/VC4D/Installation).
  i. Choose "Workstation" install
2. [Optional] Verify that "V-Ray" works with Cinema 4D locally. You can test this using any of the sample scenes available [here](https://www.chaos.com/cloud/scenes?srsltid=AfmBOorJmV6Bugw1DTiIyfiA1gxANUxdp1tUaHOTdyZLJnBGJxLON8Xi#cinema-4d).
3. Submit to Deadline Cloud from Cinema 4D by using menu command **Extensions > AWS Deadline Cloud Submitter** with `cinema4d-vray` in the Conda Packages parameter.

#### Licensing instructions

V-Ray licensing is available by default on service managed fleets. To setup licensing on a customer managed fleet, follow the licensing instructions[here](https://documentation.chaos.com/space/VC4D/116855120/Installation#Licensing)

#### Version compatibility

We ran V-Ray for Cineam 4D v7.10.01 on Cinema 4D 2025. But more recent versions should still be compatible with latest versions of Cinema 4D, etc. For more information on compatibility refer to the [V-Ray System Requirements](https://documentation.chaos.com/space/VC4D/116855102/System+Requirements).

### INSYDIUM X-Particles

Follow [these instructions](https://github.com/aws-deadline/deadline-cloud-samples/blob/mainline/conda_recipes/cinema4d-insydium-2025/README.md)
to build the INSYDIUM conda package which includes X-Particles.

#### Installation instructions for workstations

1. Install by following [instructions here](https://insydium.ltd/help/?q=1608)
2. [Optional] Verify that "INSYDIUM" works with Cinema 4D locally. You can test this using any of the sample scenes available [here](https://insydium.ltd/support-home/content-repository/).
3. Submit to Deadline Cloud from Cinema 4D by using menu command **Extensions > AWS Deadline Cloud Submitter** with `cinema4d-insydium` in the Conda Packages parameter.

#### Licensing instructions

Licensing is built into your Insydium plugin by default. For more information, see [here](https://insydium.ltd/help/?q=1608)

#### Version compatibility

We ran Insydium Fused v2024.4.1 on Cinema 4D 2025. But more recent versions should still be compatible with latest versions of Cinema 4D, etc. For more information on compatibility refer to the [Insyduim Compatability Documentation](https://insydium.ltd/help/?q=2025).

### Kit-Bash Cargo

[Cargo](https://kit-bash.myshopify.com/pages/cargo) works without requiring
extra fleet or submitter confuration. Use **File > Save Project with Assets** to
save your scene before submitting.


## License

This project is licensed under the Apache-2.0 License.
