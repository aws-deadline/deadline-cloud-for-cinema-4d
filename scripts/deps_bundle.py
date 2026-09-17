# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from _project import Dependency, get_dependencies, get_project_dict

SUPPORTED_PYTHON_VERSIONS = ["3.10", "3.11", "3.12", "3.13"]
SUPPORTED_PLATFORMS = ["Windows", "Linux", "Darwin"]
# Packages with compiled extension modules, fetched once per supported Python version so the
# bundle carries a loadable artifact for each interpreter.
#
# awscrt is here because its wheels are not uniformly abi3: Python 3.10 gets
# _awscrt.cpython-310-<platform>.so while 3.11+ get _awscrt.abi3.so. Resolving it only in
# the base environment would ship whichever the build host produced, so any Cinema 4D whose
# interpreter that single artifact does not cover would fail to import awscrt and AWS
# Console sign-in would break there.
# pyyaml is here because it ships a version-specific `_yaml` extension and nothing else in the
# bundle corrects for that. Resolved only in the base environment it lands built for a single
# interpreter -- the shipped 0.12.2 bundle carries `_yaml.cpython-313-darwin.so` alone -- and
# pyyaml hides that by falling back to its pure-Python parser, so the bundle merely got slower
# on three of the four supported interpreters rather than failing.
NATIVE_DEPENDENCIES = ["xxhash", "psutil", "awscrt", "pyyaml"]

# Distribution name -> the name its extension modules are installed under, where they differ.
NATIVE_DEPENDENCY_MODULE_NAMES = {"pyyaml": "yaml"}

PYSIDE6_VERSION = "6.8.3"
PYSIDE6_PACKAGES = [f"PySide6-Essentials=={PYSIDE6_VERSION}", f"shiboken6=={PYSIDE6_VERSION}"]

