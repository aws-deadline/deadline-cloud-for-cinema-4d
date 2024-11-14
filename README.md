# AWS Deadline Cloud for Cinema 4D

[![pypi](https://img.shields.io/pypi/v/deadline-cloud-for-cinema-4d.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-cinema-4d)
[![python](https://img.shields.io/pypi/pyversions/deadline-cloud-for-cinema-4d.svg?style=flat)](https://pypi.python.org/pypi/deadline-cloud-for-cinema-4d)
[![license](https://img.shields.io/pypi/l/deadline-cloud-for-cinema-4d.svg?style=flat)](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/mainline/LICENSE)

### Disclaimer
---
This GitHub repository is an example integration with AWS Deadline Cloud that is intended to only be used for testing and is subject to change. This code is an alpha release. It is not a commercial release and may contain bugs, errors, defects, or harmful components. Accordingly, the code in this repository is provided as-is. Use within a production environment is at your own risk!

Our focus is to explore a variety of software applications to ensure we have good coverage across common workflows. We prioritized making this example available earlier to users rather than being feature complete.

This example has been used by at least one internal or external development team to create a series of jobs that successfully rendered. However, your mileage may vary. If you have questions or issues with this example, please start a discussion or cut an issue.
---

AWS Deadline Cloud for Cinema 4D is a python package that allows users to create [AWS Deadline Cloud][deadline-cloud] jobs from within Cinema 4D. It provides both the implementation of a Cinema 4D extension for your workstation that helps you offload the computation for your rendering workloads
to [AWS Deadline Cloud][deadline-cloud] to free up your workstation's compute for other tasks, and the implementation of a command-line
adaptor application based on the [Open Job Description (OpenJD) Adaptor Runtime][openjd-adaptor-runtime] that improves AWS Deadline Cloud's
ability to run Cinema 4D efficiently on your render farm.


[deadline-cloud]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/what-is-deadline-cloud.html
[deadline-cloud-client]: https://github.com/aws-deadline/deadline-cloud
[openjd]: https://github.com/OpenJobDescription/openjd-specifications/wiki
[openjd-adaptor-runtime]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
[openjd-adaptor-runtime-lifecycle]: https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python/blob/release/README.md#adaptor-lifecycle
[service-managed-fleets]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html
[default-queue-environment]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/create-queue-environment.html#conda-queue-environment
[service-managed-fleets]: https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html

## Compatibility

This library requires:

1. Cinema 4D 2024 - 2025
1. Python 3.9 or higher; but Python 3.11 is recommended as this is the version Cinema 4D uses natively.
1. Windows is recommended; We have some information below on how to setup the submitter on Mac and adaptors on Linux but it is experimental. 

## Versioning

This package's version follows [Semantic Versioning 2.0](https://semver.org/), but is still considered to be in its 
initial development, thus backwards incompatible versions are denoted by minor version bumps. To help illustrate how
versions will increment during this initial development stage, they are described below:

1. The MAJOR version is currently 0, indicating initial development. 
2. The MINOR version is currently incremented when backwards incompatible changes are introduced to the public API. 
3. The PATCH version is currently incremented when bug fixes or backwards compatible changes are introduced to the public API. 

## Getting Started

This Cinema 4D integration for AWS Deadline Cloud has two components that you will need to install:

1. The Cinema 4D submitter extension must be installed on the workstation that you will use to submit jobs; and
2. The Cinema 4D adaptor must be installed on all of your AWS Deadline Cloud worker hosts that will be running the Cinema 4D jobs that you submit.

Before submitting any large, complex, or otherwise compute-heavy Cinema 4D render jobs to your farm using the submitter and adaptor that you
set up, we strongly recommend that you construct a simple test scene that can be rendered quickly and submit renders of that scene to your farm to ensure that your setup is correctly functioning.


## Submitter

The Cinema 4D submitter extension creates a button in your Cinema 4D UI (under Extensions tab) that can be used to submit jobs to AWS Deadline Cloud. Clicking this button reveals a UI to create a job submission for AWS Deadline Cloud using the [AWS Deadline Cloud client library][deadline-cloud-client].
It automatically determines the files required based on the loaded scene, allows the user to specify render options, builds an
[Open Job Description template][openjd] that defines the workflow, and submits the job to the farm and queue of your chosing.

### To install the submitter extension:

#### Prerequisites

1. Install the required python modules:

```
pip install deadline-cloud-for-cinema-4d
pip install deadline[gui]
```

2. Set up the `C4DPYTHONPATH311` environment variable:
  - Windows: 
```
set C4DPYTHONPATH311="Path\to\site-packages"
```

  - Mac:
```
export C4DPYTHONPATH311="Path/to/site-packages"
```

#### Downloading the extension

The Cinema 4D extension can be downloaded from the git repo:

https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/mainline/deadline_cloud_extension/DeadlineCloud.pyp


#### Set up Cinema 4D to access DeadlingCloud extension: 

There are 2 ways to setup Cinema 4D to access this extension:

1. Plugin directory method:
    1. Create a new folder "plugins" within the Cinema 4D installation directory. 
    2. Place the `DeadlineCloud.pyp` within this "plugins" directory. 

2. Environment variable method:
    1. Add the `g_additionalModulePath` environment variable to point to the location where `DeadlineCloud.pyp` exists, so that Cinema 4D can load the plugin.

Windows:
```
set g_additionalModulePath="Path\to\DeadlineCloud.pyp"
```

Linux or Mac:
```
export g_additionalModulePath="Path/to/DeadlineCloud.pyp"
```

#### Using the extension

Windows:
- If the above environment variables are set as user / system variables, then just start Cinema 4D from the start menu. 

Mac:
- Set the above environment variables in a shell. 
- Navigate to the location where the Cinema 4D application is present.
Normally it is in `/Applications/Maxon Cinema 4D 2025/Cinema 4D.app/Contents/MacOS`
- Run `./Cinema\ 4D`

If you load a scene, click on **Extensions > Deadline Cloud Submitter** to view the submitter.

### Additional Python Libraries

Some specific versions of Cinema 4D ( e.g. `Cinema 4D 2024.1.0`) have been found to be missing some libraries key to Deadline requirements ; in later versions such as `2024.4.0` this has been resolved. 

A missing library error will manifest in errors that can be visible from the **Python** section of the **Extensions > Console** UI. These typically look like:

```
PySide6/__init__.py: Unable to import Shiboken from  ...
```

To remedy these errors, you can switch to a later version of Cinema 4D which resolves the missing libraries, or you can manually add them specifically to the Cinema 4D python module, e.g in Windows it will be something like:

```
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m ensurepip   
"C:\Program Files\Maxon Cinema 4D 2024\resource\modules\python\libs\win64\python.exe"-m pip install MISSING_MODULE
``` 

## Adaptor

Jobs created by this submitter require this adaptor be installed on your worker hosts, and that both the installed adaptor
and the Cinema 4D executable be available on the PATH of the user that will be running your jobs.

Or you can set the `CINEMA4D_ADAPTOR_COMMANDLINE_EXE` to point to the Cinema 4D executable. 

The adaptor application is a command-line Python-based application that enhances the functionality of Cinema 4D for running within a render farm like Deadline Cloud. Its primary purpose for existing is to add a "sticky rendering" functionality where a single process instance of Cinema 4D is able to load the scene file and then dynamically be instructed to perform desired renders without needing to close and re-launch Cinema 4D between them. It also has additional benefits such as support for path mapping, and reporting the progress of your render to Deadline Cloud. The alternative to "sticky rendering" is that Cinema 4D would need to be run separately for each render that is done, and close afterwards.
Some scenes can take 10's of minutes just to load for rendering, so being able to keep the application open and loaded between
renders can be a significant time-saving optimization; particularly when the render itself is quick.

If you are using the [default Queue Environment][default-queue-environment], or an equivalent, to run your jobs, then the adaptor will be automatically made available to your job. Otherwise, you will need to install the adaptor.

The adaptor can be installed by the standard python packaging mechanisms:
```sh
$ pip install deadline-cloud-for-cinema-4d
```

After installation it can then be used as a command line tool:
```sh
$ cinema4d-openjd --help
```

For more information on the commands the OpenJD adaptor runtime provides, see [here][openjd-adaptor-runtime-lifecycle].

### Cinema 4D software availability in AWS Deadline Cloud Service Managed Fleets. 
You will need to ensure the desired Cinema 4D version is available on the worker host when using AWS Deadline Cloud's [Service Managed Fleets][service-managed-fleets] to run jobs. These hosts do not have pre-installed rendering applications.

Cinema 4D packages are not available in the "deadline-cloud" conda channel. You must build them yourself in DeadlineCloud. We recommend using the conda recipes in our samples Github repository. Two essential conda packages for rendering on Deadline Cloud Service Managed Fleets are [`cinema4d-2025`](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-2025) and [`cinema4d-openjd`](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-openjd).

For instructions on building conda recipes on Deadline Cloud, see this [article](https://aws.amazon.com/blogs/media/create-a-conda-package-and-channel-for-aws-deadline-cloud/). 
Though it refers to Blender, the process applies to Cinema 4D recipes as well.

For licensing Cinema 4D workers, follow the guidelines in this [article](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/byol.html).

## Viewing the Job Bundle that will be submitted

To submit a job, the submitter first generates a [Job Bundle][job-bundle], and then uses functionality from the
[Deadline][deadline-cloud-client] package to submit the Job Bundle to your render farm to run. If you would like to see
the job that will be submitted to your farm, then you can use the "Export Bundle" button in the submitter to export the
Job Bundle to a location of your choice. If you want to submit the job from the export, rather than through the
submitter plug-in then you can use the [Deadline Cloud application][deadline-cloud-client] to submit that bundle to your farm.

[job-bundle]: https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html

## Security

We take all security reports seriously. When we receive such reports, we will 
investigate and subsequently address any potential vulnerabilities as quickly 
as possible. If you discover a potential security issue in this project, please 
notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/)
or directly via email to [AWS Security](aws-security@amazon.com). Please do not 
create a public GitHub issue in this project.

## Telemetry

See [telemetry](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/release/docs/telemetry.md) for more information.

## License

This project is licensed under the Apache-2.0 License.
