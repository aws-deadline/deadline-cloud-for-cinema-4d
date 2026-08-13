# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards the dependency requirements for AWS Console sign-in.

Console sign-in is not exercised by the integration tests: it needs an interactive
browser OAuth handshake and Deadline Cloud Monitor, while CI authenticates by
assuming a role (host-provided credentials). So the parts that can break silently
are the dependency requirements themselves, which is what these tests pin.

Each failure below corresponds to a real way console sign-in breaks at runtime,
reported to the user as "Signing in to the AWS Console sign-in profile <name>
requires an additional dependency" or as a plain missing-attribute error.
"""

from importlib.metadata import version

from packaging.version import Version

# Console sign-in landed in deadline 0.60.4 and nowhere earlier. 0.60.1 through
# 0.60.3 have no AWS_CONSOLE_LOGIN credentials source and do not declare a
# `console` extra at all, so requesting deadline[console] against them is invalid.
MINIMUM_DEADLINE_VERSION = Version("0.60.4")


def test_deadline_is_new_enough_for_console_signin():
    """A lower floor can resolve to a version with no console sign-in support."""
    assert Version(version("deadline")) >= MINIMUM_DEADLINE_VERSION


def test_console_signin_credentials_source_exists():
    """`login_session` profiles are recognised via this enum member."""
    from deadline.client.api._session import AwsCredentialsSource

    assert hasattr(AwsCredentialsSource, "AWS_CONSOLE_LOGIN")


def test_awscrt_is_installed():
    """The console extra pulls awscrt.

    Console sign-in refreshes its cached token in-process, and that token is bound
    to a DPoP key whose proofs botocore's LoginProvider signs using awscrt. Without
    it every API call raises MissingDependencyException.
    """
    import awscrt  # noqa: F401


def test_botocore_can_reach_awscrt_crypto():
    """botocore.compat.EC is the symbol LoginProvider itself checks.

    It is ``awscrt.crypto.EC``, or None when awscrt is missing or older than
    0.28.4 -- so this asserts the dependency is both present and new enough,
    which a version pin alone does not guarantee.
    """
    from botocore.compat import EC

    assert EC is not None


def test_console_login_preflight_does_not_raise():
    """The guard the submitter hits on sign-in.

    deadline.client raises here when awscrt is unusable, rather than letting the
    post-launch poll loop hang forever waiting on an authentication probe that can
    never succeed. If this fails, console sign-in is broken for the user.
    """
    from deadline.client.api._loginout import _check_console_login_dependency

    _check_console_login_dependency("test-profile")
