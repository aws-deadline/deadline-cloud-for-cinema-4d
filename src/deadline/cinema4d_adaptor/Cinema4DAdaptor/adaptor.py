# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import logging
import os
import platform
import re
import sys
import threading
import time
from functools import wraps
from typing import Callable

from openjd.adaptor_runtime.adaptors import Adaptor, AdaptorDataValidators, SemanticVersion
from openjd.adaptor_runtime.adaptors.configuration import AdaptorConfiguration
from openjd.adaptor_runtime.app_handlers import RegexCallback, RegexHandler
from openjd.adaptor_runtime.application_ipc import ActionsQueue, AdaptorServer
from openjd.adaptor_runtime.process import LoggingSubprocess
from openjd.adaptor_runtime_client import Action

_logger = logging.getLogger(__name__)


class Cinema4DNotRunningError(Exception):
    """Error that is raised when attempting to use Cinema4D while it is not running"""


_FIRST_CINEMA4D_ACTIONS = ["scene_file", "take", "output_path", "multi_pass_path"]
_CINEMA4D_RUN_KEYS = {
    "frame",
}


def _check_for_exception(func: Callable) -> Callable:
    """
    Decorator that checks if an exception has been caught before calling the
    decorated function
    """

    @wraps(func)
    def wrapped_func(self, *args, **kwargs):
        if not self._has_exception:  # Raises if there is an exception  # pragma: no branch
            return func(self, *args, **kwargs)

    return wrapped_func


