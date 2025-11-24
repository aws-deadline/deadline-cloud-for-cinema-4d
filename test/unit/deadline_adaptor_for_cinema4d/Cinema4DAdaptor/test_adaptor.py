# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
from __future__ import annotations

# NOTE: All tests in this file use @pytest.mark.xdist_group(name="adaptor_tests")
# to run serially on the same worker. This is necessary because all tests share
# the same Cinema4DAdaptor action queue, which can cause race conditions and
# test failures when tests run in parallel across multiple workers.

import json
from pathlib import Path
from unittest.mock import Mock, PropertyMock, patch

import pytest
from jsonschema.exceptions import ValidationError

from deadline.cinema4d_adaptor.Cinema4DAdaptor import Cinema4DAdaptor
from deadline.cinema4d_adaptor._version import version as adaptor_version


REFERENCE_INIT_DATA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "scene_file": {"type": "string"},
        "take": {"type": "string"},
        "output_path": {"type": "string"},
        "multi_pass_path": {"type": "string"},
        "activate_error_checking": {"type": "string"},
        "use_cached_text": {"type": "string"},
    },
    "required": ["scene_file"],
}

REFERENCE_RUN_DATA_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {"frame": {"type": "number"}},
    "required": ["frame"],
}


@pytest.fixture
def init_data() -> dict:
    """
    Pytest Fixture to return an init_data dictionary that passes validation

    Returns:
        dict: An init_data dictionary
    """
    return {
        "scene_file": "C:\\Users\\user123\\test.c4d",
        "take": "Main",
        "output_path": "C:\\Users\\user123\\test_render",
        "multi_pass_path": "",
        "activate_error_checking": "1",
        "use_cached_text": "0",
    }


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_errors_on_cleanup:
    @pytest.mark.parametrize(
        "stdout,error_expected",
        [
            # Critical stops should not fail the job.
            ("CRITICAL: Stop [ge_file.cpp(1172)]", False),
            # Any string with substring "Error:" should fail the job
            ("Redshift Error: Maxon licensing error: User not logged in (7)", True),
            # This error can be printed but the jobs are still successful.
            # Hence, this should not fail the job.
            ("CRITICAL: nullptr [text_object.cpp(1082)] [objectbase1.hxx(549)]", False),
            ("Project not found", True),
            ("Error rendering project", True),
            ("Error loading project", True),
            ("Error rendering document", True),
            ("Error loading document", True),
            ("Rendering failed", True),
            ("Asset missing", True),
            ("Asset Error", True),
            ("Invalid License", True),
            ("License Check error", True),
            ("Files cannot be written", True),
            ("Enter Registration Data", True),
            ("Unable to write file", True),
            ("[rlm] abort_on_license_fail enabled", True),
            ("RenderDocument failed with return code", True),
            ("Frame rendering aborted", True),
            ("Rendering was internally aborted", True),
            ('Cannot find procedure "rsPreference"', True),
            ("Description Error: ainode_image is already registered", False),
        ],
    )
    def test_handle_errors_on_error_stdout(
        self, init_data: dict, stdout: str, error_expected: bool
    ) -> None:
        """Tests that the _handle_error method throws a error runtime error correctly"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        # Currently the callback for errors is at index 2
        error_regexes = regex_callbacks[2].regex_list

        # WHEN
        for regex in error_regexes:
            match = regex.search(stdout)
            if match:
                adaptor._handle_error(match)
                break

        # THEN
        if error_expected:
            assert match is not None
            assert str(adaptor._exc_info) == f"Cinema4D Encountered an Error: {stdout}"
        else:
            assert match is None

    @pytest.mark.parametrize(
        "stdout",
        [
            # Redshift errors should provide better message.
            ("Failed to allocate mem( 1045504 bytes)"),
        ],
    )
    def test_handle_insufficient_ram_on_stdout(self, init_data: dict, stdout: str) -> None:
        """Tests that the _handle_insufficient_ram method throws a error runtime error correctly"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)
        regex_callbacks = adaptor._get_regex_callbacks()
        # Currently the callback for insufficient RAM is at index 3
        regexes = regex_callbacks[3].regex_list

        # WHEN
        for regex in regexes:
            match = regex.search(stdout)
            if match:
                adaptor._handle_insufficient_ram(match)
                break

        # THEN
        assert match is not None
        assert str(adaptor._exc_info) == (
            "Redshift requires more RAM to render. "
            "Please increase the worker's RAM to at least double the worker's GPU VRAM. For more info: "
            "https://help.maxon.net/c4d/s26/de-de/Content/_REDSHIFT_/html/Dealing+with+Out-Of-RAM+situations.html. "
            f"Error: {stdout}"
        )