# Files to keep from PySide6 and shiboken6 pip packages after installation.
# Derived from the deadline-cloud pyinstaller allowlist to keep the bundle minimal.
# Everything not matching these patterns is deleted before zipping.
PYSIDE6_ALLOWLIST = {
    # -- shiboken6 --
    "shiboken6/__init__.py",
    "shiboken6/_config.py",
    "shiboken6/Shiboken.abi3.so",
    "shiboken6/Shiboken.pyd",
    "shiboken6/libshiboken6.abi3.*.dylib",
    "shiboken6/libshiboken6.abi3.so.*",
    "shiboken6/shiboken6.abi3.dll",
    "shiboken6/VCRUNTIME140.dll",
    "shiboken6/VCRUNTIME140_1.dll",
    "shiboken6/MSVCP140.dll",
    "shiboken6-*.dist-info/*",
    "shiboken6-*.dist-info/**/*",
    # -- PySide6 package metadata --
    "PySide6/__init__.py",
    "PySide6/_config.py",
    "PySide6/_git_pyside_version.py",
    "PySide6-*.dist-info/*",
    "PySide6-*.dist-info/**/*",
    "PySide6_Essentials-*.dist-info/*",
    # -- PySide6 Python bindings --
    "PySide6/Qt*.abi3.so",
    "PySide6/QtCore.pyd",
    "PySide6/QtGui.pyd",
    "PySide6/QtWidgets.pyd",
    "PySide6/QtDBus.pyd",
    "PySide6/QtSvg.pyd",
    "PySide6/QtNetwork.pyd",
    "PySide6/QtOpenGL.pyd",
    "PySide6/QtOpenGLWidgets.pyd",
    # -- PySide6/shiboken6 shared libraries --
    "PySide6/libpyside6.abi3.*.dylib",
    "PySide6/libpyside6.abi3.so.*",
    "PySide6/pyside6.abi3.dll",
    # -- Windows MSVC runtime bundled with PySide6 --
    "PySide6/VCRUNTIME140.dll",
    "PySide6/VCRUNTIME140_1.dll",
    "PySide6/MSVCP140.dll",
    "PySide6/MSVCP140_1.dll",
    "PySide6/MSVCP140_2.dll",
    # -- Windows OpenGL software renderer --
    "PySide6/opengl32sw.dll",
    # -- Qt core DLLs (Windows) --
    "PySide6/Qt6Core.dll",
    "PySide6/Qt6Gui.dll",
    "PySide6/Qt6Widgets.dll",
    "PySide6/Qt6DBus.dll",
    "PySide6/Qt6Svg.dll",
    # -- Qt frameworks (macOS) --
    # fnmatch's ** doesn't do recursive matching, so we need both * and **/* patterns
    "PySide6/Qt/lib/QtCore.framework/*",
    "PySide6/Qt/lib/QtCore.framework/**/*",
    "PySide6/Qt/lib/QtGui.framework/*",
    "PySide6/Qt/lib/QtGui.framework/**/*",
    "PySide6/Qt/lib/QtWidgets.framework/*",
    "PySide6/Qt/lib/QtWidgets.framework/**/*",
    "PySide6/Qt/lib/QtDBus.framework/*",
    "PySide6/Qt/lib/QtDBus.framework/**/*",
    "PySide6/Qt/lib/QtSvg.framework/*",
    "PySide6/Qt/lib/QtSvg.framework/**/*",
    # -- Qt shared libraries (Linux) --
    "PySide6/Qt/lib/libQt6Core.so.*",
    "PySide6/Qt/lib/libQt6Gui.so.*",
    "PySide6/Qt/lib/libQt6Widgets.so.*",
    "PySide6/Qt/lib/libQt6DBus.so.*",
    "PySide6/Qt/lib/libQt6Svg.so.*",
    "PySide6/Qt/lib/libQt6XcbQpa.so.*",
    "PySide6/Qt/lib/libQt6WaylandClient.so.*",
    "PySide6/Qt/lib/libQt6WaylandEglClientHwIntegration.so.*",
    "PySide6/Qt/lib/libQt6WlShellIntegration.so.*",
    "PySide6/Qt/lib/libQt6OpenGL.so.*",
    "PySide6/Qt/lib/libQt6EglFSDeviceIntegration.so.*",
    "PySide6/Qt/lib/libQt6EglFsKmsSupport.so.*",
    # ICU (required by Qt6Core on Linux)
    "PySide6/Qt/lib/libicui18n.so.*",
    "PySide6/Qt/lib/libicuuc.so.*",
    "PySide6/Qt/lib/libicudata.so.*",
    # -- Qt plugins (macOS/Linux: Qt/plugins/, Windows: plugins/) --
    # platforms
    "PySide6/Qt/plugins/platforms/libqcocoa.dylib",
    "PySide6/Qt/plugins/platforms/libqoffscreen.*",
    "PySide6/Qt/plugins/platforms/libqminimal.*",
    "PySide6/Qt/plugins/platforms/libqminimalegl.so",
    "PySide6/Qt/plugins/platforms/libqxcb.so",
    "PySide6/Qt/plugins/platforms/libqeglfs.so",
    "PySide6/Qt/plugins/platforms/libqlinuxfb.so",
    "PySide6/Qt/plugins/platforms/libqvkkhrdisplay.so",
    "PySide6/Qt/plugins/platforms/libqvnc.so",
    "PySide6/Qt/plugins/platforms/libqwayland*.so",
    "PySide6/plugins/platforms/qwindows.dll",
    "PySide6/plugins/platforms/qminimal.dll",
    "PySide6/plugins/platforms/qoffscreen.dll",
    "PySide6/plugins/platforms/qdirect2d.dll",
    # styles
    "PySide6/Qt/plugins/styles/libqmacstyle.dylib",
    "PySide6/plugins/styles/qwindowsvistastyle.dll",
    "PySide6/plugins/styles/qmodernwindowsstyle.dll",
    # iconengines
    "PySide6/Qt/plugins/iconengines/libqsvgicon.*",
    "PySide6/plugins/iconengines/qsvgicon.dll",
    # imageformats (svg only)
    "PySide6/Qt/plugins/imageformats/libqsvg.*",
    "PySide6/plugins/imageformats/qsvg.dll",
    # wayland (Linux)
    "PySide6/Qt/plugins/wayland-shell-integration/lib*.so",
    "PySide6/Qt/plugins/wayland-decoration-client/lib*.so",
    # platform themes (Linux)
    "PySide6/Qt/plugins/platformthemes/lib*.so",
    # -- Qt translations --
    "PySide6/Qt/translations/*",
    "PySide6/translations/*",
}


def _get_package_version_regex(package: str) -> re.Pattern:
    # Case-insensitive because `pip list` prints the distribution's own casing, which need not
    # match how the requirement is spelled -- `pyyaml` is reported as `PyYAML`.
    return re.compile(rf"^{re.escape(package)} *(.*)$", re.IGNORECASE)