class Cinema4DAdaptor(Adaptor[AdaptorConfiguration]):
    """
    Adaptor that creates a session in Cinema4D to Render interactively.
    """

    _SERVER_START_TIMEOUT_SECONDS = 30
    _SERVER_END_TIMEOUT_SECONDS = 30
    _CINEMA4D_START_TIMEOUT_SECONDS = 300
    _CINEMA4D_END_TIMEOUT_SECONDS = 30

    _server: AdaptorServer | None = None
    _server_thread: threading.Thread | None = None
    _cinema4d_client: LoggingSubprocess | None = None
    _action_queue = ActionsQueue()
    _is_rendering: bool = False
    # If a thread raises an exception we will update this to raise in the main thread
    _exc_info: Exception | None = None
    _performing_cleanup = False
    _regex_callbacks: list | None = None
    _validators: AdaptorDataValidators | None = None

    # Variables used for keeping track of produced outputs for progress reporting.
    # Will be optionally changed after the scene is set.
    _expected_outputs: int = 1  # Total number of renders to perform.
    _produced_outputs: int = 0  # Counter for tracking number of complete renders.

    def __init__(self, *args, **kwargs):
        if sys.platform == "linux" and "path_mapping_data" in kwargs:
            # on Linux, Cinema4D interprets Windows absolute paths as relative paths
            # e.g. `C:\Users\test-user\Documents\file.bmp` becomes
            # `./C:/Users/test-user/Documents/file.bmp`
            # To map these paths with job attachments, we duplicate any existing Windows path mapping
            # and then add a `./` prefix to it so that it converts correctly on Linux
            path_mapping_data = kwargs["path_mapping_data"] or {}
            path_mapping_rules = path_mapping_data.get("path_mapping_rules", [])
            for rule in path_mapping_rules.copy():
                source_path_format = rule.get("source_path_format", "")
                # if there is no destination_os, the rule applies
                destination_os = rule.get("destination_os", "linux")
                if source_path_format.lower().startswith(
                    "win"
                ) and destination_os.lower().startswith("linux"):
                    prefixed_rule = {
                        "source_path": f"./{rule['source_path']}",
                        "source_path_format": source_path_format,
                        "destination_path": rule["destination_path"],
                    }
                    if "destination_os" in rule:
                        prefixed_rule["destination_os"] = rule["destination_os"]
                    path_mapping_rules.append(prefixed_rule)
        super().__init__(*args, **kwargs)

    @property
    def integration_data_interface_version(self) -> SemanticVersion:
        return SemanticVersion(major=0, minor=1)

    @staticmethod
    def _get_timer(timeout: int | float) -> Callable[[], bool]:
        """
        Given a timeout length, returns a lambda which returns False until the timeout occurs.

        Args:
            timeout (int): The amount of time (in seconds) to wait before timing out.
        """
        timeout_time = time.time() + timeout
        return lambda: time.time() >= timeout_time

    @property
    def _has_exception(self) -> bool:
        """Property which checks the private _exc_info property for an exception

        Raises:
            self._exc_info: An exception if there is one

        Returns:
            bool: False there is no exception waiting to be raised
        """
        if self._exc_info and not self._performing_cleanup:
            raise self._exc_info
        return False

    @property
    def _cinema4d_is_running(self) -> bool:
        """Property which indicates that the cinema4d client is running

        Returns:
            bool: True if the cinema4d client is running, false otherwise
        """
        return self._cinema4d_client is not None and self._cinema4d_client.is_running

    @property
    def _cinema4d_is_rendering(self) -> bool:
        """Property which indicates if cinema4d is rendering

        Returns:
            bool: True if cinema4d is rendering, false otherwise
        """
        return self._cinema4d_is_running and self._is_rendering

    @_cinema4d_is_rendering.setter
    def _cinema4d_is_rendering(self, value: bool) -> None:
        """Property setter which updates the private _is_rendering boolean.

        Args:
            value (bool): A boolean indicating if cinema4d is rendering.
        """
        self._is_rendering = value

    def _wait_for_socket(self) -> str:
        """
        Performs a busy wait for the socket path that the adaptor server is running on, then
        returns it.

        Raises:
            RuntimeError: If the server does not finish initializing

        Returns:
            str: The socket path the adaptor server is running on.
        """
        is_timed_out = self._get_timer(self._SERVER_START_TIMEOUT_SECONDS)
        while (self._server is None or self._server.server_path is None) and not is_timed_out():
            time.sleep(0.01)

        if self._server is not None and self._server.server_path is not None:
            return self._server.server_path

        raise RuntimeError("Could not find a socket because the server did not finish initializing")

    def _start_cinema4d_server(self) -> None:
        """
        Starts a server with the given ActionsQueue, attaches the server to the adaptor and serves
        forever in a blocking call.
        """
        self._server = AdaptorServer(self._action_queue, self)
        self._server.serve_forever()

    def _initialize_maxon_assets_db_connection(self) -> None:
        """
        When starting `Commandline.exe` the first time on Windows, Cinema 4D sometimes has the following error:
        ```
        sslConnection.DoHandShake failed while connecting to https://assets.maxon.net/assets/MaxonAssets.db/_index/modified.dat:
            SSL_do_handshake returned error: SSL_ERROR_SSL (certificate verify failed Certificate Information: not available)
        ```
        This indicates that a secure connection was not able to be made to the Maxon assets DB, so Cinema 4D
        did not connect to it at all. (i.e. it only connects if the connection is secure)

        However, Cinema 4D appears to quit prematurely the first time because on subsequent retries, the secure
        handshake will succeed.

        To prevent this from occurring, we pre-emptively initialize the connection.

        The Maxon assets DB is used to pull in assets from Maxon and if outdated, recently released assets may not be
        available.
        """
        if sys.platform in ["win32", "cygwin"]:
            _logger.info("Initializing the Maxon assets DB connection")
            curl_subprocess = LoggingSubprocess(
                args=["curl", "https://assets.maxon.net/assets/MaxonAssets.db/_index/modified.dat"]
            )
            # Note that if curl has an error, this will not re-raise the error. This is intended because updating the
            # asset database does not affect rendering in most cases and there is NO security risk if it has an error.
            curl_subprocess.wait()

    def _start_cinema4d_server_thread(self) -> None:
        """
        Starts the cinema4d adaptor server in a thread.
        Sets the environment variable "CINEMA4D_ADAPTOR_SERVER_PATH" to
        the socket the server is running
        on after the server has finished starting.
        """
        self._server_thread = threading.Thread(
            target=self._start_cinema4d_server, name="Cinema4DAdaptorServerThread"
        )
        self._server_thread.start()
        os.environ["CINEMA4D_ADAPTOR_SERVER_PATH"] = self._wait_for_socket()

    @property
    def validators(self) -> AdaptorDataValidators:
        if not self._validators:
            cur_dir = os.path.dirname(__file__)
            schema_dir = os.path.join(cur_dir, "schemas")
            self._validators = AdaptorDataValidators.for_adaptor(schema_dir)
        return self._validators

    def _get_regex_callbacks(self) -> list[RegexCallback]:
        """
        Returns a list of RegexCallbacks used by the Cinema4D Adaptor

        Returns:
            list[RegexCallback]: List of Regex Callbacks to add
        """
        if not self._regex_callbacks:
            callback_list = []

            completed_regexes = [re.compile(".*Finished Rendering.*")]
            callback_list.append(RegexCallback(completed_regexes, self._handle_complete))

            progress_regexes = [re.compile(".*Progress ([0-9]+)%.*")]
            callback_list.append(RegexCallback(progress_regexes, self._handle_progress))

            error_regexes = [
                re.compile(r".*Document not found.*", re.IGNORECASE),
                re.compile(r".*Project not found.*", re.IGNORECASE),
                re.compile(r".*Error rendering project.*", re.IGNORECASE),
                re.compile(r".*Error loading project.*", re.IGNORECASE),
                re.compile(r".*Error rendering document.*", re.IGNORECASE),
                re.compile(r".*Error loading document.*", re.IGNORECASE),
                re.compile(r".*Rendering failed.*", re.IGNORECASE),
                re.compile(r".*Asset missing.*", re.IGNORECASE),
                re.compile(r".*Asset Error.*", re.IGNORECASE),
                re.compile(r".*Invalid License.*", re.IGNORECASE),
                re.compile(r".*licensing error.*", re.IGNORECASE),
                re.compile(r".*License Check error.*", re.IGNORECASE),
                re.compile(r".*Files cannot be written.*", re.IGNORECASE),
                re.compile(r".*Enter Registration Data.*", re.IGNORECASE),
                re.compile(r".*Unable to write file.*", re.IGNORECASE),
                re.compile(r".*\[rlm\] abort_on_license_fail enabled.*", re.IGNORECASE),
                re.compile(r".*RenderDocument failed with return code.*", re.IGNORECASE),
                re.compile(r".*Frame rendering aborted.*", re.IGNORECASE),
                re.compile(r".*Rendering was internally aborted.*", re.IGNORECASE),
                re.compile(r'.*Cannot find procedure "rsPreference".*', re.IGNORECASE),
            ]
            callback_list.append(RegexCallback(error_regexes, self._handle_error))

            insufficient_ram_regexes = re.compile(r".*Failed to allocate mem.*", re.IGNORECASE)
            callback_list.append(
                RegexCallback(
                    [re.compile(insufficient_ram_regexes)],
                    self._handle_insufficient_ram,
                )
            )

            self._regex_callbacks = callback_list
        return self._regex_callbacks

    def _handle_logging(self, match: re.Match) -> None:
        print(match.group(0))

    @_check_for_exception
    def _handle_complete(self, match: re.Match) -> None:
        """
        Callback for stdout that indicate completeness of a render. Updates progress to 100
        Args:
            match (re.Match): The match object from the regex pattern that was matched in the
                              message.
        """
        self._cinema4d_is_rendering = False
        self.update_status(progress=100)

    @_check_for_exception
    def _handle_progress(self, match: re.Match) -> None:
        """
        Callback for stdout that indicate progress of a render.
        Args:
            match (re.Match): The match object from the regex pattern that was matched in the
                              message.
        """
        text = match.group(0)
        loc = text.index("ALF_PROGRESS ") + len("ALF_PROGRESS ")
        percent = text[loc : loc + 2]
        # check for % in case of single digit progress
        percent = percent[0] if percent.endswith("%") else percent
        progress = int(percent)
        self.update_status(progress=progress)

    def _handle_error(self, match: re.Match) -> None:
        """
        Callback for stdout that indicates an error or warning.
        Args:
            match (re.Match): The match object from the regex pattern that was matched in the
                              message

        Raises:
            RuntimeError: Always raises a runtime error to halt the adaptor.
        """
        self._exc_info = RuntimeError(f"Cinema4D Encountered an Error: {match.group(0)}")

    def _handle_insufficient_ram(self, match: re.Match) -> None:
        """
        Handle insufficient RAM errors during Redshift rendering.

        Args:
            match (re.Match): The match object containing the failed memory allocation size

        Raises:
            RuntimeError: Raised when RAM allocation fails
        """
        message = (
            "Redshift requires more RAM to render. "
            "Please increase the worker's RAM to at least double the worker's GPU VRAM. For more info: "
            "https://help.maxon.net/c4d/s26/de-de/Content/_REDSHIFT_/html/Dealing+with+Out-Of-RAM+situations.html. "
            f"Error: {match.group(0)}"
        )

        self._exc_info = RuntimeError(message)

    def _add_deadline_openjd_paths(self) -> None:
        # Add the openjd namespace directory to PYTHONPATH, so that adaptor_runtime_client
        # will be available directly to the adaptor client.
        import deadline.cinema4d_adaptor
        import openjd.adaptor_runtime_client

        openjd_namespace_dir = os.path.dirname(
            os.path.dirname(openjd.adaptor_runtime_client.__file__)
        )
        deadline_namespace_dir = os.path.dirname(
            os.path.dirname(deadline.cinema4d_adaptor.__file__)
        )
        python_path_addition = f"{openjd_namespace_dir}{os.pathsep}{deadline_namespace_dir}"
        if "C4DPYTHONPATH311" in os.environ:
            os.environ["C4DPYTHONPATH311"] = (
                f"{os.environ['C4DPYTHONPATH311']}{os.pathsep}{python_path_addition}"
            )
        else:
            os.environ["C4DPYTHONPATH311"] = python_path_addition

    def _start_cinema4d_client(self) -> None:
        """
        Starts the cinema4d client by launching Cinema4D with the cinema4d_client.py file.

        Raises:
            FileNotFoundError: If the cinema4d_client.py file or the scene file could not be found.
        """
        # XXX: on linux we need to run the c4d env setup script first, this env
        # var allows us to use a wrapper around Commandline. Ideally a conda env
        # does this for us.
        # On Linux this should be a path similar to this: /opt/maxon/cinema4dr2024.200/bin/Commandline
        # On Windows it should be a path similar to this: "C:\Program Files\Maxon Cinema 4D R26\Commandline.exe"
        c4d_exe_env = os.environ.get("C4D_COMMANDLINE_EXECUTABLE", "")
        if not c4d_exe_env:
            c4d_exe = "Commandline"
        else:
            c4d_exe = c4d_exe_env
        regexhandler = RegexHandler(self._get_regex_callbacks())

        # If there are path mapping rules, set the cinema4d environment variable to enable them
        cinema4d_pathmap = self._get_cinema4d_pathmap()
        if cinema4d_pathmap:
            os.environ["CINEMA4D_PATHMAP"] = cinema4d_pathmap

        _logger.info(f"Setting CINEMA4D_PATHMAP to: {cinema4d_pathmap}")

        # set plugin path to DeadlineCloudClient
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        client_dir = os.path.join(parent_dir, "Cinema4DClient")
        plugin_dir = os.path.join(client_dir, "plugin")
        module_path_key = "g_additionalModulePath"
        module_path = os.getenv(module_path_key)
        if not module_path:
            new_module_path = plugin_dir
        else:
            new_module_path = plugin_dir + os.pathsep + module_path
        os.environ[module_path_key] = new_module_path

        arguments = [c4d_exe, "-nogui", "-DeadlineCloudClient"]
        # If this is a Redshift render, we would want to emit at least error logs
        # For non-Redshift renders this does not print any extra information.
        arguments.extend(["-redshift-log-console", "Error"])
        if "linux" in platform.system().lower():
            _logger.info("Inserting Linux adaptor wrapper script")
            arguments.insert(0, os.path.join(os.path.dirname(__file__), "adaptor.sh"))

        self._add_deadline_openjd_paths()

        self._cinema4d_client = LoggingSubprocess(
            args=arguments,
            stdout_handler=regexhandler,
            stderr_handler=regexhandler,
        )

    def _get_cinema4d_pathmap(self) -> str:
        """Builds a dict of source to destination strings from the path mapping rules

        The string representation of the dict can then be used to set CINEMA4D_PATHMAP

        Returns:
            str: The value to set CINEMA4D_PATHMAP to
        """
        path_mapping_rules: dict[str, str] = {}

        for rule in self._path_mapping_rules:
            path_mapping_rules[rule.source_path] = rule.destination_path

        if path_mapping_rules:
            return str(path_mapping_rules)
        return ""

    def on_start(self) -> None:
        """
        For job stickiness. Will start everything required for the Task. Will be used for all
        SubTasks.

        Raises:
            jsonschema.ValidationError: When init_data fails validation against the adaptor schema.
            jsonschema.SchemaError: When the adaptor schema itself is nonvalid.
            RuntimeError: If Cinema4D did not complete initialization actions due to an exception
            TimeoutError: If Cinema4D did not complete initialization actions due to timing out.
            FileNotFoundError: If the cinema4d_client.py file could not be found.
            KeyError: If a configuration for the given platform and version does not exist.
        """
        self.validators.init_data.validate(self.init_data)

        self.update_status(progress=0, status_message="Initializing Cinema4D")
        self._initialize_maxon_assets_db_connection()
        self._start_cinema4d_server_thread()
        self._populate_action_queue()
        self._start_cinema4d_client()

        is_timed_out = self._get_timer(self._CINEMA4D_START_TIMEOUT_SECONDS)
        while self._cinema4d_is_running and not self._has_exception and len(self._action_queue) > 0:
            if is_timed_out():
                raise TimeoutError(
                    "Cinema4D did not complete initialization actions in "
                    f"{self._CINEMA4D_START_TIMEOUT_SECONDS} seconds and failed to start."
                )

            time.sleep(0.1)  # busy wait for cinema4d to finish initialization

        if len(self._action_queue) > 0:
            raise RuntimeError(
                "Cinema4D encountered an error and was not able to complete initialization actions."
            )

    def on_run(self, run_data: dict) -> None:
        """
        This starts a render in Cinema4D for the given frame, scene and layer(s) and
        performs a busy wait until the render completes.
        """

        self.validators.run_data.validate(run_data)

        if not self._cinema4d_is_running:
            raise Cinema4DNotRunningError("Cannot render because Cinema4D is not running.")

        run_data["frame"] = int(run_data["frame"])
        self._is_rendering = True

        for name in _CINEMA4D_RUN_KEYS:
            if name in run_data:
                self._action_queue.enqueue_action(Action(name, {name: run_data[name]}))

        self._action_queue.enqueue_action(Action("start_render", {"frame": run_data["frame"]}))

        while self._cinema4d_is_rendering and not self._has_exception:
            time.sleep(0.1)  # busy wait so that on_cleanup is not called

        if (
            not self._cinema4d_is_running and self._cinema4d_client
        ):  # Client will always exist here.
            #  This is always an error case because the Cinema4D Client should still be running and
            #  waiting for the next command. If the thread finished, then we cannot continue
            exit_code = self._cinema4d_client.returncode
            raise Cinema4DNotRunningError(
                "Cinema4D exited early and did not render successfully, please check render logs. "
                f"Exit code {exit_code}"
            )

    def on_stop(self) -> None:
        """ """
        self._action_queue.enqueue_action(Action("close"), front=True)

    def on_cleanup(self):
        """
        Cleans up the adaptor by closing the Cinema4D client and adaptor server.
        """
        self._performing_cleanup = True

        self._action_queue.enqueue_action(Action("close"), front=True)
        is_timed_out = self._get_timer(self._CINEMA4D_END_TIMEOUT_SECONDS)
        while self._cinema4d_is_running and not is_timed_out():
            time.sleep(0.1)
        if self._cinema4d_is_running and self._cinema4d_client:
            _logger.error(
                "Cinema4D did not complete cleanup actions and failed to gracefully shutdown. "
                "Terminating."
            )
            self._cinema4d_client.terminate()

        if self._server:
            self._server.shutdown()

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=self._SERVER_END_TIMEOUT_SECONDS)
            if self._server_thread.is_alive():
                _logger.error("Failed to shutdown the Cinema4D Adaptor server.")

        self._performing_cleanup = False

    def on_cancel(self):
        """
        Cancels the current render if Cinema4D is rendering.
        """
        _logger.info("CANCEL REQUESTED")
        if not self._cinema4d_client or not self._cinema4d_is_running:
            _logger.info("Nothing to cancel because Cinema4D is not running")
            return

        self._cinema4d_client.terminate(grace_time_s=0)

    def _populate_action_queue(self) -> None:
        """
        Populates the adaptor server's action queue with actions from the init_data that the Cinema4D
        Client will request and perform. The action must be present in the _FIRST_CINEMA4D_ACTIONS
        set to be added to the action queue.
        """
        for name in _FIRST_CINEMA4D_ACTIONS:
            if name in self.init_data:
                self._action_queue.enqueue_action(Action(name, {name: self.init_data[name]}))
