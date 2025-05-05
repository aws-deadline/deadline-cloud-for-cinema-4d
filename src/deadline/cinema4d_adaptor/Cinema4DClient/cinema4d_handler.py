# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import re
import traceback
from pathlib import Path
from typing import Any, Callable, Dict

from openjd.adaptor_runtime.adaptors import PathMappingRule
from openjd.adaptor_runtime._utils import secure_open


try:
    import c4d  # type: ignore
    from c4d import bitmaps
except ImportError:  # pragma: no cover
    raise OSError("Could not find the Cinema4D module. Are you running this inside of Cinema4D?")

_RENDERRESULT = {
    c4d.RENDERRESULT_OK: "Function was successful.",
    c4d.RENDERRESULT_OUTOFMEMORY: "Not enough memory.",
    c4d.RENDERRESULT_ASSETMISSING: "Assets (textures etc.) are missing.",
    c4d.RENDERRESULT_SAVINGFAILED: "Failed to save.",
    c4d.RENDERRESULT_USERBREAK: "User stopped the processing.",
    c4d.RENDERRESULT_GICACHEMISSING: "GI cache is missing.",
    c4d.RENDERRESULT_NOMACHINE: "Machine was not found. (Team Rendering only)",
    c4d.RENDERRESULT_PROJECTNOTFOUND: "Project was not found.",
    c4d.RENDERRESULT_ERRORLOADINGPROJECT: "There was an error while loading the project.",
    c4d.RENDERRESULT_NOOUTPUTSPECIFIED: "Output was not specified.",
}


def progress_callback(progress, progress_type):
    if progress_type == c4d.RENDERPROGRESSTYPE_DURINGRENDERING:
        print("ALF_PROGRESS %g" % (progress * 100))


