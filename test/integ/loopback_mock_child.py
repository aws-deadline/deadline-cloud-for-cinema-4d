# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Start the offline mock without HTTPServer's unnecessary reverse-DNS lookup."""

from http.server import ThreadingHTTPServer
from socketserver import TCPServer
from unittest.mock import patch

from deadline_test_fixtures.deadline_mock import backend
from deadline_test_fixtures.deadline_mock._server_child import main as run_mock


class LoopbackHTTPServer(ThreadingHTTPServer):
    def server_bind(self) -> None:
        if self.server_address[0] != "127.0.0.1":
            raise ValueError("The offline mock must bind to IPv4 loopback")
        TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = int(self.server_address[1])


def main() -> None:
    with patch.object(backend, "ThreadingHTTPServer", LoopbackHTTPServer):
        run_mock()


if __name__ == "__main__":
    main()
