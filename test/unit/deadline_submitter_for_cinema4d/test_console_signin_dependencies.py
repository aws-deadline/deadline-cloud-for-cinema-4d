# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards the dependency requirements for AWS Console sign-in.

Console sign-in is not exercised by the integration tests: it needs an interactive
browser OAuth handshake and Deadline Cloud Monitor, while CI authenticates by
assuming a role, so credentials are host-provided and the console path is never
taken. What can break silently is the dependency declaration itself, which is what
these tests pin.

The tests are split by what they can promise:

* The declared-requirement tests assert on what this package *asks for*, read from
  its own metadata. They fail if the requirement is loosened, regardless of what a
  resolver happens to pick.
* The runtime tests assert on public APIs of the installed dependency, so a
  refactor inside ``deadline-cloud`` cannot turn them into unrelated CI failures.

Anything depending on a private helper degrades to a skip rather than an error, for
the same reason: the requirement is a floating ``>= 0.60.4, < 0.61``, and a patch
release inside that range may rename internals without it being a breaking change.
"""

from importlib.metadata import requires, version

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

DISTRIBUTION = "deadline-cloud-for-cinema-4d"

# Console sign-in landed in deadline 0.60.4 and nowhere earlier: 0.60.1 through
# 0.60.3 have no AWS_CONSOLE_LOGIN credentials source and do not declare a
# `console` extra at all, so `deadline[console]` is not a valid request against
# them. 0.60.3 is therefore the highest version that must be excluded.
HIGHEST_VERSION_WITHOUT_CONSOLE_SIGNIN = "0.60.3"

# awscrt.crypto.EC first appears in 0.28.4. botocore reports CRT as unavailable
# below that, which disables console sign-in even though awscrt is installed.
MINIMUM_AWSCRT_VERSION = Version("0.28.4")


def _declared_deadline_requirements() -> list[Requirement]:
    """Every `deadline` requirement this package declares, from its own metadata.

    Reads the built distribution's Requires-Dist rather than parsing
    pyproject.toml, which keeps this stdlib-only on Python 3.10 (tomllib is 3.11+)
    and asserts on what was actually declared at build time.
    """
    declared = [Requirement(r) for r in requires(DISTRIBUTION) or []]
    deadline_reqs = [r for r in declared if Requirement(r.name).name == "deadline"]
    assert deadline_reqs, f"{DISTRIBUTION} declares no requirement on deadline"
    return deadline_reqs


def test_declared_requirement_asks_for_the_console_extra():
    """Without the console extra, awscrt is never installed and sign-in fails."""
    for req in _declared_deadline_requirements():
        assert "console" in req.extras, f"missing console extra in: {req}"


def test_declared_floor_excludes_releases_without_console_signin():
    """Guards the floor itself, not whatever a resolver happened to select.

    An installed-version check cannot do this: with a loosened
    ``>= 0.60.1`` requirement, pip still resolves the newest 0.60.x, so the
    regression would pass unnoticed.
    """
    for req in _declared_deadline_requirements():
        assert not req.specifier.contains(HIGHEST_VERSION_WITHOUT_CONSOLE_SIGNIN), (
            f"requirement allows deadline {HIGHEST_VERSION_WITHOUT_CONSOLE_SIGNIN}, "
            f"which has no console sign-in support: {req}"
        )


def test_awscrt_is_installed():
    """The console extra exists to pull awscrt.

    Console sign-in refreshes its cached token in-process, and that token is bound
    to a DPoP key whose proofs botocore's LoginProvider signs using awscrt. Without
    it, every API call raises MissingDependencyException.
    """
    import awscrt  # noqa: F401


def test_awscrt_provides_ec_crypto():
    """botocore treats CRT as unavailable unless awscrt.crypto.EC imports.

    Asserted against awscrt's public API rather than botocore.compat.EC, which is
    an undocumented conditional re-export of exactly this symbol.
    """
    from awscrt.crypto import EC  # noqa: F401

    assert Version(version("awscrt")) >= MINIMUM_AWSCRT_VERSION


def test_console_login_preflight_does_not_raise():
    """The guard the submitter hits when a user signs in.

    deadline.client raises here when awscrt is unusable, rather than letting the
    post-launch poll loop wait forever on an authentication probe that can never
    succeed. Skipped rather than failed if the helper is renamed upstream, since it
    is private and a rename is not a breaking change for deadline-cloud.
    """
    loginout = pytest.importorskip("deadline.client.api._loginout")
    check = getattr(loginout, "_check_console_login_dependency", None)
    if check is None:
        pytest.skip("upstream renamed the console-login preflight helper")

    check("test-profile")


def test_console_signin_credentials_source_exists():
    """`login_session` profiles are recognised through this enum member.

    Skipped rather than failed if the enum moves, for the same reason as above:
    `deadline.client.api._session` is a private module.
    """
    session = pytest.importorskip("deadline.client.api._session")
    credentials_source = getattr(session, "AwsCredentialsSource", None)
    if credentials_source is None:
        pytest.skip("upstream moved AwsCredentialsSource")

    assert hasattr(credentials_source, "AWS_CONSOLE_LOGIN")
