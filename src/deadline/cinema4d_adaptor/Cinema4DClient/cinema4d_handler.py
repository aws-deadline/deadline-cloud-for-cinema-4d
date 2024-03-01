# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os as os
from typing import Any, Callable, Dict

try:
    import c4d  # type: ignore
    from c4d import bitmaps
except ImportError:  # pragma: no cover
    raise OSError("Could not find the Cinema4D module. Are you running this inside of Cinema4D?")


def progress_callback(progress, progress_type):
    if progress_type == c4d.RENDERPROGRESSTYPE_DURINGRENDERING:
        print("ALF_PROGRESS %g" % (progress * 100))


class Cinema4DHandler:
    action_dict: Dict[str, Callable[[Dict[str, Any]], None]] = {}
    render_kwargs: Dict[str, Any]

    def __init__(self) -> None:
        """
        Constructor for the c4dpy handler. Initializes action_dict and render variables
        """
        self.action_dict = {
            "scene_file": self.set_scene_file,
            "take": self.set_take,
            "frame": self.set_frame,
            "start_render": self.start_render,
        }
        self.render_kwargs = {}
        self.take = "Main"

    def start_render(self, data: dict) -> None:
        self.doc = c4d.documents.GetActiveDocument()
        self.render_data = self.doc.GetActiveRenderData()
        self.render_data[c4d.RDATA_FRAMESEQUENCE] = c4d.RDATA_FRAMESEQUENCE_MANUAL
        frame = int(self.render_kwargs["frame"])
        fps = self.doc.GetFps()
        self.render_data[c4d.RDATA_FRAMEFROM] = c4d.BaseTime(frame, fps)
        self.render_data[c4d.RDATA_FRAMETO] = c4d.BaseTime(frame, fps)
        self.render_data[c4d.RDATA_FRAMESTEP] = 1
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
        if result != c4d.RENDERRESULT_OK and result != c4d.RENDERRESULT_USERBREAK:
            print("Error: RenderDocument: %s" % result)
        else:
            print("Finished Rendering")

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
