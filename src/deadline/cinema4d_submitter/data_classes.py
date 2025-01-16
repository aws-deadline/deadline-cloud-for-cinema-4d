# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import dataclasses
import json
import logging
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .takes import TakeSelection  # type: ignore

RENDER_SUBMITTER_SETTINGS_FILE_EXT = ".deadline_render_settings.json"

_logger = logging.getLogger(__name__)


@dataclass
class RenderSubmitterUISettings:
    """
    Settings that the submitter UI will use
    """

    submitter_name: str = field(default="Cinema4D")

    name: str = field(default="", metadata={"sticky": True})
    description: str = field(default="", metadata={"sticky": True})

    override_frame_range: bool = field(default=False, metadata={"sticky": True})
    frame_list: str = field(default="", metadata={"sticky": True})
    output_path: str = field(default="")
    multi_pass_path: str = field(default="")

    input_filenames: list[str] = field(default_factory=list, metadata={"sticky": True})
    input_directories: list[str] = field(default_factory=list, metadata={"sticky": True})
    output_directories: list[str] = field(default_factory=list, metadata={"sticky": True})

    take_selection: TakeSelection = field(default=TakeSelection.MAIN)

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
                }
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