def _get_package_version(package: str, install_path: Path) -> str:
    version_regex = _get_package_version_regex(package)
    pip_args = ["pip", "list", "--path", str(install_path)]
    output = subprocess.run(pip_args, check=True, capture_output=True).stdout.decode("utf-8")
    for line in output.split("\n"):
        match = version_regex.match(line)
        if match:
            return match.group(1)
    raise RuntimeError(f"Could not find version for package {package}")


def _add_console_extra(requirement: str) -> str:
    """Add deadline's `console` extra to a requirement string, preserving its specifier."""
    match = re.fullmatch(
        r"(?P<name>[A-Za-z0-9._-]+)(?:\[(?P<extras>[^\]]*)\])?(?P<spec>.*)", requirement
    )
    if not match or match.group("name").lower() != "deadline":
        return requirement
    extras = [extra for extra in (match.group("extras") or "").split(",") if extra]
    if "console" not in extras:
        extras.append("console")
    return f"{match.group('name')}[{','.join(extras)}]{match.group('spec')}"


def _python_version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


EXTENSION_SUFFIXES = (".so", ".pyd", ".dylib")

# CPython tags a version-specific extension module differently per platform, and there is no
# single spelling: `_xxhash.cpython-310-darwin.so` and `_xxhash.cpython-310-x86_64-linux-gnu.so`
# on Unix, `_xxhash.cp310-win_amd64.pyd` on Windows. Matching only the Unix spelling silently
# classifies every Windows artifact as untagged.
_INTERPRETER_TAG = re.compile(r"\.(?:cpython-|cp)(3\d+)[.\-]")


def _interpreter_tag_of(artifact_name: str) -> str | None:
    """The Python version a version-specific extension module is built for, or None.

    None means the artifact is not tied to one interpreter, which on Unix is spelled with an
    ``abi3`` infix and on Windows is spelled by the *absence* of a tag -- the limited-API
    suffix there is a bare ``.pyd``, so ``psutil/_psutil_windows.pyd`` and awscrt's
    ``_awscrt.pyd`` are both stable-ABI despite carrying no marker at all.
    """
    match = _INTERPRETER_TAG.search(artifact_name)
    if not match:
        return None
    digits = match.group(1)
    return f"{digits[0]}.{digits[1:]}"


def _is_extension_module(relative: Path) -> bool:
    return relative.suffix in EXTENSION_SUFFIXES


def _ascending_supported_python_versions() -> list[str]:
    """Supported versions, oldest first.

    The order is load-bearing in two places: it decides which copy of a colliding filename the
    merge keeps, and it pairs each per-version tree with the Python it was built for.
    """
    return sorted(SUPPORTED_PYTHON_VERSIONS, key=_python_version_key)


def _lowest_supported_python_version() -> str:
    return _ascending_supported_python_versions()[0]


def _build_base_environment(working_directory: Path, dependencies: list[Dependency]) -> Path:
    (working_directory / "base_env").mkdir()
    base_env_path = working_directory / "base_env"
    # The bundle is the submitter, which needs AWS Console sign-in. The console extra is
    # requested here rather than declared in project.dependencies, because those are also
    # resolved into the adaptor package, where a compiled awscrt wheel is both unusable and
    # unavailable for one of the platform tags that build targets (see pyproject.toml).
    #
    # Requesting the extra rather than installing awscrt directly means the bundle tracks
    # whatever the extra actually requires -- notably a botocore floor, since the console
    # login provider lives in botocore, not in deadline -- and takes awscrt from the exact
    # version botocore's crt extra pins, rather than resolving it independently and drifting.
    dependencies_for_pip = [_add_console_extra(d.for_pip()) for d in dependencies]
    # Resolve for the lowest interpreter the bundle targets rather than for whichever one
    # happens to be running. Nothing pins the build host's Python, and every artifact it
    # resolves ships to every supported Cinema 4D, so letting it decide makes the bundle's
    # contents a property of the build machine. `_copy_native_to_base_env` corrects that for
    # the packages in NATIVE_DEPENDENCIES, but the rest of the tree is whatever this call
    # produced -- and a wheel chosen for a newer Python is not loadable on an older one.
    # Resolving low is the safe direction: an artifact the lowest supported interpreter can
    # use is one they all can, because a pure-Python wheel is version independent and an abi3
    # wheel is forward compatible.
    base_env_pip_args = [
        "pip",
        "install",
        "--target",
        str(base_env_path),
        "--python-version",
        _lowest_supported_python_version(),
        "--only-binary=:all:",
        *dependencies_for_pip,
    ]
    subprocess.run(base_env_pip_args, check=True)
    return base_env_path