@pytest.mark.xdist_group(name="adaptor_tests")
def test_adaptor_rejects_malformed_init_data():
    adapter = Cinema4DAdaptor({"invalid": "data"})
    with pytest.raises(ValidationError):
        adapter.on_start()


@pytest.mark.xdist_group(name="adaptor_tests")
def test_adaptor_rejects_malformed_run_data(init_data: dict):
    adapter = Cinema4DAdaptor(init_data)
    with pytest.raises(ValidationError):
        adapter.on_run({"invalid": "data"})


@pytest.mark.xdist_group(name="adaptor_tests")
def test_if_init_data_and_run_data_schema_are_changed_schema_version_is_bumped(init_data):
    """
    Test to validate that if the init data or run data schema are changed, we also bump the
    integration_data_interface_version
    """
    # Expected version for these reference schemas
    EXPECTED_MAJOR = 0
    EXPECTED_MINOR = 3

    # Get the current version from the adaptor
    adapter = Cinema4DAdaptor(init_data)
    semantic_version = adapter.integration_data_interface_version

    # Obtain current schema files
    root_directory_path = Path(__file__).parent.parent.parent.parent.parent
    schema_path = root_directory_path.joinpath(
        "src", "deadline", "cinema4d_adaptor", "Cinema4DAdaptor", "schemas"
    )
    init_data_path = schema_path.joinpath("init_data.schema.json")
    run_data_path = schema_path.joinpath("run_data.schema.json")

    # Assert current schemas to reference schemas
    with init_data_path.open() as init_data_schema_file:
        init_data_schema = json.load(init_data_schema_file)
        assert (
            init_data_schema == REFERENCE_INIT_DATA_SCHEMA
        ), "If the init_data.schema.json is changed, the integration_data_interface_version must be bumped"

    with run_data_path.open() as run_data_schema_file:
        run_data_schema = json.load(run_data_schema_file)
        assert (
            run_data_schema == REFERENCE_RUN_DATA_SCHEMA
        ), "If the run_data.schema.json is changed, the integration_data_interface_version must be bumped"

    # Assert that the semantic version matches the expected version
    assert semantic_version.major == EXPECTED_MAJOR and semantic_version.minor == EXPECTED_MINOR, (
        f"Expected version {EXPECTED_MAJOR}.{EXPECTED_MINOR} but got "
        f"{semantic_version.major}.{semantic_version.minor}. When updating schemas, "
        "both the reference schemas AND the expected version should be updated together."
    )


@pytest.mark.xdist_group(name="adaptor_tests")
def test_adaptor_prints_version_on_init(init_data, capfd):
    """
    Test that the adaptor prints its version during initialization
    """
    Cinema4DAdaptor(init_data)
    captured = capfd.readouterr()
    expected_output = f"Deadline Cloud for Cinema 4D adaptor version: {adaptor_version}"
    assert (
        expected_output in captured.out
    ), f"Expected output to contain {expected_output}, but got {captured.out}"


@pytest.mark.xdist_group(name="adaptor_tests")
@pytest.mark.parametrize("activate_error_checking", [0, 1])
def test_activate_error_checking(init_data: dict, activate_error_checking: int) -> None:
    """
    Tests that the activate_error_checking configuration controls whether error-handling
    regex callbacks are included in the adaptor's callback list.

    When activate_error_checking=0 (deactivate): Error regexes should be absent
    When activate_error_checking=1 (activate): Error regexes should be present
    """
    # GIVEN:
    init_data["activate_error_checking"] = str(activate_error_checking)
    adaptor = Cinema4DAdaptor(init_data)
    # Manually set the private variable to fix timing issue (normally set in on_start())
    adaptor._activate_error_checking = activate_error_checking

    # WHEN:
    callbacks = adaptor._get_regex_callbacks()

    # THEN: Check if `error_regexes` corresponding callback is present based on configuration
    # `error_regexes` has the callback function called `_handle_error`.
    has_handle_error_callback = any(
        regex_callback.callback == adaptor._handle_error for regex_callback in callbacks
    )

    if activate_error_checking == 1:
        assert (
            has_handle_error_callback
        ), "Error checking should be activated when activate_error_checking=1"
    else:
        assert (
            not has_handle_error_callback
        ), "Error checking should be deactivated when activate_error_checking=0"


