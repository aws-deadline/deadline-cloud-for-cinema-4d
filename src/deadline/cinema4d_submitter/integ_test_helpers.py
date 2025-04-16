# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# This file is used only for integration tests.
from .cinema4d_render_submitter import (
    initialize_render_settings,
    setup_attachments,
    get_conda_packages,
    get_takes_from_doc,
    setup_auto_detected_attachments,
    create_job_bundle,
)

import c4d


def sample_queue_params() -> list:
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


def internal_create_job_bundle(job_bundle_dir: str):
    """
    This function mimics the call that Cinema 4D submitter does to generate the job bundle.
    """

    render_settings = initialize_render_settings()

    doc = c4d.documents.GetActiveDocument()

    takes = get_takes_from_doc(doc)

    auto_detected_attachments = setup_auto_detected_attachments(takes["take_data_list"])
    attachments = setup_attachments(render_settings)

    # auto_detected_attachments is equal to asset references in create job bundle callback.
    create_job_bundle(
        settings=render_settings,
        takes=takes,
        job_bundle_dir=job_bundle_dir,
        asset_references=auto_detected_attachments,
        queue_parameters=sample_queue_params(),
        attachments=attachments,
    )
