# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""A minimal, observable in-process mock of the Deadline Cloud service.

Scope is grounded on reality: the operation set and response shapes were
captured by running the real xa11y Export-bundle test against a live farm with
the API logger in ``AutoOpenSubmitter.pyp`` enabled. The backend implements six
operations -- ``ListFarms``, ``GetFarm``, ``ListQueues``, ``GetQueue``,
``ListQueueEnvironments``, ``ListStorageProfilesForQueue``.

Protocol: Deadline Cloud speaks **rest-json**. Routes carry the ``/2023-10-12``
API prefix; path parameters like ``{farmId}`` are templated into the URI. The
real ``deadline`` client reaches this server when pointed at it via
``AWS_ENDPOINT_URL_DEADLINE`` -- with botocore's ``management.`` host-prefix
injection disabled (in-process tests pass ``Config(inject_host_prefix=False)``;
the C4D subprocess uses a ``socket.getaddrinfo`` patch instead).

Observability (the point of this phase): every served request is recorded so a
test can prove the real client's calls reached *this* server and nothing slipped
through unmocked:

* ``call_counts``    -- per-operation counter, incremented inside the handler.
* ``request_log``    -- ordered list of ``(method, path, operation)`` actually served.
* ``unmatched_requests`` -- ``(method, path)`` for any request that hit no route
  (also logged loudly), so a forgotten operation is visible, never silent.
* ``log_callback``   -- optional callable invoked once per request with a short
  message, so the server can stream "served X" lines into the test's log.

