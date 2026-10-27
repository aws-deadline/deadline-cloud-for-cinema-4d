# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import importlib
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def child_module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    return importlib.import_module("test.integ.loopback_mock_child")


def test_loopback_bind_does_not_resolve_dns(child_module):
    server = object.__new__(child_module.LoopbackHTTPServer)
    server.socket = MagicMock()
    server.socket.getsockname.return_value = ("127.0.0.1", 48001)
    server.server_address = ("127.0.0.1", 0)
    server.allow_reuse_address = False
    server.allow_reuse_port = False

    with patch.object(socket, "getfqdn", side_effect=AssertionError("unexpected DNS lookup")):
        server.server_bind()

    server.socket.bind.assert_called_once_with(("127.0.0.1", 0))
    assert server.server_address == ("127.0.0.1", 48001)
    assert server.server_name == "127.0.0.1"
    assert server.server_port == 48001


def test_child_replaces_server_only_while_running(child_module):
    original = child_module.backend.ThreadingHTTPServer
    seen = []
    with patch.object(
        child_module,
        "run_mock",
        side_effect=lambda: seen.append(child_module.backend.ThreadingHTTPServer),
    ):
        child_module.main()

    assert seen == [child_module.LoopbackHTTPServer]
    assert child_module.backend.ThreadingHTTPServer is original


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.1"])
def test_mock_rejects_nonloopback_before_binding(child_module, host):
    server = object.__new__(child_module.LoopbackHTTPServer)
    server.socket = MagicMock()
    server.server_address = (host, 0)

    with pytest.raises(ValueError, match="must bind to IPv4 loopback"):
        server.server_bind()

    server.socket.bind.assert_not_called()
