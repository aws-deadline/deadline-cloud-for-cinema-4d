# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import c4d
import yaml  # type: ignore[import]
from qtpy import QtWidgets
from qtpy.QtCore import Qt  # type: ignore[attr-defined]

from deadline.client.exceptions import DeadlineOperationError
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    JobBundlePurpose,
    SubmitJobToDeadlineDialog,
)

from ._version import version_tuple as adaptor_version_tuple
from .assets import AssetIntrospector
from .data_classes import (
    RenderSubmitterUISettings,
)
from .scene import Animation, Scene
from .style import C4D_STYLE
from .takes import TakeSelection
from .ui.components.scene_settings_tab import SceneSettingsWidget

LOADED = False


@dataclass
class TakeData:
    name: str
    display_name: str
    renderer_name: str
    ui_group_label: str
    frames_parameter_name: Optional[str]
    frame_range: str
    output_directories: set[str]
    marked: bool


def show_submitter():

    if _prompt_save_current_document() is False:
        return

    try:
        app = QtWidgets.QApplication.instance()
        if not app:
            app = QtWidgets.QApplication([])
            app.setQuitOnLastWindowClosed(False)
            app.aboutToQuit.connect(app.deleteLater)
        app.setStyleSheet(C4D_STYLE)
        w = _show_submitter(None)
        w.setStyleSheet(C4D_STYLE)
        w.exec_()
    except Exception:
        print("Deadline UI launch failed")
        import traceback

        traceback.print_exc()


def _get_parameter_values(
    settings: RenderSubmitterUISettings,
    renderers: set[str],
    queue_parameters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parameter_values: list[dict[str, Any]] = []

    # Set the c4d scene file value
    parameter_values.append({"name": "Cinema4DFile", "value": Scene.name()})
    parameter_values.append({"name": "OutputPath", "value": settings.output_path})
    parameter_values.append({"name": "MultiPassPath", "value": settings.multi_pass_path})

    if settings.override_frame_range:
        frame_list = settings.frame_list
    else:
        frame_list = str(Animation.frame_list())
    parameter_values.append({"name": "Frames", "value": frame_list})

    # Check for any overlap between the job parameters we've defined and the
    # queue parameters. This is an error, as we weren't synchronizing the values
    # between the two different tabs where they came from.
    parameter_names = {param["name"] for param in parameter_values}
    queue_parameter_names = {param["name"] for param in queue_parameters}
    parameter_overlap = parameter_names.intersection(queue_parameter_names)
    if parameter_overlap:
        raise DeadlineOperationError(
            "The following queue parameters conflict with the Cinema4D job parameters:\n"
            + f"{', '.join(parameter_overlap)}"
        )

    # If we're overriding the adaptor with wheels, remove deadline_cloud_for_cinema4d from the CondaPackages
    if settings.include_adaptor_wheels:
        conda_param = {}
        # Find the CondaPackages parameter definition
        for param in queue_parameters:
            if param["name"] == "CondaPackages":
                conda_param = param
                break
        # Remove the deadline_cloud_for_cinema4d conda package
        if conda_param:
            conda_param["value"] = " ".join(
                pkg
                for pkg in conda_param["value"].split()
                if not pkg.startswith("deadline_cloud_for_cinema4d")
            )

    parameter_values.extend(
        {"name": param["name"], "value": param["value"]} for param in queue_parameters
    )

    return parameter_values


def _get_job_template(
    settings: RenderSubmitterUISettings,
    renderers: set[str],
    takes: list[TakeData],
) -> dict[str, Any]:
    if os.getenv("DEADLINE_COMMAND_TEMPLATE"):
        template = "default_cinema4d_job_template.yaml"
        adaptor = False
    else:
        template = "adaptor_cinema4d_job_template.yaml"
        adaptor = True
    with open(Path(__file__).parent / template) as fh:
        job_template = yaml.safe_load(fh)

    # Set the job's name
    job_template["name"] = settings.name
    # Set the job's description
    if settings.description:
        job_template["description"] = settings.description
    else:
        # remove description field since it can't be empty
        # ignore if description is missing from template
        job_template.pop("description", None)

    # If there are multiple frame ranges, split up the Frames parameter by take
    if takes[0].frames_parameter_name:
        # Extract the Frames parameter definition
        frame_param = [
            param for param in job_template["parameterDefinitions"] if param["name"] == "Frames"
        ][0]
        job_template["parameterDefinitions"] = [
            param for param in job_template["parameterDefinitions"] if param["name"] != "Frames"
        ]

        # Create take-specific Frames parameters
        for take_data in takes:
            take_frame_param = deepcopy(frame_param)
            take_frame_param["name"] = take_data.frames_parameter_name
            take_frame_param["userInterface"]["groupLabel"] = take_data.ui_group_label
            job_template["parameterDefinitions"].append(take_frame_param)

    # Replicate the default step, once per render take, and adjust its settings
    default_step = job_template["steps"][0]
    job_template["steps"] = []
    for take_data in takes:
        step = deepcopy(default_step)
        job_template["steps"].append(step)

        step["name"] = take_data.display_name

        parameter_space = step["parameterSpace"]
        # Update the 'Param.Frames' reference in the Frame task parameter
        if take_data.frames_parameter_name:
            parameter_space["taskParameterDefinitions"][0]["range"] = (
                "{{Param." + take_data.frames_parameter_name + "}}"
            )

        if adaptor is False:
            variables = step["stepEnvironments"][0]["variables"]
            variables["TAKE"] = take_data.name
        else:
            # Update the init data of the step
            init_data = step["stepEnvironments"][0]["script"]["embeddedFiles"][0]
            init_data["data"] = (
                "scene_file: '{{Param.Cinema4DFile}}'\ntake: '%s'\noutput_path: '{{Param.OutputPath}}'\nmulti_pass_path: '{{Param.MultiPassPath}}'"
                % take_data.name
            )

    # If Arnold is one of the renderers, add Arnold-specific parameters
    if "arnold" in renderers:
        job_template["parameterDefinitions"].append(
            {
                "name": "ArnoldErrorOnLicenseFailure",
                "type": "STRING",
                "userInterface": {
                    "control": "CHECK_BOX",
                    "label": "Error on License Failure",
                    "groupLabel": "Arnold Renderer Settings",
                },
                "description": "Whether to produce an error when there is an Arnold license failure.",
                "default": "false",
                "allowedValues": ["true", "false"],
            }
        )

    # If this developer option is enabled, merge the adaptor_override_environment
    if settings.include_adaptor_wheels:
        with open(Path(__file__).parent / "adaptor_override_environment.yaml") as f:
            override_environment = yaml.safe_load(f)

        # Read DEVELOPMENT.md for instructions to create the wheels directory.
        wheels_path = Path(__file__).parent.parent.parent.parent / "wheels"
        if not wheels_path.exists() and wheels_path.is_dir():
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory does not exist:\n"
                + str(wheels_path)
            )
        wheels_path_package_names = {
            path.split("-", 1)[0] for path in os.listdir(wheels_path) if path.endswith(".whl")
        }
        if wheels_path_package_names != {
            "openjd_adaptor_runtime",
            "deadline",
            "deadline_cloud_for_cinema4d",
        }:
            raise RuntimeError(
                "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels directory contains the wrong wheels:\n"
                + "Expected: openjd_adaptor_runtime, deadline, and deadline_cloud_for_cinema4d\n"
                + f"Actual: {wheels_path_package_names}"
            )

        override_adaptor_wheels_param = [
            param
            for param in override_environment["parameterDefinitions"]
            if param["name"] == "OverrideAdaptorWheels"
        ][0]
        override_adaptor_wheels_param["default"] = str(wheels_path)
        override_adaptor_name_param = [
            param
            for param in override_environment["parameterDefinitions"]
            if param["name"] == "OverrideAdaptorName"
        ][0]
        override_adaptor_name_param["default"] = "cinema4d-openjd"

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameterDefinitions"].extend(override_environment["parameterDefinitions"])

        # Add the environment to the end of the template's job environments
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(override_environment["environment"])

    return job_template


