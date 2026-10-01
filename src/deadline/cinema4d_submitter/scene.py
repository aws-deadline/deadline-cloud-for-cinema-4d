# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import IntEnum

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
    viewport_renderer = 300001061

    # 3rd party, now acquired as maxon default
    redshift = 1036219

    # 3rd party
    arnold = 1029988
    vray = 1053272
    corona = 1030480
    cycles = 1035287
    octane = 1029525


# Renderers that are fully verified to work on Deadline Cloud
VERIFIED_RENDERERS = {
    RendererNames.standard,
    RendererNames.physical,
    RendererNames.redshift,
}

# 3rd party renderers that require plugins installed on workers
THIRD_PARTY_PLUGIN_RENDERERS = {
    RendererNames.arnold,
    RendererNames.vray,
}

# Renderers not supported on Deadline Cloud
UNSUPPORTED_RENDERERS = {
    RendererNames.octane,
    RendererNames.corona,
    RendererNames.cycles,
}

# Renderers that work but produce viewport-quality output (not a full render)
VIEWPORT_RENDERERS = {
    RendererNames.viewport_renderer,
}


def _get_renderer_display_name(render_id: int) -> str:
    """Gets the renderer's display name from Cinema 4D's plugin registry.
    Falls back to the numeric ID if the plugin can't be found."""
    try:
        plugin = c4d.plugins.FindPlugin(render_id, c4d.PLUGINTYPE_VIDEOPOST)
        if plugin:
            return plugin.GetName()
    except Exception:  # noqa: BLE001 - C4D may raise SDK-specific errors during startup
        # FindPlugin may fail if the plugin isn't loaded or C4D is not fully initialized.
        return str(render_id)
    return str(render_id)


def get_renderer_warning(render_id: int) -> str | None:
    """
    Returns a warning message for the given renderer ID, or None if no warning is needed.
    """
    renderer_name = _get_renderer_display_name(render_id)

    try:
        renderer = RendererNames(render_id)
    except ValueError:
        # Unknown renderer not in enum
        return (
            f'The selected renderer "{renderer_name}" has not been verified for '
            f"Deadline Cloud rendering. It may not produce expected results."
        )

    if renderer in VERIFIED_RENDERERS:
        return None

    if renderer in THIRD_PARTY_PLUGIN_RENDERERS:
        return (
            f'The selected renderer "{renderer_name}" is a third-party '
            f"plugin. Ensure it is installed and licensed on your Deadline Cloud workers."
        )

    if renderer in UNSUPPORTED_RENDERERS:
        return (
            f'The selected renderer "{renderer_name}" is not supported '
            f"on Deadline Cloud. Please change your renderer in Render Settings before submitting."
        )

    if renderer in VIEWPORT_RENDERERS:
        return (
            f'The selected renderer "{renderer_name}" produces viewport-quality output, '
            f"not a full render. The output will look like a viewport screenshot "
            f"rather than a production render."
        )

    return None