def _download_native_dependencies(working_directory: Path, base_env: Path) -> list[Path]:
    versioned_native_dependencies = [
        f"{package_name}=={_get_package_version(package_name, base_env)}"
        for package_name in NATIVE_DEPENDENCIES
    ]
    native_dependency_paths = []
    # Ascending order is load-bearing: _copy_native_to_base_env resolves a filename
    # collision in favour of the tree it sees first.
    for version in _ascending_supported_python_versions():
        native_dependency_path = working_directory / "native" / f"{version.replace('.', '_')}"
        native_dependency_paths.append(native_dependency_path)
        native_dependency_path.mkdir(parents=True)
        native_dependency_pip_args = [
            "pip",
            "install",
            "--target",
            str(native_dependency_path),
            "--python-version",
            version,
            "--only-binary=:all:",
            *versioned_native_dependencies,
        ]
        subprocess.run(native_dependency_pip_args, check=True)
    return native_dependency_paths


def _copy_native_to_base_env(base_env: Path, native_dependency_paths: list[Path]) -> None:
    """Flatten the per-version native trees into the bundle, lowest version first.

    ``native_dependency_paths`` is ordered by ascending Python version and the first tree
    to supply a path wins, overwriting the base environment. The base environment resolved
    these packages for whatever interpreter the build host happens to run, which is not a
    version the bundle targets, so it must not decide which artifact ships.

    Which artifacts survive follows from how the wheels name their extension modules, so no
    rule is needed per package. A version-specific name is unique per version and so cannot
    collide: ``xxhash`` ships one wheel per version and every interpreter keeps its own
    ``_xxhash.cpython-<tag>-<platform>.so``. An abi3 name is the same for every version and
    so collides, and there the two cases differ. ``psutil`` publishes a single abi3 wheel
    that serves all of them, so every tree holds identical bytes and the collision is a
    no-op. ``awscrt`` publishes a separate abi3 wheel per Python, each installing
    ``_awscrt.abi3.so``, so the copies differ and only one can ship; abi3 is forward
    compatible, which makes the one built for the lowest supported Python the only copy
    that loads on all of them, and taking the first tree is what keeps it.
    """
    copied: set[Path] = set()
    for native_dependency_path in native_dependency_paths:
        for file in native_dependency_path.rglob("*"):
            if file.is_file():
                relative = file.relative_to(native_dependency_path)
                if relative in copied:
                    continue
                in_base_env = base_env / relative
                in_base_env.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(file), str(in_base_env))
                copied.add(relative)


def _verify_base_environment(base_env: Path) -> None:
    """Fail the build if resolution dropped a package the bundle is supposed to carry.

    Runs before the per-version downloads, which is the only point where this is detectable.
    `_download_native_dependencies` reads each package's resolved version out of the base
    environment, so a dropped package aborts there with "Could not find version for package",
    and after the merge every name reappears in the base environment anyway because the trees
    supply it -- so checked later this says nothing.

    The failure it catches: pip can satisfy a requirement by backtracking to a version that
    does not provide the extra a package arrives through, drop the package, warn once among
    hundreds of lines, and exit 0. `check=True` passes and the bundle ships without it.
    """
    missing_packages = []
    for package_name in NATIVE_DEPENDENCIES:
        try:
            _get_package_version(package_name, base_env)
        except RuntimeError:
            missing_packages.append(package_name)
    if missing_packages:
        raise RuntimeError(
            f"Base environment resolution dropped {', '.join(sorted(missing_packages))}. The "
            "usual cause is a requirement whose floor admits a version that does not provide "
            "the extra the package arrives through: pip backtracks to it, warns, and exits 0. "
            "Check that the `deadline` floor in pyproject.toml is at or above the first "
            "version providing the `console` extra, and search the pip output above for "
            "'does not provide the extra'."
        )


