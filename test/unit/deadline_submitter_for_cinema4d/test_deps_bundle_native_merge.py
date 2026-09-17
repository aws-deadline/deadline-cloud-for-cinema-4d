# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Guards which compiled artifact the dependency bundle ships for each interpreter.

The bundle is one flat directory placed on ``PYTHONPATH``, so it holds a single file per
name no matter how many Python versions Cinema 4D might embed. ``scripts/deps_bundle.py``
installs the compiled packages once per supported version and merges the results, and the
merge is where an interpreter can quietly lose its artifact: when two versions install the
same filename, the surviving copy is the only one any interpreter gets to load, and one
built for a newer Python fails to import on an older one.

These tests drive the merge over synthetic trees named the way the real wheels name their
extension modules, because a real build downloads a wheel per compiled package per
supported version. That is also their limit: they assert which artifact is selected, not
that it loads. Proving it loads needs the target interpreter, which the unit suite has no
access to -- ``test_console_signin_dependencies`` only reaches the interpreter running the
tests.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import deps_bundle

# awscrt's abi3 wheels all install this one name, whatever Python they were built for.
ABI3_ARTIFACT = "_awscrt.abi3.so"


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def _tag(version: str) -> str:
    """The interpreter tag a wheel puts in a version-specific extension module name."""
    return version.replace(".", "")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


@pytest.fixture
def supported_versions() -> list[str]:
    versions = sorted(deps_bundle.SUPPORTED_PYTHON_VERSIONS, key=_version_key)
    assert len(versions) >= 2, "a filename collision needs at least two supported versions"
    return versions


