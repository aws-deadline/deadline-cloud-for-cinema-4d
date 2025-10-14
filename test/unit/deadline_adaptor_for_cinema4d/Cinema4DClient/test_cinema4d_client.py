# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import os
from unittest.mock import Mock, patch
import pytest
from openjd.adaptor_runtime_client import (
    PathMappingRule,
)
from deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client import Cinema4DClient, main


class TestCinema4DClient:
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.ClientInterface")
    def test_cinema4dclient(self, mock_httpclient: Mock) -> None:
        """Tests that the cinema4d client can initialize, set a take and close"""
        client = Cinema4DClient(server_path=str(9999))
        with patch("sys.exit") as mock_exit:
            client.close()
        mock_exit.assert_called_once_with(0)

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.ClientInterface")
    def test_graceful_shutdown(self, mock_httpclient: Mock) -> None:
        """Tests that the cinema4d client can initialize, set a take and close"""
        client = Cinema4DClient(server_path=str(9999))
        with patch("sys.exit") as mock_exit:
            client.graceful_shutdown(0, None)
        mock_exit.assert_called_once_with(0)

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.os.path.exists")
    @patch.dict(os.environ, {"CINEMA4D_ADAPTOR_SERVER_PATH": "server_path"})
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.Cinema4DClient.poll")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.ClientInterface")
    def test_main(self, mock_httpclient: Mock, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method starts the cinema4d client polling method"""
        # GIVEN
        mock_exists.return_value = True

        # WHEN
        main()

        # THEN
        mock_exists.assert_called_once_with("server_path")
        mock_poll.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.Cinema4DClient.poll")
    def test_main_no_server_socket(self, mock_poll: Mock) -> None:
        """Tests that the main method raises an OSError if no server socket is found"""
        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        assert str(exc_info.value) == (
            "Cinema4DClient cannot connect to the Adaptor because the environment variable "
            "CINEMA4D_ADAPTOR_SERVER_PATH does not exist"
        )
        mock_poll.assert_not_called()

    @patch.dict(os.environ, {"CINEMA4D_ADAPTOR_SERVER_PATH": "/a/path/that/does/not/exist"})
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.os.path.exists")
    @patch("deadline.cinema4d_adaptor.Cinema4DClient.Cinema4DClient.poll")
    def test_main_server_socket_not_exists(self, mock_poll: Mock, mock_exists: Mock) -> None:
        """Tests that the main method raises an OSError if the server socket does not exist"""
        # GIVEN
        mock_exists.return_value = False

        # WHEN
        with pytest.raises(OSError) as exc_info:
            main()

        # THEN
        mock_exists.assert_called_once_with(os.environ["CINEMA4D_ADAPTOR_SERVER_PATH"])
        assert str(exc_info.value) == (
            "Cinema4DClient cannot connect to the Adaptor because the socket at the path defined by "
            "the environment variable CINEMA4D_ADAPTOR_SERVER_PATH does not exist. Got: "
            f"{os.environ['CINEMA4D_ADAPTOR_SERVER_PATH']}"
        )
        mock_poll.assert_not_called()

    def test_empty_map_path(self):
        client = Cinema4DClient(server_path="/tmp/9999")
        with pytest.raises(ValueError):
            client.map_path("")

    @patch("openjd.adaptor_runtime_client.base_client_interface.BaseClientInterface.map_path")
    def test_map_path(self, mock_map_path: Mock):
        mock_map_path.return_value = "test"
        client = Cinema4DClient(server_path="/tmp/9999")
        assert client.map_path("test") == "test"

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.sys.platform")
    @patch("openjd.adaptor_runtime_client.base_client_interface.BaseClientInterface.map_path")
    @patch(
        "openjd.adaptor_runtime_client.base_client_interface.BaseClientInterface.path_mapping_rules"
    )
    def test_map_path_win(self, mock_rules: Mock, mock_map_path: Mock, mock_platform: Mock):
        mock_rules.return_value = None
        mock_map_path.return_value = "C:/test"
        mock_platform.return_value = "win"
        client = Cinema4DClient(server_path="/tmp/9999")
        assert client.map_path("test") == "C:/test"

    @patch("deadline.cinema4d_adaptor.Cinema4DClient.cinema4d_client.sys.platform")
    @patch("openjd.adaptor_runtime_client.base_client_interface.BaseClientInterface.map_path")
    @patch(
        "openjd.adaptor_runtime_client.base_client_interface.BaseClientInterface.path_mapping_rules"
    )
    def test_map_path_rules(self, mock_rules: Mock, mock_map_path: Mock, mock_platform: Mock):
        rules = PathMappingRule(
            source_path_format="windows",
            source_path="some",
            destination_os="Windows",
            destination_path="C:/Some",
        )
        mock_rules.return_value = rules
        mock_map_path.return_value = "C:/Some"
        mock_platform.return_value = "win"
        client = Cinema4DClient(server_path="/tmp/9999")
        assert client.map_path("some") == "C:/Some"