def _prompt_save_current_document():
    doc = c4d.documents.GetActiveDocument()
    if not doc.GetChanged():
        # Document has no unsaved changes
        return True
    file_path = doc.GetDocumentPath()
    file_name = doc.GetDocumentName()
    save_path = None
    if file_path:
        # Document save path exists
        save_path = os.path.join(file_path, file_name)
    if not c4d.gui.QuestionDialog("Save scene changes before submission?"):
        # User selected No
        if not save_path:
            c4d.gui.MessageDialog(
                "Submission canceled. File must be saved to disk before submission."
            )
            return False
        else:
            return True
    elif not save_path:
        # Prompt with Save As to set path for Untitled document
        save_path = c4d.storage.SaveDialog(c4d.FILESELECTTYPE_ANYTHING, "Save As", "c4d")
        # Handle user cancels document save
        if not save_path:
            c4d.gui.MessageDialog(
                "Submission canceled. File must be saved to disk before submission."
            )
            return False
        # Set document path and name
        doc_path = os.path.dirname(save_path)
        base_name = os.path.basename(save_path)
        doc.SetDocumentPath(doc_path)
        doc.SetDocumentName(base_name)
    # Save document to disk
    c4d.documents.SaveDocument(doc, save_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT)
    # Ensure document is active
    c4d.documents.InsertBaseDocument(doc)
    # Update UI
    c4d.EventAdd()
    return True