@pytest.fixture
def merged_bundle(tmp_path, supported_versions) -> Path:
    """Run the merge over trees named the way the real wheels name their artifacts.

    Reproduces both naming schemes. awscrt installs the shared abi3 name from every abi3
    wheel and a version-specific name from the non-abi3 wheel it publishes for the oldest
    supported Python; xxhash installs a version-specific name for every version; psutil
    ships one abi3 wheel that serves all of them, so every tree holds identical bytes.

    Each file's content records the version whose install produced it, so the merged tree
    reports where its own contents came from. The base environment is seeded with the
    newest version, standing in for a build host whose interpreter is newer than the one
    the bundle has to serve.
    """
    base_env = tmp_path / "base_env"
    _write(base_env / ABI3_ARTIFACT, supported_versions[-1])

    native_paths = []
    for version in supported_versions:
        tree = tmp_path / "native" / version.replace(".", "_")
        native_paths.append(tree)
        if version == supported_versions[0]:
            _write(tree / f"_awscrt.cpython-{_tag(version)}-darwin.so", version)
        else:
            _write(tree / ABI3_ARTIFACT, version)
        _write(tree / "xxhash" / f"_xxhash.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "psutil" / "_psutil_osx.abi3.so", "shared")
        _write(tree / "yaml" / f"_yaml.cpython-{_tag(version)}-darwin.so", version)

    deps_bundle._copy_native_to_base_env(base_env, native_paths)
    return base_env


def test_colliding_abi3_artifact_comes_from_the_lowest_supported_abi(
    merged_bundle, supported_versions
):
    """abi3 is forward compatible, so the lowest is the only copy that serves every version.

    A copy built for a newer Python links against symbols an older one does not export, so
    it fails to import there -- botocore then leaves its crypto binding unset and AWS
    Console sign-in reports that sign-in is needed, indefinitely.
    """
    lowest_abi3_version = supported_versions[1]
    shipped = (merged_bundle / ABI3_ARTIFACT).read_text()

    assert shipped == lowest_abi3_version, (
        f"{ABI3_ARTIFACT} was built for Python {shipped}, so it cannot be imported by "
        f"Python {lowest_abi3_version}; the copy built for the lowest supported abi3 "
        f"version is the one every supported interpreter can load"
    )


def test_version_specific_artifacts_are_kept_for_every_supported_version(
    merged_bundle, supported_versions
):
    """The other half of the rule: these names do not collide, so none may be dropped.

    Collapsing a colliding name to one copy is only safe because the names that encode an
    interpreter tag are distinct, and every supported version needs its own.
    """
    for version in supported_versions:
        artifact = merged_bundle / "xxhash" / f"_xxhash.cpython-{_tag(version)}-darwin.so"
        assert artifact.exists(), f"the bundle carries no xxhash artifact for Python {version}"
        assert artifact.read_text() == version

    lowest = supported_versions[0]
    awscrt_non_abi3 = merged_bundle / f"_awscrt.cpython-{_tag(lowest)}-darwin.so"
    assert awscrt_non_abi3.exists(), f"the bundle carries no awscrt artifact for Python {lowest}"


def test_native_trees_are_merged_lowest_python_version_first(tmp_path, monkeypatch):
    """The merge keeps the first tree to supply a name, so the download order picks the winner.

    Ordered numerically rather than as strings: sorted as text, "3.9" lands after "3.10".
    The versions here are chosen to expose that, not to describe what is supported.
    """
    monkeypatch.setattr(deps_bundle, "SUPPORTED_PYTHON_VERSIONS", ["3.13", "3.9", "3.11", "3.10"])
    monkeypatch.setattr(deps_bundle, "_get_package_version", lambda package, install_path: "1.2.3")

    requested_versions: list[str] = []

    def record(args, **kwargs):
        requested_versions.append(args[args.index("--python-version") + 1])
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(deps_bundle.subprocess, "run", record)

    tree_paths = deps_bundle._download_native_dependencies(tmp_path, tmp_path / "base_env")

    assert requested_versions == ["3.9", "3.10", "3.11", "3.13"]
    assert [path.name for path in tree_paths] == ["3_9", "3_10", "3_11", "3_13"]


def _native_trees(tmp_path, supported_versions) -> tuple[Path, list[Path]]:
    """A merged bundle plus the per-version trees it was built from.

    Same naming scheme as ``merged_bundle``, but the package directories the verification
    step looks for are created too, since it checks resolution as well as the merge.
    """
    base_env = tmp_path / "base_env"
    _write(base_env / ABI3_ARTIFACT, supported_versions[-1])

    native_paths = []
    for version in supported_versions:
        tree = tmp_path / "native" / version.replace(".", "_")
        native_paths.append(tree)
        if version == supported_versions[0]:
            _write(tree / f"_awscrt.cpython-{_tag(version)}-darwin.so", version)
        else:
            _write(tree / ABI3_ARTIFACT, version)
        _write(tree / "xxhash" / f"_xxhash.cpython-{_tag(version)}-darwin.so", version)
        _write(tree / "psutil" / "_psutil_osx.abi3.so", "shared")
        _write(tree / "yaml" / f"_yaml.cpython-{_tag(version)}-darwin.so", version)

    deps_bundle._copy_native_to_base_env(base_env, native_paths)
    return base_env, native_paths


def test_verify_bundle_accepts_a_correctly_merged_bundle(tmp_path, supported_versions):
    base_env, native_paths = _native_trees(tmp_path, supported_versions)

    deps_bundle._verify_bundle(base_env, native_paths)


def test_verify_base_environment_rejects_a_dropped_native_package(tmp_path, monkeypatch):
    """The failure mode when resolution backtracks past the extra a package arrives through.

    pip warns and exits 0, so nothing else in the build notices. Checked against the base
    environment before the per-version downloads, because afterwards every name reappears --
    the trees supply it regardless of what resolution produced.
    """
    resolved = {name: "1.0" for name in deps_bundle.NATIVE_DEPENDENCIES}
    dropped = deps_bundle.NATIVE_DEPENDENCIES[-1]
    del resolved[dropped]

    def fake_version(package, install_path):
        if package not in resolved:
            raise RuntimeError(f"Could not find version for package {package}")
        return resolved[package]

    monkeypatch.setattr(deps_bundle, "_get_package_version", fake_version)

    with pytest.raises(RuntimeError, match="resolution dropped"):
        deps_bundle._verify_base_environment(tmp_path)


def test_verify_base_environment_accepts_a_complete_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr(deps_bundle, "_get_package_version", lambda package, path: "1.0")

    deps_bundle._verify_base_environment(tmp_path)


def test_verify_bundle_rejects_an_untracked_version_specific_artifact(tmp_path, supported_versions):
    """A compiled package absent from NATIVE_DEPENDENCIES loads on one interpreter only.

    Base-env resolution is pinned to the lowest supported version, so such an artifact is
    deterministically built for that one. pyyaml was exactly this before it was added to the
    list, and it hid the problem by falling back to a pure-Python parser.
    """
    base_env, native_paths = _native_trees(tmp_path, supported_versions)
    _write(base_env / "brotli" / "_brotli.cpython-310-darwin.so", "3.10")

    with pytest.raises(RuntimeError, match="NATIVE_DEPENDENCIES"):
        deps_bundle._verify_bundle(base_env, native_paths)


def test_verify_bundle_accepts_windows_artifact_names(tmp_path, supported_versions):
    """Windows spells both cases differently: `cp310-win_amd64` tags, and bare `.pyd` for abi3.

    Matching only the Unix spellings classifies every Windows artifact as untagged, which fails
    a correct Windows bundle -- the primary installer target for this repo.
    """
    base_env = tmp_path / "win_base_env"
    native_paths = []
    for version in supported_versions:
        tree = tmp_path / "win_native" / version.replace(".", "_")
        native_paths.append(tree)
        if version == supported_versions[0]:
            _write(tree / f"_awscrt.cp{_tag(version)}-win_amd64.pyd", version)
        else:
            _write(tree / "_awscrt.pyd", version)
        _write(tree / "xxhash" / f"_xxhash.cp{_tag(version)}-win_amd64.pyd", version)
        _write(tree / "psutil" / "_psutil_windows.pyd", "shared")
        _write(tree / "yaml" / f"_yaml.cp{_tag(version)}-win_amd64.pyd", version)
    deps_bundle._copy_native_to_base_env(base_env, native_paths)

    deps_bundle._verify_bundle(base_env, native_paths)

    # The bare `.pyd` collides across every abi3 tree, so the lowest one must win.
    assert (base_env / "_awscrt.pyd").read_text() == supported_versions[1]


def test_verify_bundle_rejects_an_abi3_copy_from_the_wrong_python(tmp_path, supported_versions):
    """The defect this guards: the shipped abi3 copy is not the lowest supported version's.

    Reproduces it exactly as the old merge produced it -- the build host's copy left in place.
    """
    base_env, native_paths = _native_trees(tmp_path, supported_versions)
    (base_env / ABI3_ARTIFACT).write_text(supported_versions[-1])

    with pytest.raises(RuntimeError, match="lowest supported Python"):
        deps_bundle._verify_bundle(base_env, native_paths)


def test_verify_bundle_rejects_an_artifact_missing_from_the_bundle(tmp_path, supported_versions):
    base_env, native_paths = _native_trees(tmp_path, supported_versions)
    (base_env / ABI3_ARTIFACT).unlink()

    with pytest.raises(RuntimeError, match="absent from the bundle"):
        deps_bundle._verify_bundle(base_env, native_paths)


def test_base_environment_is_resolved_for_the_lowest_supported_python(supported_versions):
    """The bundle's contents must not depend on which interpreter the build host runs."""
    assert deps_bundle._lowest_supported_python_version() == supported_versions[0]


@pytest.mark.parametrize(
    "artifact_name,expected",
    [
        # Unix, version specific
        ("_awscrt.cpython-310-darwin.so", "3.10"),
        ("_xxhash.cpython-311-x86_64-linux-gnu.so", "3.11"),
        ("_yaml.cpython-313-darwin.so", "3.13"),
        # Windows, version specific -- the tag is `cp310`, not `cpython-310`
        ("_awscrt.cp310-win_amd64.pyd", "3.10"),
        ("_xxhash.cp312-win_amd64.pyd", "3.12"),
        # Unix, stable ABI
        ("_awscrt.abi3.so", None),
        ("_psutil_osx.abi3.so", None),
        ("libshiboken6.abi3.6.8.dylib", None),
        # Windows, stable ABI -- spelled by the *absence* of a tag, not by an `abi3` infix
        ("_awscrt.pyd", None),
        ("_psutil_windows.pyd", None),
    ],
)
def test_interpreter_tag_of_reads_every_platform_spelling(artifact_name, expected):
    """Pins the filename rules the coverage check depends on.

    Every name here was taken from a real wheel. Reading only the Unix spelling classifies a
    Windows version-specific artifact as stable ABI, which is the more dangerous direction: it
    makes a one-interpreter binary look loadable everywhere.
    """
    assert deps_bundle._interpreter_tag_of(artifact_name) == expected


def test_verify_bundle_rejects_a_windows_version_gap(tmp_path, supported_versions):
    """A Windows bundle missing one version's artifact must fail, not pass as stable ABI.

    This is what discriminates correct tag parsing from treating every Windows name as
    untagged: `_xxhash.cp310-win_amd64.pyd` loads on 3.10 alone, so if it is mistaken for a
    stable-ABI module the gap on 3.11+ goes unreported.
    """
    base_env = tmp_path / "gap_base_env"
    native_paths = []
    lowest = supported_versions[0]
    for version in supported_versions:
        tree = tmp_path / "gap_native" / version.replace(".", "_")
        native_paths.append(tree)
        _write(tree / "_awscrt.pyd", "shared")
        _write(tree / "psutil" / "_psutil_windows.pyd", "shared")
        _write(tree / "yaml" / f"_yaml.cp{_tag(version)}-win_amd64.pyd", version)
        # xxhash resolves only for the oldest interpreter, so every later one is uncovered.
        if version == lowest:
            _write(tree / "xxhash" / f"_xxhash.cp{_tag(version)}-win_amd64.pyd", version)
    deps_bundle._copy_native_to_base_env(base_env, native_paths)

    with pytest.raises(RuntimeError, match="no compiled artifact that can load"):
        deps_bundle._verify_bundle(base_env, native_paths)
