# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import logging
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import c4d
import yaml  # type: ignore[import]
from qtpy import QtWidgets
from qtpy.QtCore import Qt  # type: ignore[attr-defined]

from deadline.client.config import get_setting, str2bool
from deadline.client.dataclasses import SubmitterInfo
from deadline.client.exceptions import DeadlineOperationCanceled, DeadlineOperationError
from deadline.client.job_bundle._yaml import deadline_yaml_dump
from deadline.client.job_bundle.parameters import JobParameter
from deadline.client.job_bundle.submission import AssetReferences
from deadline.client.ui.dialogs.submit_job_to_deadline_dialog import (  # pylint: disable=import-error
    JobBundlePurpose,
    SubmitJobToDeadlineDialog,
)
from deadline.client.ui.pre_gui_hooks import (
    PreGuiHookContext,
    apply_pre_gui_output,
    qt_hook_confirmation,
    run_pre_gui_hooks,
)

from ._version import version_tuple as adaptor_version_tuple
from ._yaml_utils import _build_embedded_yaml
from .assets import AssetIntrospector
from .data_classes import (
    RenderSubmitterUISettings,
)
from .detailed_logging_utils import get_detailed_logging_environment
from .font_utils import FONTS_DIR, get_font_manager_environment, scene_has_fonts
from .platform_utils import is_macos, is_windows
from .scene import Animation, Scene, get_renderer_warning
from .setup_adaptor_wheels import _find_wheels
from .style import C4D_STYLE
from .takes import TakeSelection
from .template_timeout_patcher import add_timeouts_to_job_template
from .tile_utils import build_assembly_step, build_tile_task_parameters
from .ui.components import SceneSettingsWidget, SubmissionWarningDialog
from .update_utils import check_and_show_update_dialog
from .warning_collector import warning_collector
from .warning_logging_handler import WarningCollectorHandler

logger = logging.getLogger(__name__)
if not any(isinstance(h, WarningCollectorHandler) for h in logger.handlers):
    logger.addHandler(WarningCollectorHandler())

LOADED = False

_TAKE_TOKEN = "$take"


def _get_release_date() -> str | None:
    """Safely retrieve release date from _version.py.

    Returns:
        The release date string if available, None otherwise.
    """
    try:
        from ._version import release_date

        return release_date
    except (ImportError, AttributeError):
        return None


@dataclass
class TakeData:
    name: str
    display_name: str
    renderer_name: str
    ui_group_label: str
    frames_parameter_name: str | None
    frame_range: str
    output_directories: set[str]
    marked: bool


def show_submitter():
    if _prompt_save_current_document() is False:
        return

    try:
        app = QtWidgets.QApplication.instance()
        if not app:
            # Cinema 4D is not a Qt application, so there is no QApplication to reuse and we
            # construct one inside the host process. On macOS that makes Qt load its own nib
            # for the main menu and take possession of the native menu bar, replacing Cinema
            # 4D's menus for the rest of the session.
            #
            # AA_PluginApplication tells Qt it is being used to author a plugin, which is
            # exactly our situation, and suppresses that initialisation. Per the Qt
            # documentation it avoids "loading our nib for the main menu and not taking
            # possession of the native menu bar", and implies AA_DontUseNativeMenuBar. It
            # must be set before the QApplication is constructed; setting it afterwards has
            # no effect.
            #
            # Scoped only to macOS because Windows does not exhibit the problem, and the
            # attribute also disables native event filters -- a behaviour change not worth
            # taking on a platform that works.
            #
            # DCCs that are themselves Qt applications (Maya, Nuke) never reach this branch,
            # which is why the problem is specific to Cinema 4D.
            if is_macos():
                try:
                    QtWidgets.QApplication.setAttribute(
                        Qt.ApplicationAttribute.AA_PluginApplication, True
                    )
                except Exception:
                    # Losing the host's menu bar is a cosmetic problem; failing to open the
                    # submitter is not. Never let this be fatal.
                    logger.warning(
                        "Could not set AA_PluginApplication; Cinema 4D's menu bar may be "
                        "replaced for this session.",
                        exc_info=True,
                    )
            app = QtWidgets.QApplication([])
            app.setQuitOnLastWindowClosed(False)
            app.aboutToQuit.connect(app.deleteLater)

        if check_and_show_update_dialog():
            return

        # Get the scene file's directory path to create the temporary directory
        # in the same location as the original scene file. This ensures consistent
        # path resolution across platforms and avoids path mapping errors,
        # particularly on Linux systems.
        scene = c4d.documents.GetActiveDocument()
        scene_dir_path = scene.GetDocumentPath()

        # Create a temporary directory that will be automatically cleaned up after submission
        with tempfile.TemporaryDirectory(
            prefix="scene_with_assets_", dir=scene_dir_path
        ) as temp_dir:
            app.setStyleSheet(C4D_STYLE)  # type: ignore[attr-defined]
            if is_windows():
                w = _show_submitter(
                    temp_dir, None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint
                )
            else:
                w = _show_submitter(temp_dir, None)
            # _show_submitter returns None when the user declines the pre-GUI hook confirmation
            # prompt; treat that as a normal cancellation and skip showing the dialog.
            if w is None:
                return
            w.setStyleSheet(C4D_STYLE)
            w.exec_()
    except Exception:  # noqa: BLE001 - prevent UI failures from escaping into Cinema 4D
        print("Deadline UI launch failed")
        import traceback

        traceback.print_exc()