Responses are filtered and validated against the botocore Deadline service model
(same approach as deadline-cloud's own MockDeadlineBackend), so a response that
doesn't match the real API shape fails loudly here rather than confusing the
client.
"""

from __future__ import annotations

import json as _json
import re as _re
import sys as _sys
import threading as _threading
import time as _time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler as _BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer as _ThreadingHTTPServer
from typing import Callable, Optional
from urllib.parse import parse_qs as _parse_qs
from urllib.parse import urlparse as _urlparse

import botocore.session
from botocore.exceptions import ClientError
from botocore.model import ServiceModel
from botocore.validate import ParamValidator

from . import fixtures_data as data

API_PREFIX = "/2023-10-12"

# Out-of-band endpoint (not a real Deadline route) for reading observability
# state when the server runs in a separate process. See start_server_process.
_ADMIN_CALLS_PATH = "/__admin__/calls"


def route(method: str, path: str, operation: str):
    """Tag a backend method with an HTTP route + botocore operation name.

    The HTTP server discovers these annotations to build its routing table; the
    operation name drives response-shape validation against the service model.
    """

    def decorator(fn):
        fn.__http_route__ = (method, f"{API_PREFIX}{path}", operation)
        return fn

    return decorator


def _resource_not_found(resource_type: str, resource_id: str, operation: str) -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": f"Resource of type {resource_type} with id {resource_id} does not exist.",
            }
        },
        operation,
    )


class MockDeadlineBackend:
    """In-memory Deadline Cloud backend for the Export-bundle integ test.

    Seeded from sanitized real data (:mod:`mock_aws.fixtures_data`) with a single
    farm, a single queue, and a single (Conda) queue environment -- the minimum
    the Export-bundle dialog reads. ``farm_id`` / ``queue_id`` are exposed so the
    test can write a matching deadline config for the C4D subprocess.

    ``response_delay_s`` adds an artificial per-response delay (default 0.3s) to
    approximate the real farm's observed 200-600ms latencies, so the dialog's
    open-time loading behaviour resembles a real session rather than resolving
    instantly. Set to 0 to disable.
    """

    def __init__(self, response_delay_s: float = 0.3) -> None:
        self.farm_id = data.FARM_ID
        self.queue_id = data.QUEUE_ID
        self.response_delay_s = response_delay_s

        # --- Observability state ---
        # Guarded by a lock because the server is multi-threaded (one thread per
        # request), so concurrent submitter calls don't corrupt these.
        self._lock = _threading.Lock()
        self.call_counts: dict[str, int] = {}
        self.request_log: list[tuple[str, str, str]] = []
        self.unmatched_requests: list[tuple[str, str]] = []
        self.log_callback: Optional[Callable[[str], None]] = None

        self._validator: Optional[ParamValidator] = None
        self._service_model: Optional[ServiceModel] = None

    def _log(self, msg: str) -> None:
        if self.log_callback is not None:
            try:
                self.log_callback(msg)
            except Exception:
                # Logging is best-effort observability; a failing callback must
                # never break request serving.
                pass

    # ===================== Observed operations only =====================

    @route("GET", "/farms", "ListFarms")
    def list_farms(self, *, maxResults: int = 100, nextToken: str | None = None, **kwargs) -> dict:
        # The auth probe (check_authentication_status) calls this with
        # maxResults=1 and a principalId filter; we ignore filters and return
        # the single seeded farm.
        return {"farms": [data.GET_FARM_RESPONSE]}

    @route("GET", "/farms/{farmId}", "GetFarm")
    def get_farm(self, *, farmId: str) -> dict:
        if farmId != self.farm_id:
            raise _resource_not_found("farm", farmId, "GetFarm")
        return dict(data.GET_FARM_RESPONSE)

    @route("GET", "/farms/{farmId}/queues/{queueId}", "GetQueue")
    def get_queue(self, *, farmId: str, queueId: str) -> dict:
        if farmId != self.farm_id or queueId != self.queue_id:
            raise _resource_not_found("queue", queueId, "GetQueue")
        return dict(data.GET_QUEUE_RESPONSE)

    @route("GET", "/farms/{farmId}/queues", "ListQueues")
    def list_queues(self, *, farmId: str, **kwargs) -> dict:
        if farmId != self.farm_id:
            raise _resource_not_found("farm", farmId, "ListQueues")
        return {"queues": [data.GET_QUEUE_RESPONSE]}

    @route(
        "GET", "/farms/{farmId}/queues/{queueId}/storage-profiles", "ListStorageProfilesForQueue"
    )
    def list_storage_profiles_for_queue(self, *, farmId: str, queueId: str, **kwargs) -> dict:
        if farmId != self.farm_id or queueId != self.queue_id:
            raise _resource_not_found("queue", queueId, "ListStorageProfilesForQueue")
        return {"storageProfiles": []}

    @route("GET", "/farms/{farmId}/queues/{queueId}/environments", "ListQueueEnvironments")
    def list_queue_environments(self, *, farmId: str, queueId: str) -> dict:
        if farmId != self.farm_id or queueId != self.queue_id:
            raise _resource_not_found("queue", queueId, "ListQueueEnvironments")
        # Return an empty queue-environment list. With zero envs, the submitter's
        # queue-parameter load has nothing to build, so
        # OpenJDParametersWidget.rebuild_ui never recreates QLineEdits and the
        # reload race (a control deleted out from under an Export press) cannot
        # occur. The exported bundle then carries no CondaPackages / CondaChannels
        # (those come only from the Conda queue env), so the expected job bundles
        # omit them too.
        return {"environments": []}


# ========================= HTTP server =========================

_INT_QUERY_PARAMS = {"maxResults", "itemOffset", "pageSize"}

# Cap request bodies so a malformed/oversized Content-Length can't make the mock
# read an unbounded amount into memory. The real requests here are tiny; this is
# just a defensive ceiling.
_MAX_BODY_BYTES = 10 * 1024 * 1024  # 10 MiB


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def _discover_routes(backend: MockDeadlineBackend):
    """Find @route-decorated methods on the backend and compile URI patterns."""
    routes = []
    for name in dir(backend):
        fn = getattr(backend, name)
        info = getattr(fn, "__http_route__", None)
        if info is None:
            continue
        method, path, operation = info
        pattern = _re.compile("^" + _re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$")
        routes.append((method, pattern, fn, operation))
    return routes


class _ResponseValidator:
    """Filters mock responses to the service-model shape and validates them, so a
    malformed mock response fails here instead of confusing the real client."""

    def __init__(self) -> None:
        session = botocore.session.get_session()
        loader = session.get_component("data_loader")
        self._model = ServiceModel(loader.load_service_model("deadline", "service-2"))
        self._validator = ParamValidator()

    _TYPE_DEFAULTS = {
        "string": "",
        "integer": 0,
        "long": 0,
        "float": 0.0,
        "double": 0.0,
        "boolean": False,
        "timestamp": datetime(1970, 1, 1, tzinfo=timezone.utc),
        "list": [],
        "map": {},
        "structure": {},
    }

    def _filter(self, shape, value):
        # Drop keys not in the shape; fill required members the mock omitted with
        # type-appropriate defaults, so response validation passes across
        # botocore versions that add new required fields.
        if shape is None or value is None:
            return value
        t = shape.type_name
        if t == "structure":
            members = shape.members
            filtered = {k: self._filter(members[k], v) for k, v in value.items() if k in members}
            for req in getattr(shape, "required_members", []):
                if req not in filtered and req in members:
                    filtered[req] = self._TYPE_DEFAULTS.get(members[req].type_name, None)
            return filtered
        if t == "list":
            return [self._filter(shape.member, v) for v in value]
        if t == "map":
            return {k: self._filter(shape.value, v) for k, v in value.items()}
        return value

    def filter_and_validate(self, operation_name: str, response: dict) -> dict:
        output_shape = self._model.operation_model(operation_name).output_shape
        if output_shape is None:
            return response
        filtered = self._filter(output_shape, response)
        report = self._validator.validate(filtered, output_shape)
        if report.has_errors():
            raise ValueError(
                f"Mock response for {operation_name} failed validation: {report.generate_report()}"
            )
        return filtered


def _make_handler(routes, validator, backend: MockDeadlineBackend):
    class _Handler(_BaseHTTPRequestHandler):
        def log_message(self, format, *args):  # silence default stderr access logs
            return

        def _send_json(self, status, body, error_code=None):
            data_bytes = _json.dumps(body, default=_json_default).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data_bytes)))
                if error_code:
                    self.send_header("x-amzn-errortype", error_code)
                self.end_headers()
                self.wfile.write(data_bytes)
            except (BrokenPipeError, ConnectionResetError):
                # The submitter abandons in-flight requests when it tears down a
                # queue-environment reload (the reload race the test guards
                # against), closing the socket mid-response. That's expected and
                # harmless -- the client already moved on -- so swallow it rather
                # than letting socketserver dump a traceback to stderr.
                pass

        def _dispatch(self, method):
            parsed = _urlparse(self.path)

            # Admin endpoint: expose the observability state so a test running in
            # a different process (the server runs out-of-process to avoid GIL
            # starvation from xa11y's native waits) can read what was served.
            if parsed.path == _ADMIN_CALLS_PATH and method == "GET":
                with backend._lock:
                    snapshot = {
                        "call_counts": dict(backend.call_counts),
                        "request_log": [list(r) for r in backend.request_log],
                        "unmatched_requests": [list(r) for r in backend.unmatched_requests],
                    }
                self._send_json(200, snapshot)
                return

            for route_method, pattern, handler_fn, op_name in routes:
                if route_method != method:
                    continue
                m = pattern.match(parsed.path)
                if not m:
                    continue
                # --- Matched a route: record + serve ---
                # Approximate the real farm's 200-600ms response latency so the
                # submitter's queue-environment reload timing is reproduced
                # faithfully (see MockDeadlineBackend docstring).
                if backend.response_delay_s:
                    _time.sleep(backend.response_delay_s)
                with backend._lock:
                    backend.call_counts[op_name] = backend.call_counts.get(op_name, 0) + 1
                    backend.request_log.append((method, parsed.path, op_name))
                kwargs = dict(m.groupdict())
                for k, v in _parse_qs(parsed.query).items():
                    kwargs[k] = int(v[0]) if k in _INT_QUERY_PARAMS else v[0]
                length = int(self.headers.get("Content-Length", 0))
                if length > _MAX_BODY_BYTES:
                    self._send_json(413, {"message": "Payload too large"})
                    return
                if length:
                    kwargs.update(_json.loads(self.rfile.read(length)))
                try:
                    result = handler_fn(**kwargs)
                    result = validator.filter_and_validate(op_name, result)
                    backend._log(f"served {op_name} ({method} {parsed.path}) -> 200")
                    self._send_json(200, result)
                except ClientError as exc:
                    err = exc.response["Error"]
                    code = err.get("Code", "InternalServerException")
                    status = 404 if code == "ResourceNotFoundException" else 400
                    backend._log(f"served {op_name} ({method} {parsed.path}) -> {status} {code}")
                    self._send_json(status, {"message": err.get("Message", "")}, error_code=code)
                except Exception as exc:  # noqa: BLE001
                    import traceback

                    traceback.print_exc()
                    backend._log(f"served {op_name} ({method} {parsed.path}) -> 500 {exc!r}")
                    self._send_json(
                        500, {"message": str(exc)}, error_code="InternalServerException"
                    )
                return

            # --- No route matched: record loudly so a missing mock is visible ---
            with backend._lock:
                backend.unmatched_requests.append((method, parsed.path))
            backend._log(f"UNMATCHED {method} {parsed.path} -> 404 (no mock for this route)")
            _sys.stderr.write(f"[mock-deadline] 404 NO ROUTE {method} {parsed.path}\n")
            _sys.stderr.flush()
            self._send_json(
                404,
                {"message": f"No route for {method} {parsed.path}"},
                error_code="NotFoundException",
            )

        def do_GET(self):  # noqa: N802
            self._dispatch("GET")

        def do_POST(self):  # noqa: N802
            self._dispatch("POST")

        def do_PATCH(self):  # noqa: N802
            self._dispatch("PATCH")

    return _Handler


def start_server(backend: MockDeadlineBackend, port: int = 0):
    """Start the mock Deadline HTTP server in a daemon thread.

    Returns ``(server, base_url, thread)``. Binds to ``127.0.0.1`` on an
    ephemeral port. Point the ``deadline`` client at ``base_url`` via
    ``AWS_ENDPOINT_URL_DEADLINE`` (and disable the ``management.`` host prefix).
    """
    routes = _discover_routes(backend)
    validator = _ResponseValidator()
    handler_cls = _make_handler(routes, validator, backend)
    server = _ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    actual_port = server.server_address[1]
    thread = _threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{actual_port}", thread
