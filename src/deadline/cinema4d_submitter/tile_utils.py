# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

from copy import deepcopy
from typing import Any

from ._yaml_utils import _build_embedded_yaml
from .data_classes import RenderSubmitterUISettings


def build_tile_task_parameters(tiles_columns: int, tiles_rows: int) -> tuple[list[dict], str]:
    """
    Build the task parameter definitions and combination expression for tile rendering.

    Returns a tuple of (parameter_definitions, combination_expression) where
    parameter_definitions is a list of TileCol/TileRow INT parameter dicts and
    combination_expression is the parameterSpace combination string.
    """
    return (
        [
            {
                "name": "TileCol",
                "type": "INT",
                "range": f"0-{tiles_columns - 1}",
            },
            {
                "name": "TileRow",
                "type": "INT",
                "range": f"0-{tiles_rows - 1}",
            },
        ],
        "Frame * TileCol * TileRow",
    )


def build_assembly_step(
    render_step: dict[str, Any],
    settings: RenderSubmitterUISettings,
    output_path: str,
    multi_pass_path: str,
) -> dict[str, Any]:
    """Build a tile-assembly step that depends on the given render step."""
    # Only carry over the Frame parameter (first task param), not tile params
    frame_param = deepcopy(render_step["parameterSpace"]["taskParameterDefinitions"][0])

    return {
        "name": f"{render_step['name']} - Assemble Tiles",
        "dependencies": [{"dependsOn": render_step["name"]}],
        "parameterSpace": {"taskParameterDefinitions": [frame_param]},
        "stepEnvironments": deepcopy(render_step["stepEnvironments"]),
        "script": {
            "embeddedFiles": [
                {
                    "name": "runData",
                    "filename": "run-data.yaml",
                    "type": "TEXT",
                    "data": _build_embedded_yaml(
                        {
                            "frame": "{{Task.Param.Frame}}",
                            "tile_action": "assemble",
                            "total_tiles_column": settings.tiles_columns,
                            "total_tiles_row": settings.tiles_rows,
                            "output_path": output_path,
                            "multi_pass_path": multi_pass_path,
                        },
                        unquoted_keys={"output_path", "multi_pass_path"},
                    ),
                }
            ],
            "actions": deepcopy(render_step["script"]["actions"]),
        },
    }