def _get_parameter_values(
    settings: RenderSubmitterUISettings,
    queue_parameters: list[JobParameter],
    per_take_frames_parameters: bool,
    submit_takes: list[TakeData],
) -> list[dict[str, Any]]:
    parameter_values: list[dict[str, Any]] = []

    # Set the c4d scene file value
    parameter_values.append({"name": "Cinema4DFile", "value": Scene.name()})
    parameter_values.append(
        {
            "name": "SubmitterIntegrationVersion",
            "value": ".".join(str(v) for v in adaptor_version_tuple),
        }
    )
    parameter_values.append({"name": "OutputPath", "value": settings.output_path})
    parameter_values.append({"name": "MultiPassPath", "value": settings.multi_pass_path})
    parameter_values.append(
        {"name": "ActivateErrorChecking", "value": settings.activate_error_checking}
    )
    parameter_values.append(
        {"name": "DetailedLogging", "value": "1" if settings.activate_detailed_logging else "0"}
    )
    parameter_values.append({"name": "UseCachedText", "value": settings.use_cached_text})
    # Set chunking parameter values
    parameter_values.append({"name": "ChunkSize", "value": settings.chunk_size})
    parameter_values.append(
        {"name": "TargetChunkDuration", "value": settings.target_chunk_duration}
    )

    if per_take_frames_parameters:
        for take_data in submit_takes:
            parameter_values.append(
                {
                    "name": take_data.frames_parameter_name,
                    "value": take_data.frame_range,
                }
            )
    else:
        if settings.override_frame_range:
            frame_list = settings.frame_list
        else:
            frame_list = submit_takes[0].frame_range
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
            "Rename the parameters on the queue to continue job submissions."
        )

    # If we're overriding the adaptor with wheels, remove deadline_cloud_for_cinema4d from the CondaPackages
    if settings.include_adaptor_wheels:
        conda_param: JobParameter | None = None
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


def _get_parameter_definition(
    parameter_definitions: list[dict[str, Any]], name: str
) -> dict[str, Any]:
    parameter = next(
        (item for item in parameter_definitions if item["name"] == name),
        None,
    )
    if parameter is None:
        raise RuntimeError(f"Template is missing the '{name}' parameter definition")
    return parameter


def _get_adaptor_override_environment(wheels_path: Path) -> dict[str, Any]:
    if not wheels_path.is_dir():
        raise RuntimeError(
            "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels "
            f"directory does not exist:\n{wheels_path}"
        )

    try:
        _find_wheels(wheels_path)
    except RuntimeError as exc:
        raise RuntimeError(
            "The Developer Option 'Include Adaptor Wheels' is enabled, but the wheels "
            f"directory contains the wrong wheels:\n{exc}"
        ) from exc

    with open(Path(__file__).parent / "adaptor_override_environment.yaml") as file:
        override_environment = yaml.safe_load(file)

    override_adaptor_wheels_param = _get_parameter_definition(
        override_environment["parameterDefinitions"],
        "OverrideAdaptorWheels",
    )
    override_adaptor_wheels_param["default"] = str(wheels_path)
    override_adaptor_name_param = _get_parameter_definition(
        override_environment["parameterDefinitions"],
        "OverrideAdaptorName",
    )
    override_adaptor_name_param["default"] = "cinema4d-openjd"

    setup_script_path = Path(__file__).parent / "setup_adaptor_wheels.py"
    setup_script = setup_script_path.read_text(encoding="utf8")
    setup_file = next(
        (
            embedded_file
            for embedded_file in override_environment["environment"]["script"]["embeddedFiles"]
            if embedded_file["name"] == "SetupAdaptor"
        ),
        None,
    )
    if setup_file is None:
        raise RuntimeError(
            "Adaptor override environment is missing the 'SetupAdaptor' embedded file"
        )
    setup_file["data"] = setup_script

    return override_environment