class Animation:
    """
    Functionality for retrieving Animation related settings from the active
    document
    """

    @staticmethod
    def current_frame(data) -> int:
        """
        Returns the current frame number from Cinema 4D.
        """
        return int(data[c4d.RDATA_FRAMEFROM].GetFrame(int(data[c4d.RDATA_FRAMERATE])))

    @staticmethod
    def start_frame(data) -> int:
        """
        Returns the start frame for the scenes render
        """
        return int(data[c4d.RDATA_FRAMEFROM].GetFrame(int(data[c4d.RDATA_FRAMERATE])))

    @staticmethod
    def end_frame(data) -> int:
        """
        Returns the End frame for the scenes Render
        """
        return int(data[c4d.RDATA_FRAMETO].GetFrame(int(data[c4d.RDATA_FRAMERATE])))

    @staticmethod
    def frame_step(data) -> int:
        """
        Returns the frame step of the current render.
        """
        return int(data[c4d.RDATA_FRAMESTEP])

    @staticmethod
    def custom_frames(data) -> str:
        """
        Returns the custom frames specification of the current render.
        Note that this field may be filled even if custom frames are not being used.
        To check if custom frames are being used, check whether
        doc.GetActiveRenderData()[c4d.RDATA_FRAMESEQUENCE] == c4d.RDATA_FRAMESEQUENCE_CUSTOM
        """
        return data[c4d.RDATA_FRAME_RANGE_STRING]

    @classmethod
    def frame_list(cls, data=None) -> str:
        """
        Returns a string representing the full framelist.
        """
        if data is None:
            doc = c4d.documents.GetActiveDocument()
            data = doc.GetActiveRenderData()
        frame_spec_type = data[c4d.RDATA_FRAMESEQUENCE]
        if frame_spec_type == c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME:
            return str(FrameRange(start=cls.current_frame(data)))
        if (
            hasattr(c4d, "RDATA_FRAMESEQUENCE_CUSTOM")
            and frame_spec_type == c4d.RDATA_FRAMESEQUENCE_CUSTOM
        ):
            return cls.custom_frames(data)
        return str(
            FrameRange(
                start=cls.start_frame(data), stop=cls.end_frame(data), step=cls.frame_step(data)
            )
        )


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
        Returns the name of the current renderer as defined in the scene.
        For unknown renderers not in the RendererNames enum, returns the string
        representation of the renderer ID.
        """
        if render_data is None:
            doc = c4d.documents.GetActiveDocument()
            render_data = doc.GetActiveRenderData()
        render_id = render_data[c4d.RDATA_RENDERENGINE]
        try:
            return RendererNames(render_id).name
        except ValueError:
            # Renderer ID not in enum — return the ID as a string so the submitter
            # can still open. The warning is handled separately by get_renderer_warning().
            return str(render_id)

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

        image_paths = set()
        if render_data[c4d.RDATA_SAVEIMAGE]:
            path = render_data[c4d.RDATA_PATH]
            xpath = Scene.replace_render_path_tokens(
                path, doc=doc, take=take, render_data=render_data
            )
            if not os.path.isabs(xpath):
                xpath = xpath.removeprefix("./")
                xpath = os.path.join(doc_path, xpath)
            image_paths.add(os.path.dirname(os.path.normpath(xpath)))
        if render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE]:
            path = render_data[c4d.RDATA_MULTIPASS_FILENAME]
            xpath = Scene.replace_render_path_tokens(
                path, doc=doc, take=take, render_data=render_data
            )
            if not os.path.isabs(xpath):
                xpath = xpath.removeprefix("./")
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
    def replace_render_path_tokens(path, doc=None, take=None, render_data=None):
        """
        Replaces tokens in a path with actual values from scene and render data
        """
        if doc is None:
            doc = c4d.documents.GetActiveDocument()

        if render_data is None:
            render_data = Scene.get_render_data(doc=doc, take=take)

        render_path_data = {
            "_doc": doc,
            "_rData": render_data,
            "_rBc": render_data.GetDataInstance(),
            "_frame": doc.GetTime().GetFrame(doc.GetFps()),
        }
        if take:
            render_path_data["_take"] = take

        return c4d.modules.tokensystem.FilenameConvertTokens(path, render_path_data)

    @staticmethod
    def get_output_paths(take=None) -> tuple[str, str]:
        """
        Returns the default and multi-pass output paths.
        """
        doc = c4d.documents.GetActiveDocument()
        doc_path = doc.GetDocumentPath()
        render_data = Scene.get_render_data(doc=doc, take=take)

        default_out = ""
        multi_out = ""
        if render_data[c4d.RDATA_SAVEIMAGE]:
            path = render_data[c4d.RDATA_PATH]
            xpath = Scene.replace_render_path_tokens(
                path, doc=doc, take=take, render_data=render_data
            )
            if not os.path.isabs(xpath):
                xpath = xpath.removeprefix("./")
                xpath = os.path.join(doc_path, xpath)
            default_out = os.path.normpath(xpath)
        if render_data[c4d.RDATA_MULTIPASS_SAVEIMAGE]:
            path = render_data[c4d.RDATA_MULTIPASS_FILENAME]
            xpath = Scene.replace_render_path_tokens(
                path, doc=doc, take=take, render_data=render_data
            )
            if not os.path.isabs(xpath):
                xpath = xpath.removeprefix("./")
                xpath = os.path.join(doc_path, xpath)
            multi_out = os.path.normpath(xpath)
        return default_out, multi_out


@dataclass
class FrameRange:
    """
    Class used to represent a frame range.
    """

    start: int
    stop: int | None = None
    step: int | None = None

    def __repr__(self) -> str:
        if self.stop is None or self.stop == self.start:
            return str(self.start)

        if self.step is None or self.step == 1:
            return f"{self.start}-{self.stop}"

        return f"{self.start}-{self.stop}:{self.step}"
