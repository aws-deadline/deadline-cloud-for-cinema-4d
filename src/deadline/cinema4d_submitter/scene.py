# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterator, Optional

import c4d

"""
Functionality used for querying scene settings
"""


class RendererNames(IntEnum):
    """
    A collection of supported renderers and their respective name.
    """

    # native
    standard = 0
    physical = 1023342
    # previewhardware = 300001061  # Not supported for submission

    # 3rd party, now acquired as maxon default
    redshift = 1036219

    # 3rd party
    arnold = 1029988
    vray = 1053272
    corona = 1030480
    cycles = 1035287
    octane = 1029525


class Animation:
    """
    Functionality for retrieving Animation related settings from the active
    document
    """

    @staticmethod
    def current_frame() -> int:
        """
        Returns the current frame number from Cinema 4D.
        """
        doc = c4d.documents.GetActiveDocument()
        data = doc.GetActiveRenderData()
        return int(data[c4d.RDATA_FRAMEFROM].GetFrame(doc.GetFps()))

    @staticmethod
    def start_frame() -> int:
        """
        Returns the start frame for the scenes render
        """
        doc = c4d.documents.GetActiveDocument()
        data = doc.GetActiveRenderData()
        return int(data[c4d.RDATA_FRAMEFROM].GetFrame(doc.GetFps()))

    @staticmethod
    def end_frame() -> int:
        """
        Returns the End frame for the scenes Render
        """
        doc = c4d.documents.GetActiveDocument()
        data = doc.GetActiveRenderData()
        return int(data[c4d.RDATA_FRAMETO].GetFrame(doc.GetFps()))

    @staticmethod
    def frame_step() -> int:
        """
        Returns the frame step of the current render.
        """
        doc = c4d.documents.GetActiveDocument()
        data = doc.GetActiveRenderData()
        return int(data[c4d.RDATA_FRAMESTEP])

    @staticmethod
    def extension_padding() -> int:
        """
        Returns the amount that frames are padded by in the output file name.
        """
        return 4

    @classmethod
    def frame_list(cls, data=None) -> "FrameRange":
        """
        Retursn a FrameRange object representing the full framelist.
        """
        if data is None:
            doc = c4d.documents.GetActiveDocument()
            data = doc.GetActiveRenderData()
        if data[c4d.RDATA_FRAMESEQUENCE] != c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME:
            return FrameRange(start=cls.start_frame(), stop=cls.end_frame(), step=cls.frame_step())
        else:
            return FrameRange(start=cls.current_frame())


class Scene:
    """
    Functionality for retrieving settings from the active scene
    """

    @staticmethod
    def name() -> str:
        """
        Returns the full path to the Active Scene
        """
        doc = c4d.documents.GetActiveDocument()
        return doc[c4d.DOCUMENT_FILEPATH]

    @staticmethod
    def renderer(render_data=None) -> str:
        """
        Returns the name of the current renderer as defined in the scene
        """
        if render_data is None:
            doc = c4d.documents.GetActiveDocument()
            render_data = doc.GetActiveRenderData()
        render_id = render_data[c4d.RDATA_RENDERENGINE]
        return RendererNames(render_id).name

    @staticmethod
    def get_output_directories(render_data=None, take=None) -> set[str]:
        """
        Returns a list of directories files will be output to.
        """
        doc = c4d.documents.GetActiveDocument()
        doc_path = doc.GetDocumentPath()
        if not take:
            take_data = doc.GetTakeData()
            take = take_data.GetCurrentTake()
        render_data = Scene.get_render_data(doc=doc, take=take)
        rbc = render_data.GetDataInstance()
        rpd = {
            "_doc": doc,
            "_rData": render_data,
            "_rBc": rbc,
            "_frame": doc.GetTime().GetFrame(doc.GetFps()),
        }
        if take:
            rpd["_take"] = take
        image_paths = set()
        if render_data[c4d.RDATA_SAVEIMAGE]:
            path = render_data[c4d.RDATA_PATH]
            xpath = c4d.modules.tokensystem.FilenameConvertTokens(path, rpd)
            if not os.path.isabs(xpath):
                if xpath.startswith("./"):
                    xpath = xpath[2:]
                xpath = os.path.join(doc_path, xpath)
            image_paths.add(os.path.dirname(os.path.normpath(xpath)))
        if render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE]:
            path = render_data[c4d.RDATA_MULTIPASS_FILENAME]
            xpath = c4d.modules.tokensystem.FilenameConvertTokens(path, rpd)
            if not os.path.isabs(xpath):
                if xpath.startswith("./"):
                    xpath = xpath[2:]
                xpath = os.path.join(doc_path, xpath)
            image_paths.add(os.path.dirname(os.path.normpath(xpath)))
        return image_paths

    @staticmethod
    def get_render_data(doc=None, take=None):
        if doc is None:
            doc = c4d.documents.GetActiveDocument()
        render_data = None
        if take is not None:
            take_data = doc.GetTakeData()
            take_erd = take.GetEffectiveRenderData(take_data)
            if take_erd is not None:
                render_data = take_erd[0]
        if render_data is None:
            render_data = doc.GetActiveRenderData()
        return render_data

    @staticmethod
    def get_output_paths(take=None) -> str:
        doc = c4d.documents.GetActiveDocument()
        doc_path = doc.GetDocumentPath()
        render_data = Scene.get_render_data(doc=doc, take=take)
        render_base_container_instance = render_data.GetDataInstance()
        rpd = {
            "_doc": doc,
            "_rData": render_data,
            "_rBc": render_base_container_instance,
            "_frame": doc.GetTime().GetFrame(doc.GetFps()),
        }
        if take:
            rpd["_take"] = take
        default_out = ""
        multi_out = ""
        if render_data[c4d.RDATA_SAVEIMAGE]:
            path = render_data[c4d.RDATA_PATH]
            xpath = c4d.modules.tokensystem.FilenameConvertTokens(path, rpd)
            if not os.path.isabs(xpath):
                if xpath.startswith("./"):
                    xpath = xpath[2:]
                xpath = os.path.join(doc_path, xpath)
            default_out = os.path.normpath(xpath)
        if render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE]:
            path = render_data[c4d.RDATA_MULTIPASS_FILENAME]
            xpath = c4d.modules.tokensystem.FilenameConvertTokens(path, rpd)
            if not os.path.isabs(xpath):
                if xpath.startswith("./"):
                    xpath = xpath[2:]
                xpath = os.path.join(doc_path, xpath)
            multi_out = os.path.normpath(xpath)
        return default_out, multi_out

    @staticmethod
    def output_path() -> str:
        """
        Returns the path to the default output directory.
        """
        doc = c4d.documents.GetActiveDocument()
        return doc.GetDocumentPath()


@dataclass
class FrameRange:
    """
    Class used to represent a frame range.
    """

    start: int
    stop: Optional[int] = None
    step: Optional[int] = None

    def __repr__(self) -> str:
        if self.stop is None or self.stop == self.start:
            return str(self.start)

        if self.step is None or self.step == 1:
            return f"{self.start}-{self.stop}"

        return f"{self.start}-{self.stop}:{self.step}"

    def __iter__(self) -> Iterator[int]:
        stop: int = self.stop if self.stop is not None else self.start
        step: int = self.step if self.step is not None else 1

        return iter(range(self.start, stop + step, step))