def _verify_bundle(base_env: Path, native_dependency_paths: list[Path]) -> None:
    """Fail the build if the bundle cannot serve every interpreter it claims to.

    Both halves of the assembly fail quietly, which is why this is a build step rather than a
    test. Resolution can drop a requested extra and still exit 0, because a version that
    predates the extra satisfies the floor -- pip reports that as a warning among hundreds of
    lines and `check=True` passes. The merge can discard a compiled artifact, because the
    bundle is one flat directory and two wheels can install the same filename. Neither is
    visible in the finished zip without knowing to look, and the resulting installer reports
    the missing dependency as "sign-in needed" rather than as a packaging fault.

    Checked here, at the point where the per-version trees are still on disk to compare
    against, rather than in the installer test suite, which sees only the merged result.
    """
    # The merge contract: for every path any per-version tree supplies, the bundle holds the
    # copy from the earliest tree that supplied it. For a version-specific extension module
    # that is its own tree's copy, since the name cannot collide. For an abi3 module it is the
    # lowest supported version's copy, which is the only one every supported interpreter can
    # load. Comparing bytes rather than presence is what makes this catch a copy-order
    # regression, which is invisible in a directory listing.
    # Each entry records the file and the Python version of the earliest tree that supplied
    # it. The version cannot be recovered from the file's own path -- an abi3 filename does
    # not carry it, and the parent directory is the package's, not the tree's -- so the trees
    # are paired with the ascending version list they were built from. Pairing by position
    # rather than by parsing the directory name keeps the naming a private detail of
    # _download_native_dependencies.
    versions = _ascending_supported_python_versions()
    if len(native_dependency_paths) != len(versions):
        raise RuntimeError(
            f"Expected one native dependency tree per supported Python {versions}, got "
            f"{len(native_dependency_paths)}."
        )

    expected_source: dict[Path, tuple[Path, str]] = {}
    for native_dependency_path, tree_version in zip(native_dependency_paths, versions):
        for file in native_dependency_path.rglob("*"):
            if file.is_file():
                relative = file.relative_to(native_dependency_path)
                expected_source.setdefault(relative, (file, tree_version))

    discarded = []
    for relative, (source, tree_version) in sorted(expected_source.items()):
        in_base_env = base_env / relative
        if not in_base_env.is_file():
            discarded.append(f"{relative} is absent from the bundle")
        elif in_base_env.read_bytes() != source.read_bytes():
            discarded.append(f"{relative} is not the copy built for Python {tree_version}")
    if discarded:
        details = "\n  ".join(discarded)
        raise RuntimeError(
            "The dependency bundle does not hold the compiled artifacts the per-version "
            "downloads produced, so at least one supported Python cannot load them:\n  "
            f"{details}\n"
            "Every abi3 wheel installs the same filename, so the copies collide and only one "
            "can ship. It must be the one built for the lowest supported Python, because abi3 "
            "is forward compatible and not backward compatible."
        )

    # Merge fidelity is not coverage: the checks above prove the bundle holds what the
    # downloads produced, not that what they produced serves every interpreter. A version
    # whose extension module went missing upstream leaves nothing to compare against and so
    # passes silently -- which is how a bundle carrying no compiled artifact at all would
    # otherwise reach the installer test. Verified here rather than there because only here is
    # it known which Python each artifact was built for: an abi3 filename does not record it,
    # but the tree that supplied the file does.
    uncovered = []
    for version in versions:
        for package_name in NATIVE_DEPENDENCIES:
            if not _has_loadable_artifact(package_name, version, expected_source):
                uncovered.append(f"{package_name} on Python {version}")
    if uncovered:
        raise RuntimeError(
            "The dependency bundle carries no compiled artifact that can load on every "
            f"supported interpreter. Missing: {', '.join(uncovered)}. Either the package "
            "publishes no wheel for that Python, or SUPPORTED_PYTHON_VERSIONS names a version "
            "the bundle cannot actually serve."
        )

    # NATIVE_DEPENDENCIES is a hand-maintained list, and the per-version loop only corrects the
    # packages on it. Anything else compiled is left exactly as the base environment resolved
    # it -- which, now that resolution is pinned to the lowest supported version, means a
    # version-specific artifact is deterministically built for that version and unloadable on
    # every other. A transitive dependency can start shipping one at any dependency bump, so
    # the list going stale has to be a build failure rather than something to notice later.
    strays = sorted(
        str(relative)
        for relative in (
            path.relative_to(base_env) for path in base_env.rglob("*") if path.is_file()
        )
        if _is_extension_module(relative)
        and _interpreter_tag_of(relative.name) is not None
        and relative not in expected_source
    )
    if strays:
        details = "\n  ".join(strays)
        raise RuntimeError(
            "The bundle carries version-specific compiled artifacts that the per-version "
            "downloads do not cover, so they load on one interpreter only:\n  "
            f"{details}\n"
            "Add the owning distribution to NATIVE_DEPENDENCIES so it is fetched once per "
            "supported Python. If it genuinely does not need to load -- a package that falls "
            "back to a pure-Python implementation, say -- say so in a comment there rather "
            "than leaving it to be rediscovered."
        )