def _get_job_template(
    settings: RenderSubmitterUISettings,
    renderers: set[str],
    takes: list[TakeData],
    has_take_token: bool = False,
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
        frame_param = _get_parameter_definition(
            job_template["parameterDefinitions"],
            "Frames",
        )
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

        # Add tile parameters when tile rendering is enabled
        if settings.enable_tile_rendering:
            tile_params, combination = build_tile_task_parameters(
                settings.tiles_columns, settings.tiles_rows
            )
            parameter_space["taskParameterDefinitions"].extend(tile_params)
            parameter_space["combination"] = combination

        if adaptor is False:
            variables = step["stepEnvironments"][0]["variables"]
            variables["TAKE"] = take_data.name
        else:
            # Resolve output paths: use $take-substituted paths or parameter references
            output_path, multi_pass_path = _resolve_take_paths(
                settings, take_data.name, has_take_token
            )

            init_data = step["stepEnvironments"][0]["script"]["embeddedFiles"][0]
            init_data["data"] = _build_embedded_yaml(
                {
                    "scene_file": "{{Param.Cinema4DFile}}",
                    "take": take_data.name,
                    "output_path": output_path,
                    "multi_pass_path": multi_pass_path,
                    "activate_error_checking": "{{Param.ActivateErrorChecking}}",
                    "use_cached_text": "{{Param.UseCachedText}}",
                },
                unquoted_keys={"scene_file", "output_path", "multi_pass_path"},
            )

            # Update run-data to include tile region references when tile rendering is enabled
            if settings.enable_tile_rendering:
                run_data = step["script"]["embeddedFiles"][0]
                run_data["data"] = _build_embedded_yaml(
                    {
                        "frame": "{{Task.Param.Frame}}",
                        "tile_action": "render",
                        "current_tile_column": "{{Task.Param.TileCol}}",
                        "current_tile_row": "{{Task.Param.TileRow}}",
                        "total_tiles_column": settings.tiles_columns,
                        "total_tiles_row": settings.tiles_rows,
                    }
                )

    # Add tile assembly steps (one per render step) when tile rendering is enabled
    if settings.enable_tile_rendering and adaptor:
        render_steps = list(job_template["steps"])
        for idx, render_step in enumerate(render_steps):
            take_name = takes[idx].name
            output_path, multi_pass_path = _resolve_take_paths(settings, take_name, has_take_token)
            assembly_step = build_assembly_step(render_step, settings, output_path, multi_pass_path)
            job_template["steps"].append(assembly_step)

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
        # Read DEVELOPMENT.md for instructions to create the wheels directory.
        wheels_path = Path(__file__).parent.parent.parent.parent / "wheels"
        override_environment = _get_adaptor_override_environment(wheels_path)

        # There are no parameter conflicts between these two templates, so this works
        job_template["parameterDefinitions"].extend(override_environment["parameterDefinitions"])

        # Add the environment to the end of the template's job environments
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(override_environment["environment"])

    # Add DetailedLogging job environment
    if adaptor:
        detailed_logging_environment = get_detailed_logging_environment()
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(detailed_logging_environment)

    # Conditionally add FontManager job environment if fonts are detected (Windows only)
    if adaptor and is_windows() and scene_has_fonts(Path(Scene.name()).parent):
        font_manager_environment = get_font_manager_environment(Scene.name())
        if "jobEnvironments" not in job_template:
            job_template["jobEnvironments"] = []
        job_template["jobEnvironments"].append(font_manager_environment)

    add_timeouts_to_job_template(job_template, settings.timeouts)

    return job_template


def _prompt_save_current_document():
    doc = c4d.documents.GetActiveDocument()
    if not doc.GetDocumentPath():
        c4d.gui.MessageDialog(
            "Please open an existing project or save the current scene to disk\n"
            "before launching the submitter."
        )
        return False

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


def initialize_render_settings() -> RenderSubmitterUISettings:
    """
    Initialize the render settings with defaults that come from the scene.
    """
    render_settings = RenderSubmitterUISettings()
    render_settings.name = Path(Scene.name()).name
    render_settings.frame_list = Animation.frame_list()
    default_path, multi_path = Scene.get_output_paths()
    render_settings.output_path = default_path
    render_settings.multi_pass_path = multi_path
    render_settings.load_sticky_settings(Scene.name())
    return render_settings


# Characters to strip from display names (replaced with underscore)
_STRIPPED_PATH_CHARS = re.compile(r"[|:()\* ]")


def _resolve_take_paths(
    settings: RenderSubmitterUISettings,
    take_name: str | None,
    has_take_token: bool,
) -> tuple[str, str]:
    """Resolve output_path and multi_pass_path, substituting $take if present.

    Returns literal empty strings ('') instead of {{Param}} references for
    empty paths, because unquoted {{Param}} substituted with "" produces
    bare YAML ``key:`` which parses as None instead of "".
    """
    if has_take_token and take_name is not None:
        take_name_for_path = _STRIPPED_PATH_CHARS.sub("_", take_name)
        return (
            settings.output_path.replace(_TAKE_TOKEN, take_name_for_path),
            settings.multi_pass_path.replace(_TAKE_TOKEN, take_name_for_path),
        )
    return (
        "{{Param.OutputPath}}" if settings.output_path else "",
        "{{Param.MultiPassPath}}" if settings.multi_pass_path else "",
    )


def get_takes_from_doc(doc: Any) -> dict[str, list[TakeData]]:
    """
    Extracts and organizes take data from the given Cinema 4D document.

    Recursively processes all takes in the document, including the main take and its children,
    collecting rendering information and organizing them into different categories.
    """
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
        display_name = take_name[:64]
        take_render_data = Scene.get_render_data(doc=doc, take=take)
        renderer_name = Scene.renderer(take_render_data)
        output_directories = Scene.get_output_directories(take=take)
        label_prefix = "Take "
        label_suffix = f" Settings ({renderer_name} renderer)"
        characters_from_take_in_label = 64 - len(label_prefix) - len(label_suffix)
        take_data = TakeData(
            name=take_name,
            display_name=display_name,
            renderer_name=renderer_name,
            ui_group_label=f"{label_prefix}{display_name[:characters_from_take_in_label]}{label_suffix}",
            frames_parameter_name=None,
            frame_range=Animation.frame_list(take_render_data),
            output_directories=output_directories,
            marked=take.IsChecked(),
        )
        take_data_list.append(take_data)
        if current_take == take:
            current_data_list = [take_data]
        if take.IsChecked():
            marked_data_list.append(take_data)
    return {
        "take_data_list": take_data_list,
        "current_data_list": current_data_list,
        "marked_data_list": marked_data_list,
        "main_data_list": [take_data_list[0]],
    }


def save_job_bundle_files(
    job_bundle_path: Path,
    job_template: dict,
    parameter_values: list[dict[str, Any]],
    asset_references: AssetReferences,
) -> None:
    """
    This function saves the generated template/parameter_values/asset_references
    into the job bundle path.
    All the files are saved with UTF-8 encoding.
    """
    with open(job_bundle_path / "template.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(job_template, f, indent=1)

    with open(job_bundle_path / "parameter_values.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump({"parameterValues": parameter_values}, f, indent=1)

    with open(job_bundle_path / "asset_references.yaml", "w", encoding="utf8") as f:
        deadline_yaml_dump(asset_references.to_dict(), f, indent=1)


def _restore_pre_gui_hook_sticky_settings(
    settings: RenderSubmitterUISettings,
    pre_gui_hook_sticky_reset: dict[str, tuple[Any, Any]] | None,
) -> dict[str, Any]:
    """Restore pre-hook baseline values for sticky fields a pre-GUI hook overwrote.

    ``pre_gui_hook_sticky_reset`` maps each sticky field a pre-GUI hook overwrote to
    ``(pre_hook_value, hook_value)``. For each, restore the pre-hook value unless the user changed
    the field in the dialog -- in that case the current value differs from what the hook applied,
    so we keep the user's value. Hook output therefore stays scoped to the session: it never
    persists as a stale default after the hook is disabled, nor feeds back as ``jobName`` on the
    next launch.

    Returns the ``{field_name: hook_value}`` it reset to baseline, so the caller can reapply the
    hook values after the sticky write and avoid leaving the live ``settings`` object mutated (see
    :func:`_pre_gui_hook_sticky_baseline`).
    """
    if not pre_gui_hook_sticky_reset:
        return {}
    restored: dict[str, Any] = {}
    for field_name, (baseline_value, hook_value) in pre_gui_hook_sticky_reset.items():
        if getattr(settings, field_name) == hook_value:
            setattr(settings, field_name, baseline_value)
            restored[field_name] = hook_value
    return restored


# deadline-cloud's shared-settings tab (SharedJobPropertiesWidget) writes these "deadline:*" job
# properties onto the matching sticky RenderSubmitterUISettings fields when it gathers settings on
# Export/Submit. A pre-GUI hook only ever puts them in the shared parameter values (not directly on
# the settings object), so a hook emitting e.g. deadline:priority would otherwise persist into the
# scene's sticky settings exactly as an unscoped name/description would. This maps each such shared
# key to its sticky field so both are scoped out of the sticky write together.
_HOOK_STICKY_SHARED_PARAM_FIELDS = {
    "deadline:priority": "priority",
    "deadline:targetTaskRunStatus": "initial_status",
    "deadline:maxFailedTasksCount": "max_failed_tasks_count",
    "deadline:maxRetriesPerTask": "max_retries_per_task",
    "deadline:maxWorkerCount": "max_worker_count",
}


def _compute_pre_gui_hook_sticky_reset(
    settings: RenderSubmitterUISettings,
    name_description_baseline: dict[str, Any],
    shared_before: dict[str, Any],
    shared_after: dict[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """Build the ``{sticky_field: (pre_hook_value, hook_value)}`` map of every sticky field a
    pre-GUI hook changed, so create_job_bundle can keep the hook's values out of the sticky write.

    Two routes a hook reaches a sticky field:

    * ``name`` / ``description`` are set directly on ``settings`` by ``apply_pre_gui_output`` —
      detected by diffing ``name_description_baseline`` (snapshotted before the hook) against the
      current value.
    * ``deadline:*`` job properties are routed into the shared parameter values instead; the shared
      settings tab later writes them onto the matching sticky field (see
      ``_HOOK_STICKY_SHARED_PARAM_FIELDS``). Each such key the hook added or changed
      (``shared_before`` -> ``shared_after``) is recorded against its field, with the hook's value
      so a later user edit in the dialog (current value != hook value) is still kept.

    The baseline for a shared-param field is the field's current value on ``settings``, which
    ``apply_pre_gui_output`` does not touch — so it is still the pre-hook (scene/sticky) value.
    """
    reset: dict[str, tuple[Any, Any]] = {}
    for attr, baseline in name_description_baseline.items():
        current = getattr(settings, attr)
        if current != baseline:
            reset[attr] = (baseline, current)
    for shared_key, field_name in _HOOK_STICKY_SHARED_PARAM_FIELDS.items():
        if shared_key in shared_after and shared_after[shared_key] != shared_before.get(shared_key):
            reset[field_name] = (getattr(settings, field_name), shared_after[shared_key])
    return reset


@contextmanager
def _pre_gui_hook_sticky_baseline(
    settings: RenderSubmitterUISettings,
    pre_gui_hook_sticky_reset: dict[str, tuple[Any, Any]] | None,
):
    """Scope the pre-GUI hook sticky-settings reset to the ``save_sticky_settings`` call only.

    Restores pre-hook baselines for the sticky write, then reapplies the hook values so the live
    ``settings`` object is unchanged on exit. ``on_create_job_bundle_callback`` runs once per
    Export/Submit against the dialog's *live* settings object (not a per-call copy), so permanently
    resetting ``name``/``description`` to baseline would make a second action in the same session
    build its job from the scene-derived value instead of the hook's -- two different job names for
    two identical clicks, with the dialog still showing the first. Keeping the reset scoped to the
    sticky write leaves the in-memory settings exactly as the user saw them, while the persisted
    sticky settings still exclude the hook output.
    """
    restored = _restore_pre_gui_hook_sticky_settings(settings, pre_gui_hook_sticky_reset)
    try:
        yield
    finally:
        for field_name, hook_value in restored.items():
            setattr(settings, field_name, hook_value)


def create_job_bundle(
    settings: RenderSubmitterUISettings,
    takes: dict[str, list[TakeData]],
    job_bundle_dir: str,
    asset_references: AssetReferences,
    queue_parameters: list[JobParameter],
    attachments: AssetReferences,
    temp_dir: str | None = None,
    host_requirements: dict | None = None,
    pre_gui_hook_sticky_reset: dict[str, tuple[Any, Any]] | None = None,
) -> dict[str, Any]:
    """
    Creates a job bundle and saves sticky settings for rendering.

    This function processes the render settings, takes, and asset references to create
    a job bundle for submission. It handles different take selection modes, manages
    frame ranges, and prepares job templates with the necessary parameters.
    """

    original_cinema4d_file = Scene.name()
    scene_output_path, scene_multi_pass_path = Scene.get_output_paths()

    if settings.export_job_bundle_to_temp and temp_dir:
        export_to_temp_folder(temp_dir, asset_references)

    job_bundle_path = Path(job_bundle_dir)
    submit_takes = get_submit_takes(settings, takes)

    # Check for $take token BEFORE replacing tokens
    output_path_before = (
        settings.output_path if settings.override_output_path else scene_output_path
    )
    multi_pass_before = (
        settings.multi_pass_path if settings.override_multi_pass_path else scene_multi_pass_path
    )
    has_take_token = _TAKE_TOKEN in (output_path_before or "") or _TAKE_TOKEN in (
        multi_pass_before or ""
    )

    # Add overrides to asset references and update the paths with C4D render path tokens.
    if settings.override_output_path:
        if settings.output_path:
            settings.output_path = Scene.replace_render_path_tokens(settings.output_path)
            asset_references.output_directories.add(os.path.dirname(settings.output_path))
    else:
        if scene_output_path:
            settings.output_path = Scene.replace_render_path_tokens(scene_output_path)
            asset_references.output_directories.add(os.path.dirname(scene_output_path))

    if settings.override_multi_pass_path:
        if settings.multi_pass_path:
            settings.multi_pass_path = Scene.replace_render_path_tokens(settings.multi_pass_path)
            asset_references.output_directories.add(os.path.dirname(settings.multi_pass_path))
    else:
        if scene_multi_pass_path:
            settings.multi_pass_path = Scene.replace_render_path_tokens(scene_multi_pass_path)
            asset_references.output_directories.add(os.path.dirname(scene_multi_pass_path))

    # # Check if there are multiple frame ranges across the takes
    first_frame_range = submit_takes[0].frame_range
    per_take_frames_parameters = not settings.override_frame_range and any(
        take.frame_range != first_frame_range for take in submit_takes
    )

    # Deduplicate take names, then generate per-take Frames parameters
    # if there are multiple frame ranges and we're not overriding the range.
    deduplicate_take_names(submit_takes)
    if per_take_frames_parameters:
        generate_take_parameter_names(submit_takes)

    renderers: set[str] = {take_data.renderer_name for take_data in submit_takes}
    job_template = _get_job_template(settings, renderers, submit_takes, has_take_token)
    parameter_values = _get_parameter_values(
        settings, queue_parameters, per_take_frames_parameters, submit_takes
    )

    # If "HostRequirements" is provided, inject it into each of the "Step"
    if host_requirements:
        # for each step in the template, append the same host requirements.
        for step in job_template["steps"]:
            step["hostRequirements"] = host_requirements

    save_job_bundle_files(job_bundle_path, job_template, parameter_values, asset_references)
    # Save Sticky Settings
    if settings.export_job_bundle_to_temp:
        # Close temporary document
        c4d.documents.KillDocument(c4d.documents.GetActiveDocument())

        # Restore the original Cinema4DFile to be the active document.
        doc = c4d.documents.LoadDocument(
            original_cinema4d_file, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
        )
        c4d.documents.InsertBaseDocument(doc)
        c4d.documents.SetActiveDocument(doc)

    settings.input_filenames = sorted(attachments.input_filenames)
    settings.input_directories = sorted(attachments.input_directories)

    # Keep pre-GUI hook output out of the persisted sticky settings (the job template above already
    # captured the effective name/description). Scope the reset to the sticky write only, so the
    # live settings object keeps the hook values for any later action in the same dialog session.
    with _pre_gui_hook_sticky_baseline(settings, pre_gui_hook_sticky_reset):
        settings.save_sticky_settings(Scene.name())

    return {
        "known_asset_paths": [
            os.path.abspath(directory) for directory in settings.input_directories
        ],
        "job_parameters": parameter_values,
    }


def _find_duplicate_take_names(submit_takes: list[TakeData]) -> set[str]:
    """Returns the set of take names that appear more than once."""
    name_counts: dict[str, int] = {}
    for take in submit_takes:
        name_counts[take.name] = name_counts.get(take.name, 0) + 1
    return {name for name, count in name_counts.items() if count > 1}


def deduplicate_take_names(submit_takes: list[TakeData]) -> None:
    """
    Checks for duplicate take names and makes them unique by appending
    _1, _2, etc. suffixes. Handles collisions with existing take names
    (e.g. 'take', 'take', 'take_1' won't produce two 'take_1' entries).
    """
    duplicated_names = _find_duplicate_take_names(submit_takes)
    if not duplicated_names:
        return

    _validate_duplicate_name_lengths(duplicated_names)

    all_names = {take.name for take in submit_takes}
    next_suffix: dict[str, int] = dict.fromkeys(duplicated_names, 1)

    for take in submit_takes:
        if take.name in next_suffix:
            new_name, next_start = _generate_unique_name(
                take.name, next_suffix[take.name], all_names
            )
            _apply_take_name(take, new_name)
            all_names.add(new_name)
            next_suffix[take.name] = next_start


def _validate_duplicate_name_lengths(duplicated_names: set[str]) -> None:
    """Raises RuntimeError if any duplicated take name is already at the 64-char limit."""
    for name in duplicated_names:
        if len(name) >= 64:
            raise RuntimeError(
                f"Multiple takes share the name '{name}', which is already 64 characters long. "
                "Please shorten or rename the duplicate takes so they can be uniquely identified."
            )


def _generate_unique_name(
    original_name: str, start_suffix: int, existing_names: set[str]
) -> tuple[str, int]:
    """Finds the next available suffixed name that doesn't collide with existing names.

    Returns the unique name and the next suffix to try for this original name.
    """
    suffix = start_suffix
    new_name = f"{original_name}_{suffix}"
    while new_name in existing_names:
        suffix += 1
        new_name = f"{original_name}_{suffix}"
    return new_name, suffix + 1


def _apply_take_name(take: TakeData, new_name: str) -> None:
    """Applies a new name to a take, truncating display_name to 64 characters."""
    take.name = new_name
    take.display_name = new_name[:64]


def warn_duplicate_take_names(submit_takes: list[TakeData]) -> None:
    """
    Checks for duplicate take names and adds a warning via warning_collector
    if any are found.
    """
    duplicated_names = _find_duplicate_take_names(submit_takes)
    if duplicated_names:
        renamed_list = ", ".join(f"'{name}'" for name in sorted(duplicated_names))
        warning_collector.add_warning(
            f"Duplicate take names were found: {renamed_list}. "
            "They have been automatically renamed with _1, _2, etc. suffixes to ensure uniqueness."
        )


def generate_take_parameter_names(submit_takes: list[TakeData]) -> None:
    """
    This function generates unique take frame range parameter names
    by combining each takes name with a unique suffix (if required)
    while still meeting the requirements (letters+numbers+underscores,
    max 64 chars, etc.) of a parameter name.

    The frame parameter names are saved to the input submit_takes.
    """

    # parameter names must start with a letter or underscore
    allowed_first_job_parameter_chars = re.compile("[a-zA-Z_]")
    # parameter names must only contain letters, numbers, or underscores
    removed_job_parameter_chars = re.compile("[^a-zA-Z0-9_]")

    parameter_names = set()

    for take_number in range(len(submit_takes)):
        take_data = submit_takes[take_number]
        take_name = take_data.name

        # determine the frame parameter name
        # remove all disallowed characters
        parameter_name = removed_job_parameter_chars.sub("", take_data.display_name)[
            : 64 - len("Frames")
        ]
        # ensure the first character is allowed or prefix with an _
        if not allowed_first_job_parameter_chars.match(parameter_name):
            parameter_name = f"_{parameter_name}"[: 64 - len("Frames")]
        # ensure all parameter names are unique
        if parameter_name in parameter_names:
            # example: NewTake_00001
            parameter_name = f"{parameter_name[: 64 - len('Frames') - 6]}_{take_number:05}"
            if parameter_name in parameter_names:
                raise RuntimeError(
                    f"Unable to generate unique parameter name for take '{take_name}', please change the take name."
                )
        parameter_names.add(parameter_name)
        # Append "Frames"
        # example: NewTake_00001Frames
        take_data.frames_parameter_name = f"{parameter_name}Frames"


def setup_auto_detected_attachments(take_data_list: list[TakeData]) -> AssetReferences:
    """
    Set up automatically detected attachments from the scene and takes.
    """
    auto_detected_attachments = AssetReferences()
    introspector = AssetIntrospector()

    # Get scene assets
    auto_detected_attachments.input_filenames = {
        os.path.normpath(path) for path in introspector.parse_scene_assets()
    }

    # Add output directories from takes
    for take_data in take_data_list:
        auto_detected_attachments.output_directories.update(take_data.output_directories)

    return auto_detected_attachments


def setup_attachments(render_settings: RenderSubmitterUISettings) -> AssetReferences:
    """
    Create AssetReferences from render settings.
    """
    return AssetReferences(
        input_filenames=set(render_settings.input_filenames),
        input_directories=set(render_settings.input_directories),
        output_directories=set(render_settings.output_directories),
    )


def get_conda_packages(doc: Any) -> str:
    """
    Get the required conda packages string based on C4D version.
    """
    c4d_major_version = str(c4d.GetC4DVersion())[:4]
    adaptor_version = ".".join(str(v) for v in adaptor_version_tuple[:2])
    packages = f"cinema4d={c4d_major_version}.* cinema4d-openjd={adaptor_version}.*"

    render_data = doc.GetActiveRenderData()
    if render_data[c4d.RDATA_RENDERENGINE] == 1029988:  # Arnold
        packages += " cinema4d-c4dtoa"

    return packages


def get_submit_takes(
    settings: RenderSubmitterUISettings, takes: dict[str, list[TakeData]]
) -> list[TakeData]:
    """
    Determine which takes will be submitted based on take selection setting.
    """
    if settings.take_selection == TakeSelection.MAIN:
        return takes["main_data_list"]
    if settings.take_selection == TakeSelection.ALL:
        return takes["take_data_list"]
    if settings.take_selection == TakeSelection.MARKED:
        return takes["marked_data_list"]
    if settings.take_selection == TakeSelection.CURRENT:
        return takes["current_data_list"]
    return takes["main_data_list"]


def check_take_token_warnings(
    settings: RenderSubmitterUISettings, takes: dict[str, list[TakeData]]
) -> None:
    """
    Check if multiple takes are selected without $take token in output paths.
    Adds a warning if output files will overwrite each other.
    """
    submit_takes = get_submit_takes(settings, takes)
    if len(submit_takes) == 1:
        return
    if _TAKE_TOKEN in settings.output_path:
        return
    if _TAKE_TOKEN in settings.multi_pass_path:
        return
    warning_collector.add_warning(
        f"Multiple takes are selected but output paths do not contain the {_TAKE_TOKEN} token. "
        f"This will cause different takes to overwrite each other. Use {_TAKE_TOKEN} in your path to avoid this."
    )


def export_to_temp_folder(temp_dir: str, asset_references: AssetReferences) -> None:
    """
    Exports the current Cinema 4D project to a temporary folder and updates the asset references.
    If SaveProject fails due to missing asset paths, an exception will be returned.

    Args:
        temp_dir: Path to the temporary directory
        asset_references: Asset references to update
    """

    doc = c4d.documents.GetActiveDocument()

    # Get the original scene file path BEFORE the temp export
    # This is crucial because Scene.name() will change after SaveProject
    original_scene_file_path = Path(Scene.name())
    original_scene_dir = original_scene_file_path.parent
    original_fonts_dir = original_scene_dir / FONTS_DIR

    # Save the project to the temporary directory
    temp_file_path = os.path.join(temp_dir, doc.GetDocumentName())
    save_success = c4d.documents.SaveProject(
        doc,
        c4d.SAVEPROJECT_ASSETS | c4d.SAVEPROJECT_SCENEFILE,
        temp_file_path,
        [],
        [],
    )

    if not save_success:
        raise RuntimeError(
            "Exporting the scene failed. Please fix all the paths for your assets in your scene in Cinema 4D's Window menu bar > Project Asset Inspector."
        )

    fonts_dir = Path(Scene.name()).parent / FONTS_DIR

    # Copy fonts from the original scene's fonts directory to the temp directory (Windows only)
    if is_windows() and original_fonts_dir.exists() and original_fonts_dir.is_dir():
        # Create the fonts directory in the temp location
        fonts_dir.mkdir(exist_ok=True, parents=True)

        # Copy all font files from the original fonts directory
        for font_file in original_fonts_dir.iterdir():
            if font_file.is_file():
                destination = fonts_dir / font_file.name
                shutil.copy2(font_file, destination)

    # If we get here, save was successful
    # Get all files within the temp directory
    temp_assets = set()

    for root, _, files in os.walk(temp_dir):
        for file in files:
            file_path = os.path.join(root, file)
            temp_assets.add(os.path.normpath(file_path))

    # Add all assets to the asset references
    asset_references.input_filenames = temp_assets


def _pre_gui_hook_confirm_callback(parent):
    """Choose the confirmation callback for pre-GUI hooks based on the auto_accept setting.

    Returns ``None`` (run hooks without prompting) when ``settings.auto_accept`` is enabled,
    otherwise the standard Qt confirmation dialog from ``qt_hook_confirmation``. Kept as a small
    helper so the auto_accept branch can be unit-tested headlessly.
    """
    if str2bool(get_setting("settings.auto_accept")):
        return None

    return qt_hook_confirmation(parent)


def _show_submitter(temp_dir: str, parent=None, f=Qt.WindowType.Tool):  # type: ignore[call-overload]
    """
    Creates and returns a submission dialog for rendering jobs.

    This function initializes render settings, processes takes from the active document,
    sets up attachments, and configures a submission dialog with necessary callbacks
    and requirements for job submission.

    Args:
        temp_dir: Path to a temporary directory for job bundle export
        parent: The parent widget
        f: Window flags
    """

    render_settings = initialize_render_settings()

    doc = c4d.documents.GetActiveDocument()

    takes = get_takes_from_doc(doc)

    auto_detected_attachments = setup_auto_detected_attachments(takes["take_data_list"])
    attachments = setup_attachments(render_settings)

    # Check for renderer warnings
    # (must be after setup_auto_detected_attachments which clears warnings)
    render_data = doc.GetActiveRenderData()
    render_id = render_data[c4d.RDATA_RENDERENGINE]
    renderer_warning = get_renderer_warning(render_id)
    if renderer_warning:
        logger.warning(renderer_warning)

    conda_packages = get_conda_packages(doc)

    # Create SubmitterInfo with all available metadata
    release_date = _get_release_date()
    additional_info: dict[str, Any] | None = (
        {"release_date": release_date} if release_date else None
    )

    submitter_info = SubmitterInfo(
        submitter_name="Cinema4D",
        submitter_package_name="deadline-cloud-for-cinema4d",
        submitter_package_version=".".join(str(v) for v in adaptor_version_tuple),
        host_application_name="Cinema 4D",
        host_application_version=str(c4d.GetC4DVersion()),
        additional_info=additional_info,
    )

    # Maps each sticky field a pre-GUI hook overwrites -> (pre-hook value, hook value). Populated
    # after the hooks run below and passed to create_job_bundle, which uses it to keep hook output
    # out of the persisted sticky settings. See the block near apply_pre_gui_output.
    pre_gui_hook_sticky_reset: dict[str, tuple[Any, Any]] = {}

    def on_create_job_bundle_callback(
        widget: SubmitJobToDeadlineDialog,
        job_bundle_dir: str,
        settings: RenderSubmitterUISettings,
        queue_parameters: list[JobParameter],
        asset_references: AssetReferences,
        host_requirements: dict[str, Any] | None = None,
        purpose: JobBundlePurpose = JobBundlePurpose.SUBMISSION,
    ) -> dict[str, Any]:
        """
        Callback function for creating a job bundle when submitting the job.
        """
        submit_takes = get_submit_takes(settings, takes)
        warn_duplicate_take_names(submit_takes)

        check_take_token_warnings(settings, takes)

        if warning_collector.has_warnings():
            continue_submission = SubmissionWarningDialog.show_warnings(
                warning_collector.get_warnings(), "Issues Detected", widget
            )

            if not continue_submission:
                # User chose to cancel submission
                raise RuntimeError("Submission cancelled")

        return create_job_bundle(
            settings,
            takes,
            job_bundle_dir,
            asset_references,
            queue_parameters,
            widget.job_attachments.attachments,
            temp_dir,
            host_requirements,
            pre_gui_hook_sticky_reset=pre_gui_hook_sticky_reset,
        )

    shared_parameter_values = {
        "CondaPackages": conda_packages,
    }

    # Run pre-GUI hooks so studios can pre-populate dialog fields before it opens. Cinema 4D has
    # no on-disk job bundle at this point, so hooks are sourced from DEADLINE_HOOKS_DIR only
    # (bundle_dir=None), gated by settings.allow_environment_hooks. The confirmation prompt is
    # skipped when auto_accept is set; otherwise the standard dialog is shown.
    try:
        pre_gui_output = run_pre_gui_hooks(
            PreGuiHookContext(
                bundle_dir=None,
                job_name=render_settings.name,
                submitter_name="cinema4d",
                parameters=dict(shared_parameter_values),
            ),
            confirm_callback=_pre_gui_hook_confirm_callback(parent),
        )
    except DeadlineOperationCanceled:
        # The user declined the hook confirmation prompt. This is a normal cancellation, not an
        # error, so abort opening the submitter silently by returning None; show_submitter skips
        # the dialog. Without this, the exception would surface as a spurious "Deadline UI launch
        # failed" error for what is a deliberate "No" click.
        return None
    # RenderSubmitterUISettings has no `.parameters` list, so apply_pre_gui_output routes
    # name/description onto it and every hook parameter into shared_parameter_values.
    # run_pre_gui_hooks returns {} when no hooks run (and raises DeadlineOperationCanceled, handled
    # above, if the user declines); `or {}` is defensive against any future contract change so the
    # common no-hooks path can never pass a falsy value into apply_pre_gui_output.
    #
    # name/description (and deadline:* job properties routed through shared_parameter_values) are
    # sticky settings (data_classes.py). Snapshot the pre-hook (scene/sticky) state first, then
    # record what the hook actually changed so create_job_bundle can scope those to this session
    # (keep them out of the sticky write). This stops hook output from persisting as a stale default
    # once the hook is disabled and from feeding back on the next launch, while any edit the user
    # makes in the dialog still persists. See _compute_pre_gui_hook_sticky_reset.
    name_description_baseline = {
        attr: getattr(render_settings, attr) for attr in ("name", "description")
    }
    shared_values_before_hook = dict(shared_parameter_values)
    apply_pre_gui_output(pre_gui_output or {}, render_settings, shared_parameter_values)
    pre_gui_hook_sticky_reset = _compute_pre_gui_hook_sticky_reset(
        render_settings,
        name_description_baseline,
        shared_values_before_hook,
        shared_parameter_values,
    )

    submitter_dialog = SubmitJobToDeadlineDialog(
        job_setup_widget_type=SceneSettingsWidget,
        initial_job_settings=render_settings,
        initial_shared_parameter_values=shared_parameter_values,
        auto_detected_attachments=auto_detected_attachments,
        attachments=attachments,
        on_create_job_bundle_callback=on_create_job_bundle_callback,
        parent=parent,
        f=f,
        show_host_requirements_tab=True,
        submitter_info=submitter_info,
        use_deadline_cloud_v2_channel=True,
    )

    return submitter_dialog