def _show_submitter(parent=None, f=Qt.WindowFlags()):

    render_settings = RenderSubmitterUISettings()

    # Set the setting defaults that come from the scene
    render_settings.name = Path(Scene.name()).name
    render_settings.frame_list = str(Animation.frame_list())
    default_path, multi_path = Scene.get_output_paths()
    render_settings.output_path = default_path
    render_settings.multi_pass_path = multi_path

    # Load the sticky settings
    render_settings.load_sticky_settings(Scene.name())

    doc = c4d.documents.GetActiveDocument()
    take_data = doc.GetTakeData()
    main_take = take_data.GetMainTake()
    current_take = take_data.GetCurrentTake()

    def get_child_takes(take):
        child_takes = take.GetChildren()
        all_takes = child_takes
        if child_takes:
            for child_take in child_takes:
                all_takes.extend(get_child_takes(child_take))
        return all_takes

    all_takes = [main_take] + get_child_takes(main_take)
    take_data_list = []
    current_data_list = []
    marked_data_list = []
    for take in all_takes:
        take_name = take.GetName()
        take_render_data = Scene.get_render_data(doc=doc, take=take)
        renderer_name = Scene.renderer(take_render_data)
        output_directories = Scene.get_output_directories(take=take)
        take_data = TakeData(
            name=take_name,
            display_name=take_name,
            renderer_name=renderer_name,
            ui_group_label=f"Take {take_name} Settings ({renderer_name} renderer)",
            frames_parameter_name=None,
            frame_range=str(Animation.frame_list(take_render_data)),
            output_directories=output_directories,
            marked=take.IsChecked(),
        )
        take_data_list.append(take_data)
        if current_take == take:
            current_data_list = [take_data]
        if take.IsChecked():
            marked_data_list.append(take_data)
    main_data_list = [take_data_list[0]]

    def on_create_job_bundle_callback(
        widget: SubmitJobToDeadlineDialog,
        job_bundle_dir: str,
        settings: RenderSubmitterUISettings,
        queue_parameters: list[dict[str, Any]],
        asset_references: AssetReferences,
        host_requirements: Optional[dict[str, Any]] = None,
        purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
    ) -> None:
        submit_takes = main_data_list
        job_bundle_path = Path(job_bundle_dir)
        if settings.take_selection == TakeSelection.MAIN:
            submit_takes = main_data_list
        if settings.take_selection == TakeSelection.ALL:
            submit_takes = take_data_list
        if settings.take_selection == TakeSelection.MARKED:
            submit_takes = marked_data_list
        if settings.take_selection == TakeSelection.CURRENT:
            submit_takes = current_data_list

        # Add overrides to asset references
        if settings.output_path:
            asset_references.output_directories.add(os.path.dirname(settings.output_path))
        if settings.multi_pass_path:
            asset_references.output_directories.add(os.path.dirname(settings.multi_pass_path))

        # # Check if there are multiple frame ranges across the takes
        first_frame_range = submit_takes[0].frame_range
        per_take_frames_parameters = not settings.override_frame_range and any(
            take.frame_range != first_frame_range for take in submit_takes
        )

        # If there are multiple frame ranges and we're not overriding the range,
        # then we create per-take Frames parameters.
        if per_take_frames_parameters:
            for take_data in submit_takes:
                take_data.frames_parameter_name = f"{take_data.display_name}Frames"

        renderers: set[str] = {take_data.renderer_name for take_data in submit_takes}
        job_template = _get_job_template(settings, renderers, submit_takes)
        parameter_values = _get_parameter_values(settings, renderers, queue_parameters)

        # If "HostRequirements" is provided, inject it into each of the "Step"
        if host_requirements:
            # for each step in the template, append the same host requirements.
            for step in job_template["steps"]:
                step["hostRequirements"] = host_requirements

        with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(job_template, f, indent=1)

        with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

        with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
            deadline_yaml_dump(asset_references.to_dict(), f, indent=1)

        # Save Sticky Settings
        attachments: AssetReferences = widget.job_attachments.attachments
        settings.input_filenames = sorted(attachments.input_filenames)
        settings.input_directories = sorted(attachments.input_directories)
        settings.input_filenames = sorted(attachments.input_filenames)

        settings.save_sticky_settings(Scene.name())

    auto_detected_attachments = AssetReferences()
    introspector = AssetIntrospector()
    auto_detected_attachments.input_filenames = set(
        os.path.normpath(path) for path in introspector.parse_scene_assets()
    )

    for take_data in take_data_list:
        auto_detected_attachments.output_directories.update(take_data.output_directories)
    attachments = AssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )

    c4d_major_version = str(c4d.GetC4DVersion())[:4]
    adaptor_version = ".".join(str(v) for v in adaptor_version_tuple[:2])
    conda_packages = f"cinema4d={c4d_major_version}.* cinema4d-openjd={adaptor_version}.*"

    submitter_dialog = SubmitJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_job_settings=render_settings,
        initial_shared_parameter_values={
            "CondaPackages": conda_packages,
        },
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_job_bundle_callback,
        parent=parent,
        f=f,
        show_host_requirements_tab=True,
    )

    return submitter_dialog
