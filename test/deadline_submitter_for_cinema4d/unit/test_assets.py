# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations
from unittest.mock import patch

from deadline.cinema4d_submitter.assets import AssetIntrospector


@patch("c4d.documents.GetAllAssetsNew", return_value={"filename": "/foo.png", "exists": True})
def test_parse_scene_assets(f1):
    a = AssetIntrospector()
    assets = a.parse_scene_assets()
    assert assets is not None
    assert len(assets) == 1
