# Development documentation

This documentation provides guidance on developer workflows for working with the code in this repository.

> **Tip:** This repo includes three AI skills in `skills/` (following the [Agent Skills standard](https://agentskills.io/)) to accelerate development with AI coding assistants:
> - **c4d-dev-setup** — Automates dev environment setup. Ask: *"use c4d-dev-setup to set up this computer"*
> - **c4d-dev** — Day-to-day development: build, test, lint, debug. Ask: *"how do I run integration tests?"*
> - **c4d-design** — Structured design docs for new features. Ask: *"help me design a new feature"*
>
> See [AGENTS.md](AGENTS.md) at the repo root for general agent guidance that applies across all AI tools.

Table of Contents:

* [Development Environment Setup](#development-environment-setup)
* [Software Architecture](#software-architecture)
* [The Development Loop](#the-development-loop)
   * [Submitter Development Workflow](#submitter-development-workflow)
      * [Pre-requisites](#running-the-plug-in)
      * [Making Code Changes](#making-submitter-code-changes)
      * [Running Tests](#running-submitter-tests)
   * [Adaptor Development Workflow](#adaptor-development-workflow)
      * [Running the Adaptor Locally](#running-the-adaptor-locally)
      * [Running the Adaptor on a Farm](#running-the-adaptor-on-a-farm)
      * [Testing the Adaptor](#testing-the-adaptor)
   * [Running the integration tests](#integration-tests)

## Development Environment Setup

To develop the Python code in this repository you will need:

1. Python 3.10 or higher. We recommend [mise](https://github.com/jdx/mise) if you would like to run more than one version
   of Python on the same system. When running unit tests against all supported Python versions, for instance.
2. The [hatch](https://github.com/pypa/hatch) package installed (`pip install --upgrade hatch`) into your Python environment.
3. An install of a supported version of Cinema 4D.

The xa11y integration suite uses an offline mock Deadline backend, so it does
not require an AWS account or farm. A real AWS account, farm, queue, and fleet
are only required when testing jobs on Deadline Cloud.

Submitter and xa11y development are supported on Windows and macOS. Adaptor
development is supported on Windows and Linux.

## Software Architecture

If you are not already familiar with the architecture of the Cinema 4D submitter extension and adaptor application in this repository
then we suggest going over the [software architecture](docs/software_arch.md) for an overview of the components and how they function.

## The Development Loop

We have configured [hatch](https://github.com/pypa/hatch) commands to support a standard development loop. You can run the following
from any directory of this repository:

* `hatch build` - To build the installable Python wheel and sdist packages into the `dist/` directory.
* `hatch run test` - To run the PyTest unit tests found in the `test/unit` directory. See [Testing](#testing).
* `hatch run all:test` - To run the PyTest unit tests against all available supported versions of Python.
* `hatch run integ:test` - To run the xa11y integration tests against your current build.
* `hatch run lint` - To check that the package's formatting adheres to our standards.
* `hatch run fmt` - To automatically reformat all code to adhere to our formatting standards.
* `hatch shell` - Enter a shell environment that will have Python set up to import your development version of this package.
* `hatch env prune` - Delete all of your isolated workspace [environments](https://hatch.pypa.io/1.12/environment/)
   for this package.
* `hatch run installer:build-installer --local-dev --platform <PLATFORM> [--install-builder-path <LOCATION> --output-dir <DIR>]` - To build a local submitter installer.
    * platform can be `windows` or `macos`
* `hatch run test-installer` - To run tests against your locally built installer. 

Note: Hatch uses [environments](https://hatch.pypa.io/1.12/environment/) to isolate the Python development workspace
for this package from your system or virtual environment Python. If your build/test run is not making sense, then
sometimes pruning (`hatch env prune`) all of these environments for the package can fix the issue.

### Submitter Development Workflow

The submitter plug-in extension generates job bundles to submit to AWS Deadline Cloud. Developing a change
to the submitter involves iteratively changing the plug-in extension code, then running the plug-in within Cinema 4D to generate or submit a job bundle, inspecting the generated job bundle to ensure that it is as you expect,
and ultimately running that job to ensure that it works as desired.

#### Pre-requisites

Before making changes to the existing Cinema 4D extension, verify your current setup is correct. Follow the [instructions here](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d?tab=readme-ov-file#submitter) to set up properly.

#### Making Submitter Code Changes

Whenever you modify code for the plug-in extension or its supporting Python libraries, you will need to make similar changes to your Cinema 4D workstation and restart Cinema 4D for changes to take effect.

#### Running Submitter Tests

The tests for the plug-in have two forms:

1. Unit tests - Small tests that are narrowly focused on ensuring that function-level behavior of the
   implementation behaves as it is expected to. These can always be run locally on your workstation without
   requiring an AWS account.
2. Integration tests - In-application tests that verify that job submissions generate expected job bundles.

##### Unit Tests

Unit tests are located under the `test/unit/deadline_submitter_for_cinema4d/` directory of this repository. If you are adding
or modifying functionality, then you will almost always want to be writing one or more unit tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the unit tests, simply use hatch:

```bash
hatch run test
```

### Adaptor Development Workflow

The Cinema 4D adaptor is a command-line application (named `cinema4d-openjd`) that interfaces with the Cinema 4D application.

When developing a change to the Cinema 4D adaptor we recommend primarily running the adaptor locally on your workstation,
and running and adding to the unit tests until you are comfortable that your change looks like it is working as you expect.
Testing locally like this will allow you to iterate faster on your change than the alternative of testing by
submitting jobs to Deadline Cloud to run using your modified adaptor. Then, test it out on a real render farm only once
you think that your change is functioning as you'd like.

#### Running the Adaptor Locally

To run the adaptor you will first need to create two files:

1. An `init-data.yaml` (or `init-data.json`) file that contains the information passed to the adaptor
   during its initialization phase. The schema for this file can be found at
   `src/deadline/cinema4d_adaptor/Cinema4DAdaptor/schemas/init_data.schema.json`. 
2. A `run-data.yaml` (or `run-data.json`) file that contains the information passed to the adaptor
   to do a single Task run. The schema for this file can be found at
   `src/deadline/cinema4d_adaptor/Cinema4DAdaptor/schemas/run_data.schema.json`.

To run the adaptor once you have created an `init-data.yaml` and `run-data.yaml` file to test with:

1. Ensure that Cinema 4D commandline executable can be run directly in your terminal by putting its location in your PATH environment variable.
3. Run the `cinema4d-openjd` commmand-line with arguments that exercise your code change.

The adaptor has two modes of operation:

1. Running directly via the `cinema4d-openjd run` subcommand; or
2. Running as a background daemon via subcommands of the `cinema4d-openjd daemon` subcommand.

We recommend primarily developing using the `cinema4d-openjd run` subcommand as it is simpler to operate
for rapid development iterations, but that you should also ensure that your change works with the background
daemon mode with multiple `run` commands before calling your change complete.

The basic command to run the `cinema4d-openjd` run command will look like:

```bash
cinema4d-openjd run \
  --init-data file://<absolute-path-to-init-data.yaml> \
  --run-data file://<absolute-path-to-run-data.yaml>
```

The equivalent run with the `cinema4d-openjd daemon` subcommand looks like:

```bash
# The daemon start command requires that the connection-info file not already exist.
test -f connection-info.json || rm connection-info.json

# This starts up a background process running the adaptor, and runs the `on_init` and `on_start`
# methods of the adaptor.
cinema4d-openjd daemon start \
  --init-data file://<absolute-path-to-init-data.yaml> \
  --connection-file file://connection-info.json

# This connects to the already running adaptor, via the information in the connection-info.json file,
# and runs the adaptor's `on_run` method.
# When testing, we suggest doing multiple "daemon run" commands with different inputs before
# running "daemon stop". This will help identify problems caused by data carrying over from a previous
# run.
cinema4d-openjd daemon run \
  --run-data file://<absolute-path-to-run-data.yaml> \
  --connection-file file://connection-info.json

# This connects to the already running adaptor to instruct it to shutdown the Cinema 4D application
# and then exit.
cinema4d-openjd daemon stop \
  --connection-file file://connection-info.json
```

#### Running the Adaptor on a Farm

If you have made modifications to the adaptor and wish to test your modifications on a live Deadline Cloud Farm
with real jobs, then we recommend using a [Service Managed Fleet](https://docs.aws.amazon.com/deadline-cloud/latest/userguide/smf-manage.html)
for your testing. We recommend performing this style of test if you have made any modifications that might interact with Deadline Cloud's
job attachments feature, or that could interact with path mapping in any way. 

You'll need to perform the following steps to substitute your build of the adaptor for the one in the service.

1. Follow the [instructions](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes#create-a-patch-for-a-recipe) to make a patch for your "cinema4d-openjd" recipe. 
2. Build a new "cinema4d-openjd" conda package using this patch. For instructions on building conda recipes on Deadline Cloud, follow this [article](https://aws.amazon.com/blogs/media/create-a-conda-package-and-channel-for-aws-deadline-cloud/). 
This should have automatically added the latest patch onto the S3 bucket for the SMF workers to pull from. 
3. Submit jobs and check if the renders work as expected. 

##### Unit tests

Unit tests are located under the `test/unit/deadline_adaptor_for_cinema4d/` directory of this repository. If you are adding
or modifying functionality, then you will almost always want to be writing one or more unit tests to demonstrate that your
logic behaves as expected and that future changes do not accidentally break your change.

To run the unit tests, simply use hatch:

```bash
hatch run test
```



### Integration Tests

The xa11y suite launches the real Cinema 4D submitter, drives its UI against an
offline mock Deadline backend, validates the exported job bundle, and renders
the bundle on Windows. Cinema 4D and renderer licensing must be configured.

#### Test Structure

```text
test/integ/
├── test_cinema4d.py               # Orchestrates scene build, UI export, and validation
├── conftest.py                    # Cinema 4D and mock Deadline fixtures
├── submitter_ui.py                # xa11y controls for the submitter dialog
├── utils.py                       # Scene, bundle, and render helpers
├── fixtures/auto_open_submitter/  # Test-only plugin that opens the submitter
└── test_cases/<name>/
    ├── input/
    │   ├── scene.py               # Builds the Cinema 4D scene
    │   └── configure.py           # Optional xa11y dialog configuration
    ├── expected/
    │   ├── job_bundle/            # Golden bundle files
    │   └── renders/               # Golden render images
    └── actual/                    # Gitignored runtime output
```

Run the suite with:

```bash
hatch run integ:test
```

See [`test/AGENTS.md`](test/AGENTS.md) for platform support, setup, focused runs,
test-case authoring, selector discovery, and golden-bundle capture.