@pytest.fixture()
def run_data() -> dict:
    return {"frame": 42}


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_on_start:
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.AdaptorServer")
    def test_no_error(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        init_data: dict,
    ) -> None:
        """Tests that on_start completes without error"""
        adaptor = Cinema4DAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        adaptor.on_start()

    @patch("time.sleep")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.AdaptorServer")
    def test__wait_for_socket(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
    ) -> None:
        """Tests that the _wait_for_socket method sleeps until a socket is available"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)
        socket_mock = PropertyMock(
            side_effect=[None, None, None, "/tmp/9999", "/tmp/9999", "/tmp/9999"]
        )
        type(mock_server.return_value).server_path = socket_mock

        # WHEN
        adaptor.on_start()

        # THEN
        assert mock_sleep.call_count == 3


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_on_run:
    @patch("time.sleep")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.ActionsQueue.__len__", return_value=0)
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.LoggingSubprocess")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.AdaptorServer")
    def test_on_run(
        self,
        mock_server: Mock,
        mock_logging_subprocess: Mock,
        mock_actions_queue: Mock,
        mock_sleep: Mock,
        init_data: dict,
        run_data: dict,
    ) -> None:
        """Tests that on_run completes without error, and waits"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)
        mock_server.return_value.server_path = "/tmp/9999"
        # First side_effect value consumed by setter
        is_rendering_mock = PropertyMock(side_effect=[None, True, False])
        Cinema4DAdaptor._is_rendering = is_rendering_mock
        adaptor.on_start()

        # WHEN
        adaptor.on_run(run_data)

        # THEN
        mock_sleep.assert_called_once_with(0.1)


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_on_cleanup:
    @patch("time.sleep")
    @patch("deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor._logger")
    def test_on_cleanup_cinema4d_not_graceful_shutdown(
        self, mock_logger: Mock, mock_sleep: Mock, init_data: dict
    ) -> None:
        """Tests that on_cleanup reports when cinema4d does not gracefully shutdown"""
        # GIVEN
        adaptor = Cinema4DAdaptor(init_data)

        with (
            patch(
                "deadline.cinema4d_adaptor.Cinema4DAdaptor.adaptor.Cinema4DAdaptor._cinema4d_is_running",
                new_callable=lambda: True,
            ),
            patch.object(adaptor, "_CINEMA4D_END_TIMEOUT_SECONDS", 0.01),
            patch.object(adaptor, "_cinema4d_client") as mock_client,
        ):
            # WHEN
            adaptor.on_cleanup()

        # THEN
        mock_logger.error.assert_called_once_with(
            "Cinema4D did not complete cleanup actions and failed to gracefully shutdown. Terminating."
        )
        mock_client.terminate.assert_called_once()


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_on_cancel:
    """Tests for Cinema4DAdaptor.on_cancel"""

    def test_terminates_cinema4d_client(self, init_data: dict, caplog: pytest.LogCaptureFixture):
        """Tests that the cinema4d client is terminated on cancel"""
        # GIVEN
        caplog.set_level(0)
        adaptor = Cinema4DAdaptor(init_data)
        adaptor._cinema4d_client = mock_client = Mock()

        # WHEN
        adaptor.on_cancel()

        # THEN
        mock_client.terminate.assert_called_once_with(grace_time_s=0)
        assert "CANCEL REQUESTED" in caplog.text

    def test_does_nothing_if_cinema4d_not_running(
        self, init_data: dict, caplog: pytest.LogCaptureFixture
    ):
        """Tests that nothing happens if a cancel is requested when cinema4d is not running"""
        # GIVEN
        caplog.set_level(0)
        adaptor = Cinema4DAdaptor(init_data)
        adaptor._cinema4d_client = None

        # WHEN
        adaptor.on_cancel()

        # THEN
        assert "CANCEL REQUESTED" in caplog.text
        assert "Nothing to cancel because Cinema4D is not running" in caplog.text


