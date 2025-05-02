# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
import traceback
from typing import Any, Callable, Dict

try:
    import c4d  # type: ignore
    import maxon
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

    def __init__(self, map_path: Callable[[str], str]) -> None:
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

    def _remap_assets(self) -> None:
        """
        Asset references in the .c4d files are not automatically re-mapped if they are
        absolute paths. This function remaps the asset references to the new paths.
        """
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
            if not (owner and param_id and filename):
                # unrelated asset, e.g. the main scene which is already pathmapped
                continue
            mapped_path = self.map_path(filename)
            # note: we can't skip if mapped_path == filename because some internal
            # references in the owner nodes may need to be updated

            # whether we have done owner[param_id] = mapped_path
            attempted_basic_path_mapping_approach = False
            try:
                print(
                    f"Attempting to update path for asset with owner '{owner}', paramId '{param_id}', "
                    f"new filename '{mapped_path}', nodeSpace '{node_space}', and nodePath '{node_path}'."
                )
                success = self._pathmap_recognized_types(
                    owner, param_id, node_space, node_path, mapped_path
                )

                if not success:
                    print(
                        f"WARNING: asset wasn't recognized. Attempting to path map {owner}[{param_id}] = {mapped_path}"
                    )
                    attempted_basic_path_mapping_approach = True
                    owner[param_id] = mapped_path

            except Exception as e:
                print(
                    f"WARNING: asset with asset owner '{owner}', asset paramId {param_id}, filename "
                    f"'{filename}', nodeSpace '{node_space}', and nodePath '{node_path}' could not be path "
                    f"mapped. Error: {e} {traceback.format_exc()}"
                )
                if not attempted_basic_path_mapping_approach:
                    print(
                        f"Attempting to use basic path mapping {owner}[{param_id}] = {mapped_path}"
                    )
                    try:
                        owner[param_id] = mapped_path
                    except Exception as f:
                        print(
                            f"{owner}[{param_id}] = {mapped_path} failed. Error: {f} {traceback.format_exc()}"
                        )

    def _pathmap_recognized_types(
        self, owner, param_id, node_space, node_path, mapped_path
    ) -> bool:
        """
        Applies path mapping to recognized owner types.

        Returns True if the owner is recognized and has been path mapped.
        Returns False otherwise.
        """
        if isinstance(owner, c4d.BaseShader):
            # C4D classic textures
            return self._pathmap_base_shader(owner, param_id, mapped_path)

        if isinstance(owner, c4d.BaseObject):
            # Redshift light textures
            return self._pathmap_base_object(owner, mapped_path)

        if isinstance(owner, c4d.documents.BaseVideoPost):
            # PostFX, e.g. LUT files or background files
            return self._pathmap_base_video_post(owner, mapped_path)

        if isinstance(owner, c4d.BaseMaterial):
            # Redshift node-based materials
            return self._pathmap_base_material(owner, node_space, node_path, mapped_path)

        return False

    def _pathmap_base_shader(self, owner, param_id, mapped_path) -> bool:
        # C4D classic materials have a param ID other than -1
        if param_id != -1:
            owner[param_id] = mapped_path
            return True
        return False

    def _pathmap_base_object(self, owner, mapped_path) -> bool:
        # c4d.BaseObject e.g. Redshift light texture
        mapped = False
        for item in [
            c4d.REDSHIFT_LIGHT_PHYSICAL_TEXTURE,
            c4d.REDSHIFT_LIGHT_DOME_TEX0,
            c4d.REDSHIFT_LIGHT_DOME_TEX1,
        ]:
            # there are three types of textures for Redshift lights.
            # For each type of texture, we check if the texture is specified,
            # and if it is, we override the path
            desc_id = c4d.DescID(
                # 1036765 is the data type for textures
                c4d.DescLevel(item, 1036765),
                c4d.DescLevel(c4d.REDSHIFT_FILE_PATH, c4d.DTYPE_STRING, 0),
            )
            existing_path = owner[desc_id]
            if existing_path:
                owner[desc_id] = mapped_path
                mapped = True

        return mapped

    def _pathmap_base_video_post(self, owner, mapped_path) -> bool:
        # PostFX, e.g. LUT files or background files
        path = owner[c4d.REDSHIFT_POSTEFFECTS_LUT_FILE]
        if path:
            owner[c4d.REDSHIFT_POSTEFFECTS_LUT_FILE] = mapped_path
            return True
        return False

    def _pathmap_base_material(self, owner, node_space, node_path, mapped_path) -> bool:
        # Redshift materials
        if not (node_path and node_space == "com.redshift3d.redshift4c4d.class.nodespace"):
            return False

        # Redshift node
        node_material = owner.GetNodeMaterialReference()
        graph = node_material.GetGraph(maxon.Id(node_space))
        with graph.BeginTransaction() as transaction:
            node = graph.GetNode(maxon.NodePath(node_path))
            node_id = node.GetId().ToString()
            if node_id.split("@")[0] == "texturesampler":
                path_port = (
                    node.GetInputs()
                    .FindChild("com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0")
                    .FindChild("path")
                )
                path_port.SetDefaultValue(mapped_path)
            else:
                print(f"Unrecognized nodeId {node_id}")
                return False
            transaction.Commit()
        return True

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
