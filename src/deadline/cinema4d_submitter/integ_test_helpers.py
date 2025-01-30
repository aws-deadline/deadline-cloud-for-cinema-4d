from cinema4d_render_submitter import (
    initialize_render_settings,
    setup_attachments,
    get_conda_packages,
    process_takes,
    setup_auto_detected_attachments,
    process_job_bundle,
)

import c4d


def dummy_queue_params() -> list:
    """
    This is the default queue parameters that we expect during callbacks when we submit a job.
    """
    return [
        {
            "default": "cinema4d=2024 cinema4d-openjd",
            "description": 'This is a space-separated list of Conda package match specifications to install for the job. E.g. "blender=3.6" for a job that renders frames in Blender 3.6.\nSee https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/pkg-specs.html#package-match-specifications\n',
            "name": "CondaPackages",
            "type": "STRING",
            "userInterface": {
                "control": "LINE_EDIT",
                "groupLabel": "Queue Environment: Conda",
                "label": "Conda Packages",
            },
            "value": get_conda_packages(),
        },
        {
            "default": "deadline-cloud",
            "description": 'This is a space-separated list of Conda channels from which to install packages. Deadline Cloud SMF packages are installed from the "deadline-cloud" channel that is configured by Deadline Cloud.\nAdd "conda-forge" to get packages from the https://conda-forge.org/ community, and "defaults" to get packages from Anaconda Inc (make sure your usage complies with https://www.anaconda.com/terms-of-use).\n',
            "name": "CondaChannels",
            "type": "STRING",
            "userInterface": {
                "control": "LINE_EDIT",
                "groupLabel": "Queue Environment: Conda",
                "label": "Conda Channels",
            },
            "value": "deadline-cloud",
        },
        {
            "name": "deadline:targetTaskRunStatus",
            "type": "STRING",
            "userInterface": {"control": "DROPDOWN_LIST", "label": "Initial state"},
            "allowedValues": ["READY", "SUSPENDED"],
            "value": "READY",
        },
        {
            "name": "deadline:maxFailedTasksCount",
            "description": "Maximum number of Tasks that can fail before the Job will be marked as failed.",
            "type": "INT",
            "userInterface": {"control": "SPIN_BOX", "label": "Maximum failed tasks count"},
            "minValue": 0,
            "value": 20,
        },
        {
            "name": "deadline:maxRetriesPerTask",
            "description": "Maximum number of times that a task will retry before it's marked as failed.",
            "type": "INT",
            "userInterface": {"control": "SPIN_BOX", "label": "Maximum retries per task"},
            "minValue": 0,
            "value": 5,
        },
        {"name": "deadline:priority", "type": "INT", "value": 50},
    ]


def dummy_host_requirements() -> dict:
    """
    This is an example of host_requirements for a submission.
    """
    return {
        "attributes": [
            {"name": "attr.worker.os.family", "anyOf": ["windows"]},
        ]
    }


def internal_create_job_bundle(job_bundle_dir):
    render_settings = initialize_render_settings()

    doc = c4d.documents.GetActiveDocument()

    take_data_list, current_data_list, marked_data_list, main_data_list = process_takes(doc)

    auto_detected_attachments = setup_auto_detected_attachments(take_data_list)
    attachments = setup_attachments(render_settings)

    # auto_detected_attachments is equal to asset references in create job bundle callback.
    process_job_bundle(
        render_settings,
        take_data_list,
        current_data_list,
        marked_data_list,
        main_data_list,
        job_bundle_dir,
        auto_detected_attachments,
        dummy_queue_params(),
        attachments,
        dummy_host_requirements(),
    )