@pytest.mark.xdist_group(name="adaptor_tests")
class TestCinema4DAdaptor_populate_action_queue:
    """Tests for Cinema4DAdaptor._populate_action_queue"""

    @pytest.fixture(autouse=True)
    def cleanup_action_queue(self):
        """Fixture to clean up the shared action queue before and after each test"""
        # Create a temporary adaptor to access the shared action queue
        temp_adaptor = Cinema4DAdaptor({"scene_file": "test.c4d"})

        # Clear the queue before the test
        while len(temp_adaptor._action_queue) > 0:
            temp_adaptor._action_queue.dequeue_action()

        yield

        # Clear the queue after the test
        while len(temp_adaptor._action_queue) > 0:
            temp_adaptor._action_queue.dequeue_action()

    def test_populate_action_queue_with_all_actions(self):
        """Tests that _populate_action_queue adds all available actions from init_data"""
        # GIVEN
        init_data_with_all_actions = {
            "scene_file": "test.c4d",
            "take": "Main",
            "output_path": "/output",
            "multi_pass_path": "/multipass",
            "use_cached_text": "1",
            "activate_error_checking": "1",
        }
        adaptor = Cinema4DAdaptor(init_data_with_all_actions)

        # WHEN
        adaptor._populate_action_queue()

        # THEN
        # Verify that all expected actions are in the queue
        actions = []
        while len(adaptor._action_queue) > 0:
            action = adaptor._action_queue.dequeue_action()
            if action:
                actions.append(action)

        action_names = [action.name for action in actions]
        assert "scene_file" in action_names
        assert "take" in action_names
        assert "output_path" in action_names
        assert "multi_pass_path" in action_names
        assert "use_cached_text" in action_names

        # Verify the order matches _FIRST_CINEMA4D_ACTIONS
        expected_order = ["scene_file", "take", "output_path", "multi_pass_path", "use_cached_text"]
        assert action_names == expected_order

    def test_populate_action_queue_with_use_cached_text(self, init_data: dict):
        """Tests that _populate_action_queue includes use_cached_text when present in init_data"""
        # GIVEN
        init_data["use_cached_text"] = "1"
        adaptor = Cinema4DAdaptor(init_data)

        # WHEN
        adaptor._populate_action_queue()

        # THEN
        actions = []
        while len(adaptor._action_queue) > 0:
            action = adaptor._action_queue.dequeue_action()
            if action:
                actions.append(action)

        # Find the use_cached_text action
        use_cached_text_action = next((a for a in actions if a.name == "use_cached_text"), None)
        assert use_cached_text_action is not None, "use_cached_text action should be in the queue"
        assert use_cached_text_action.args == {"use_cached_text": "1"}

    def test_populate_action_queue_without_use_cached_text(self):
        """Tests that _populate_action_queue works when use_cached_text is not in init_data"""
        # GIVEN
        init_data_without_use_cached_text = {
            "scene_file": "test.c4d",
            "take": "Main",
            "activate_error_checking": "1",
        }
        adaptor = Cinema4DAdaptor(init_data_without_use_cached_text)

        # WHEN
        adaptor._populate_action_queue()

        # THEN
        actions = []
        while len(adaptor._action_queue) > 0:
            action = adaptor._action_queue.dequeue_action()
            if action:
                actions.append(action)

        action_names = [action.name for action in actions]
        assert "use_cached_text" not in action_names
        assert "scene_file" in action_names
        assert "take" in action_names

    def test_populate_action_queue_only_includes_first_actions(self):
        """Tests that _populate_action_queue only includes actions from _FIRST_CINEMA4D_ACTIONS"""
        # GIVEN
        init_data_with_extra = {
            "scene_file": "test.c4d",
            "take": "Main",
            "use_cached_text": "0",
            "activate_error_checking": "1",
            "frame": 42,  # This is a run action, not an init action
            "extra_field": "should_not_be_included",
        }
        adaptor = Cinema4DAdaptor(init_data_with_extra)

        # WHEN
        adaptor._populate_action_queue()

        # THEN
        actions = []
        while len(adaptor._action_queue) > 0:
            action = adaptor._action_queue.dequeue_action()
            if action:
                actions.append(action)

        action_names = [action.name for action in actions]
        # Should only include actions from _FIRST_CINEMA4D_ACTIONS
        assert "scene_file" in action_names
        assert "take" in action_names
        assert "use_cached_text" in action_names
        # Should NOT include run actions or extra fields
        assert "frame" not in action_names
        assert "extra_field" not in action_names
        assert "activate_error_checking" not in action_names

    def test_populate_action_queue_with_minimal_init_data(self):
        """Tests that _populate_action_queue works with minimal init_data (only scene_file)"""
        # GIVEN
        minimal_init_data = {
            "scene_file": "test.c4d",
        }
        adaptor = Cinema4DAdaptor(minimal_init_data)

        # WHEN
        adaptor._populate_action_queue()

        # THEN
        actions = []
        while len(adaptor._action_queue) > 0:
            action = adaptor._action_queue.dequeue_action()
            if action:
                actions.append(action)

        action_names = [action.name for action in actions]
        assert action_names == ["scene_file"]
        assert len(actions) == 1
