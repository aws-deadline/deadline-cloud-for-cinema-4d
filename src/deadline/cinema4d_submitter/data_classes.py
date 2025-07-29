# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import dataclasses
import json
import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from deadline.client.ui.dataclasses.timeouts import TimeoutEntry, TimeoutTableEntries

from .takes import TakeSelection  # type: ignore
from .error_checking import ErrorChecking
from datetime import timedelta

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"

_logger = logging.getLogger(__name__)


def default_timeout_entries() -> TimeoutTableEntries:
    entries = {
        "Task Run": TimeoutEntry(
            tooltip="Maximum duration for a task run or for rendering a frame.",
            seconds=int(timedelta(days=2).total_seconds()),
            is_activated=True,
        ),
        "Cinema 4D launch": TimeoutEntry(
            tooltip="Maximum duration for Cinema 4D to launch. In general, this takes less than a minute.",
            is_activated=True,
            seconds=int(timedelta(minutes=10).total_seconds()),
        ),
        "Cinema 4D shutdown": TimeoutEntry(
            tooltip="Maximum duration for Cinema 4D to shutdown gracefully. In general, this takes less than 5 seconds.",
            is_activated=True,
            seconds=int(timedelta(minutes=5).total_seconds()),
        ),
    }
    return TimeoutTableEntries(entries=entries)


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="Cinema4D")

    name: str = field(default="", metadata={"sticky": True})
    description: str = field(default="", metadata={"sticky": True})

    priority: int = field(default=50, metadata={"sticky": True})
    initial_status: str = field(default="READY", metadata={"sticky": True})
    max_failed_tasks_count: int = field(default=20, metadata={"sticky": True})
    max_retries_per_task: int = field(default=5, metadata={"sticky": True})
    max_worker_count: int = field(
        default=-1, metadata={"sticky": True}
    )  # -1 indicates unlimited max worker count

    override_frame_range: bool = field(default=False, metadata={"sticky": True})
    override_output_path: bool = field(default=False, metadata={"sticky": True})
    override_multi_pass_path: bool = field(default=False, metadata={"sticky": True})
    frame_list: str = field(default="", metadata={"sticky": True})
    output_path: str = field(default="", metadata={"sticky": True})
    multi_pass_path: str = field(default="", metadata={"sticky": True})

    input_filenames: list[str] = field(default_factory=list, metadata={"sticky": True})
    input_directories: list[str] = field(default_factory=list, metadata={"sticky": True})
    output_directories: list[str] = field(default_factory=list, metadata={"sticky": True})

    take_selection: TakeSelection = field(default=TakeSelection.MAIN, metadata={"sticky": True})
    activate_error_checking: str = field(
        default=ErrorChecking.ACTIVATE.value, metadata={"sticky": True}
    )
    timeouts: TimeoutTableEntries = field(
        default_factory=default_timeout_entries, metadata={"sticky": True}
    )
    export_job_bundle_to_temp: bool = field(default=False, metadata={"sticky": True})

    # developer options
    include_adaptor_wheels: bool = field(default=False, metadata={"sticky": True})

    def load_sticky_settings(self, scene_filename: str):
        sticky_settings_filename = Path(scene_filename).with_suffix(
            RENDER_SUBMITTER_SETTINGS_FILE_EXT
        )
        if sticky_settings_filename.exists() and sticky_settings_filename.is_file():
            try:
                with open(sticky_settings_filename, encoding="utf8") as fh:
                    sticky_settings = json.load(fh)

                if isinstance(sticky_settings, dict):
                    sticky_fields = {
                        field.name: field
                        for field in dataclasses.fields(self)
                        if field.metadata.get("sticky")
                    }
                    for name, value in sticky_settings.items():
                        # Only set fields that are defined in the dataclass
                        if name in sticky_fields:
                            if name == "timeouts":
                                self.timeouts.update_from_sticky_settings(value)
                            # Convert take_selection int to TakeSelection enum to access its data
                            elif name == "take_selection":
                                self.take_selection = TakeSelection(value)
                            else:
                                setattr(self, name, value)
            except (OSError, json.JSONDecodeError):
                # If something bad happened to the sticky settings file,
                # just use the defaults instead of producing an error.
                traceback.print_exc()
                _logger.warning(
                    f"Failed to load sticky settings file {sticky_settings_filename.absolute()}, reverting to the"
                    + "default settings."
                )

    def save_sticky_settings(self, scene_filename: str):
        sticky_settings_filename = Path(scene_filename).with_suffix(
            RENDER_SUBMITTER_SETTINGS_FILE_EXT
        )
        sticky_settings_path = str(sticky_settings_filename.absolute())
        try:
            with open(sticky_settings_filename, "w", encoding="utf8") as fh:
                obj = {
                    field.name: getattr(self, field.name)
                    for field in dataclasses.fields(self)
                    if field.metadata.get("sticky")
                    and field.name not in ["timeouts", "output_path", "multi_pass_path"]
                }
                obj["timeouts"] = self.timeouts.to_sticky_settings_dict()
                if self.override_output_path:
                    obj["output_path"] = self.output_path
                if self.override_multi_pass_path:
                    obj["multi_pass_path"] = self.multi_pass_path
                json.dump(obj, fh, indent=1)
        except OSError as e:
            traceback.print_exc()
            if len(sticky_settings_path) >= 256:
                # raise an error here because if we ignore this error, there will likely be later errors in rendering
                # due to exceeding the max path length
                raise RuntimeError(
                    "Failed to save sticky settings file. This usually occurs from exceeding the maximum path length. "
                    + f"Please reduce the length of your .c4d filename. Error: {e}"
                )
            _logger.warning(f"Failed to save sticky settings file to {sticky_settings_path}.")