class Cinema4DHandler:
    action_dict: Dict[str, Callable[[Dict[str, Any]], None]] = {}
    render_kwargs: Dict[str, Any]
    map_path: Callable[[str], str]

    def __init__(
        self,
        map_path: Callable[[str], str],
        path_mapping_rules: Callable[[], list[PathMappingRule]],
    ) -> None:
        """
        Constructor for the c4dpy handler. Initializes action_dict and render variables
        """
        self.action_dict = {
            "scene_file": self.set_scene_file,
            "take": self.set_take,
            "frame": self.set_frame,
            "start_render": self.start_render,
            "output_path": self.output_path,
            "multi_pass_path": self.multi_pass_path,
        }
        self.render_kwargs = {}
        self.take = "Main"
        self.map_path = map_path
        self.path_mapping_rules = path_mapping_rules

    def _remap_assets(self) -> None:
        """
        Asset references in the .c4d files are not automatically re-mapped if they are
        absolute paths. This function remaps the asset references to the new paths.
        """
        self._set_c4d_native_asset_pathmap()
        self._set_redshift_pathmap()

    def _set_c4d_native_asset_pathmap(self) -> None:
        asset_list: list[Dict[str, Any]] = []
        c4d.documents.GetAllAssetsNew(
            self.doc, allowDialogs=False, lastPath="", assetList=asset_list
        )
        for asset in asset_list:
            owner = asset.get("owner")
            param_id = asset.get("paramId")
            filename = asset.get("filename")
            node_space = asset.get("nodeSpace")
            node_path = asset.get("nodePath")
            if owner and param_id and filename:
                if param_id != -1:
                    try:
                        # C4D classic assets have a param ID other than -1
                        owner[param_id] = self.map_path(filename)
                    except Exception as e:
                        print(
                            f"WARNING: asset with asset owner '{owner}', paramId {param_id}, filename "
                            f"'{filename}', nodeSpace '{node_space}', and nodePath '{node_path}' could not be path "
                            f"mapped. Error: {e} {traceback.format_exc()}"
                        )

    # Redshift path mapping
    def _set_redshift_pathmap(self) -> None:
        rules = self.path_mapping_rules()
        if not rules:
            print("No path mapping rules found")
            return

        print(f"Path mapping rules: {rules}")

        redshift_rules: list[tuple[str, str]] = [
            (rule.source_path.replace("\\", "/"), rule.destination_path.replace("\\", "/"))
            for rule in rules
        ]

        # "C:/Users/AUser/Directory" "/sessions/session-abcd/"
        redshift_rule_regex = re.compile(r"\"([^\"]*)\"\s+\"([^\"]*)\"")

        # Collect any additional rules if REDSHIFT_PATHOVERRIDE_FILE is already set
        if existing_rule_file_path := os.getenv("REDSHIFT_PATHOVERRIDE_FILE"):
            print(
                f"Found existing REDSHIFT_PATHOVERRIDE_FILE environment variable: {existing_rule_file_path}"
            )
            try:
                with secure_open(
                    existing_rule_file_path, "r", encoding="utf-8"
                ) as existing_rule_file:
                    redshift_rules.extend(redshift_rule_regex.findall(existing_rule_file.read()))
            except FileNotFoundError:
                print(
                    f"The file pointed to by the REDSHIFT_PATHOVERRIDE_FILE environment variable does not exist at: {existing_rule_file_path}"
                )

        # Collect any additional rules if REDSHIFT_PATHOVERRIDE_STRING is already set
        if existing_rule_str := os.getenv("REDSHIFT_PATHOVERRIDE_STRING"):
            print(f"Found existing REDSHIFT_PATHOVERRIDE_STRING: {existing_rule_str}")
            redshift_rules.extend(redshift_rule_regex.findall(existing_rule_str))

        # Redshift expects double quoted space delimited "source" "destination" pairs
        # example: "C:/Users/AUser/Directory" "/sessions/session-abcd/"
        # https://help.maxon.net/r3d/maya/en-us/Content/html/Redshift+Environment+Variables.html
        formatted_rules = "\n".join([f'"{rule[0]}" "{rule[1]}"' for rule in redshift_rules])
        # Write all rules to a new temp override file and point to it
        new_pathmap_file_path = Path(os.getcwd(), "new_redshift_pathmap_override.txt")
        print(f"Writing path mapping rules: {formatted_rules}")
        with secure_open(
            new_pathmap_file_path, open_mode="w", encoding="utf-8"
        ) as new_pathmap_file:
            new_pathmap_file.write(formatted_rules)
        print(f"Setting REDSHIFT_PATHOVERRIDE_FILE to: {str(new_pathmap_file_path)}")
        os.environ["REDSHIFT_PATHOVERRIDE_FILE"] = str(new_pathmap_file_path)

    def start_render(self, data: dict) -> None:
        self.doc = c4d.documents.GetActiveDocument()
        self.render_data = self.doc.GetActiveRenderData()
        self.render_data[c4d.RDATA_FRAMESEQUENCE] = c4d.RDATA_FRAMESEQUENCE_MANUAL
        frame = int(self.render_kwargs.get("frame", data.get("frame")))
        fps = self.doc.GetFps()
        self.render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(frame, fps)
        self.render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(frame, fps)
        self.render_data[c4d.RDATA_FRAMESTEP] = 1

        if self.render_data[c4d.RDATA_PATH]:
            self.render_data[c4d.RDATA_PATH] = self.map_path(self.render_data[c4d.RDATA_PATH])
        if (
            self.render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE]
            and self.render_data[c4d.RDATA_MULTIPASS_FILENAME]
        ):
            self.render_data[c4d.RDATA_MULTIPASS_FILENAME] = self.map_path(
                self.render_data[c4d.RDATA_MULTIPASS_FILENAME]
            )

        self._remap_assets()

        bm = bitmaps.MultipassBitmap(
            int(self.render_data[c4d.RDATA_XRES]),
            int(self.render_data[c4d.RDATA_YRES]),
            c4d.COLORMODE_RGB,
        )
        rd = self.render_data.GetDataInstance()
        result = c4d.documents.RenderDocument(
            self.doc,
            rd,
            bm,
            c4d.RENDERFLAGS_EXTERNAL | c4d.RENDERFLAGS_SHOWERRORS,
            prog=progress_callback,
        )
        result_description = _RENDERRESULT.get(result)
        if result_description is None:
            raise RuntimeError("Error: unhandled render result: %s" % result)
        if result != c4d.RENDERRESULT_OK:
            raise RuntimeError("Error: render result: %s" % result_description)
        else:
            print("Finished Rendering")

    def output_path(self, data: dict) -> None:
        output_path = data.get("output_path", "")
        if output_path:
            doc = c4d.documents.GetActiveDocument()
            render_data = doc.GetActiveRenderData()
            render_data[c4d.RDATA_PATH] = self.map_path(output_path)

    def multi_pass_path(self, data: dict) -> None:
        multi_pass_path = data.get("multi_pass_path", "")
        if multi_pass_path:
            doc = c4d.documents.GetActiveDocument()
            render_data = doc.GetActiveRenderData()
            render_data[c4d.RDATA_MULTIPASS_FILENAME] = self.map_path(multi_pass_path)

    def set_take(self, data: dict) -> None:
        """
        Sets the take to render

        Args:
            data (dict):
        """
        take_name = data.get("take", "")
        doc = c4d.documents.GetActiveDocument()
        take_data = doc.GetTakeData()
        if not take_data:
            return

        def get_child_takes(take):
            child_takes = take.GetChildren()
            all_takes = child_takes
            if child_takes:
                for child_take in child_takes:
                    all_takes.extend(get_child_takes(child_take))
            return all_takes

        main_take = take_data.GetCurrentTake()
        all_takes = [main_take] + get_child_takes(main_take)

        take = None
        for take in all_takes:
            if take.GetName() == take_name:
                break
        if take is None:
            print("Error: take not found: %s" % take_name)
        take_data.SetCurrentTake(take)

    def set_frame(self, data: dict) -> None:
        """
        Sets the frame to render

        Args:
            data (dict):
        """
        self.render_kwargs["frame"] = int(data.get("frame", ""))

    def set_scene_file(self, data: dict) -> None:
        """
        Opens the scene file in Cinema4D.

        Args:
            data (dict): The data given from the Adaptor. Keys expected: ['scene_file']

        Raises:
            FileNotFoundError: If path to the scene file does not yield a file
        """
        scene_file = data.get("scene_file", "")
        if not os.path.isfile(scene_file):
            raise FileNotFoundError(f"The scene file '{scene_file}' does not exist")
        doc = c4d.documents.LoadDocument(
            scene_file, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
        )
        if doc is None:
            print("Error: LoadDocument failed: %s" % scene_file)
        else:
            c4d.documents.InsertBaseDocument(doc)
            c4d.documents.SetActiveDocument(doc)
