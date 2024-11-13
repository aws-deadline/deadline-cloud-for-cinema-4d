# Software Architecture

This document provides an overview of the Cinema 4D submitter extension and adaptor that are in this repository.
The intent is to help you have a basic understanding of what the applications are doing to give you context to understand what you are looking at when diving through the code. This is not a comprehensive deep dive of the implementation.

## Cinema 4D Submitter extension

The Cinema 4D extension is contructed in two parts:
1. A very bare-bones extension [file](https://github.com/aws-deadline/deadline-cloud-for-cinema-4d/blob/mainline/deadline_cloud_extension/DeadlineCloud.pyp). 
2. The `deadline.cinema4d_submitter` Python package located in `/src/deadline/cinema4d_submitter` that provides all of the actual business logic for the plugin.

### `deadline.cinema4d_submitter`

Fundamentally, what this submitter is doing is creating a [Job Bundle](https://docs.aws.amazon.com/deadline-cloud/latest/developerguide/build-job-bundle.html)
and using the GUI creation code in the [`deadline` Python package](https://pypi.org/project/deadline/) to generate the UI that is displayed to the user. The important parts to know about in a job bundle are:

1. The job template file. The submitter code dynamically generates the template based on properties of the specific scene file that is loaded. For example, it may contain a Step for each layer of the scene to render.

Note: All job template files are currently derived from a standard static job template located at
   `src/deadline/cinema4d_submitter/adaptor_cinema4d_job_template.yaml`.
2. Asset references. These are the files that the job, when submitted, will require to be able to run. The submitter contains code that introspects the loaded scene to automatically discover these. The submitter extension's UI allows the end-user to modify this list of files.

The job submission itself is handled by functionality within the `deadline` package that is hooked up when the UI is created.

## Cinema 4D Adaptor Application

See the [README](../README.md#Adaptor) for background on what purpose the adaptor application serves.

The implementation of the adaptor for Cinema 4D has two parts:

1. The adaptor application itself whose code is located in `src/deadline/cinema4d_adaptor/Cinema4DAdaptor`. This is the implementation of the command-line application (named `Cinema 4D-openjd`) that is run by Jobs created by the Cinema 4D submitter.
2. A "Cinema4DClient" application located in `src/deadline/cinema4d_adaptor/Cinema4DClient`. This is an application that is run within Cinema 4D by the adaptor application when it launches Cinema 4D. The Cinema 4D Client remains running as long as the Cinema 4D process is running. It facilitates communication between the adaptor process and the running Cinema 4D process; communication to tell Cinema 4D to, say, load a scene file, or render frame 20 of the loaded scene.

The adaptor application is built using the [Open Job Description Adaptor Runtime](https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python) package. This package supplies the application entrypoint that defines and parses the command-line subcommands and options, as well as the business logic that drives the state machine of the adaptor itself. Please see the README for the runtime package for information on the lifecycle states of an adaptor, and the command line options that are available. 

Digging through the code for the adaptor, you will find that the `on_start()` method is where the Cinema 4D application is started.
The application is started with arguments that tell Cinema 4D to run the "Cinema 4D Client" application. This application is, essentially, a secure web server that is running over named pipes rather than network sockets. The adaptor sends the client commands (look for calls to `enqueue_action()` in the adaptor) to instruct Cinema 4D to do things, and then waits for the results of those actions to take effect. 

You can see the definitions of the available commands, and the actions that they take by inspecting `src/deadline/Cinema4DClient/cinema4d_client.py`. You'll notice that the commands that it directly defines are minimal, and that the set of commands that are available is updated when the adaptor sends it a command to set the renderer being used.

The final thing to be aware of is that the adaptor defines a number of stdout/stderr handlers. These are registered when launching the Cinema 4D process via the `LoggingSubprocess` class. Each handler defines a regex that is compared against the output stream of Cinema 4D itself, and code that is run when that regex is matched in Cinema 4D's output. This allows the adaptor to, say, translate the rendering progress status from Cinema 4D into a form that can be understood and reported to Deadline Cloud.