def _has_loadable_artifact(
    package_name: str, version: str, expected_source: dict[Path, tuple[Path, str]]
) -> bool:
    """Whether some shipped extension module of ``package_name`` can load on ``version``.

    Decided from how wheels name extension modules. A version-specific name carries its
    interpreter tag and loads on that version alone. An abi3 name loads on the Python it was
    built for and every later one, and the tree that supplied it is what identifies that
    Python -- the filename does not.
    """
    target = _python_version_key(version)
    module_name = NATIVE_DEPENDENCY_MODULE_NAMES.get(package_name, package_name)
    for relative, (_, tree_version) in expected_source.items():
        if not _is_extension_module(relative):
            continue
        # awscrt installs its extension module beside the package rather than inside it, so
        # match on the module name as well as on the containing directory.
        if module_name not in relative.parts and not relative.name.lstrip("_").startswith(
            module_name
        ):
            continue
        built_for = _interpreter_tag_of(relative.name)
        if built_for == version:
            return True
        # Untagged means stable ABI, which loads on the Python it was built for and later
        # ones. The filename does not say which that was, so the tree it came from does.
        if built_for is None and _python_version_key(tree_version) <= target:
            return True
    return False


def _get_zip_path(working_directory: Path, project_dict: dict[str, Any]) -> Path:
    if "project" not in project_dict:
        raise ValueError("pyproject.toml is missing project section")
    if "name" not in project_dict["project"]:
        raise ValueError("pyproject.toml is missing name section")
    transformed_project_name = (
        f"{project_dict['project']['name'].replace('-', '_')}_submitter-deps.zip"
    )
    return working_directory / transformed_project_name


def _zip_bundle(base_env: Path, zip_path: Path) -> None:
    shutil.make_archive(str(zip_path.with_suffix("")), "zip", str(base_env))


def _copy_zip_to_destination(zip_path: Path) -> Path:
    dependency_bundle_dir = Path.cwd() / "dependency_bundle"
    dependency_bundle_dir.mkdir(exist_ok=True)
    zip_destination = dependency_bundle_dir / zip_path.name
    if zip_destination.exists():
        zip_destination.unlink()
    shutil.copy(str(zip_path), str(zip_destination))

    return zip_destination


def _install_pyside6(install_path: Path) -> None:
    """Install PySide6 and shiboken6, then strip to only the files in PYSIDE6_ALLOWLIST."""
    # Resolved for the lowest supported interpreter for the same reason as the base
    # environment: these ship as abi3 wheels, which are forward compatible only.
    pip_args = [
        "pip",
        "install",
        "--target",
        str(install_path),
        "--python-version",
        _lowest_supported_python_version(),
        "--only-binary=:all:",
        *PYSIDE6_PACKAGES,
    ]
    subprocess.run(pip_args, check=True)
    _strip_pyside6(install_path)


def _strip_pyside6(install_path: Path) -> None:
    """Remove PySide6/shiboken6 files not in PYSIDE6_ALLOWLIST."""
    for prefix in (
        "PySide6",
        "shiboken6",
        "PySide6_Essentials-*.dist-info",
        "shiboken6-*.dist-info",
    ):
        for pkg_dir in install_path.glob(prefix):
            if not pkg_dir.is_dir():
                continue
            for path in list(pkg_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(install_path))
                if not any(fnmatch.fnmatch(rel, pat) for pat in PYSIDE6_ALLOWLIST):
                    path.unlink()
            # Clean up empty directories
            for dirpath in sorted(pkg_dir.rglob("*"), reverse=True):
                if dirpath.is_dir() and not any(dirpath.iterdir()):
                    dirpath.rmdir()


def build_deps_bundle() -> None:
    with TemporaryDirectory() as working_directory:
        working_directory = Path(working_directory)
        project_dict = get_project_dict()
        dependencies: list[Dependency] = get_dependencies(project_dict)
        deps_noopenjd: list[Dependency] = filter(
            lambda dep: not dep.name.startswith("openjd"), dependencies
        )
        base_env = _build_base_environment(working_directory, deps_noopenjd)
        _verify_base_environment(base_env)
        native_dependency_paths = _download_native_dependencies(working_directory, base_env)
        _copy_native_to_base_env(base_env, native_dependency_paths)
        _verify_bundle(base_env, native_dependency_paths)
        _install_pyside6(base_env)
        zip_path = _get_zip_path(working_directory, project_dict)
        _zip_bundle(base_env, zip_path)
        print(list(working_directory.glob("*")))
        _copy_zip_to_destination(zip_path)


if __name__ == "__main__":
    build_deps_bundle()
