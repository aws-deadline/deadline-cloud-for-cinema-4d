# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from shutil import copy2, rmtree
from typing import Callable, Optional

import pytest
import xa11y
from deadline_test_fixtures.job_bundle import (
    JobBundleCase,
    assert_valid_job_bundle,
    find_complete_job_bundle,
)
from deadline_test_fixtures.xa11y import (
    SharedSubmitterDialog,
    find_accessibility_app,
)
from .utils import (
    assert_all_images_close,
    assert_expected_job_bundle_and_generated_job_bundle_are_equal,
    assert_openjd_run_with_cinema4d_successful,
    build_cinema4d_scene,
    build_submitter_pythonpath,
    kill_proc,
    log,
    resolve_c4d_exe,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_REAL_PLUGIN_DIR = _REPO_ROOT / "deadline_cloud_extension"

# Test-only sidecar plugin loaded alongside the real plugin (see its docstring).
# Its presence on g_additionalModulePath is what auto-opens the submitter; the
# shipped DeadlineCloud.pyp carries no test hook of its own.
_AUTO_OPEN_PLUGIN_DIR = Path(__file__).parent / "fixtures" / "auto_open_submitter"

# Selector strings pinned by inspecting the live UIA tree at runtime
# (see commit history for tree dumps). UIA on Windows surfaces the Qt
# QApplication display name as the dialog's accessible name — *not*
# Qt's windowTitle. The Submit/Export-bundle buttons keep their visible
# labels as accessible names.
#
# Export button: deadline-cloud/src/deadline/client/ui/dialogs/
#                    submit_job_to_deadline_dialog.py:250
# Both the UIA App hosting the dialog and the dialog window itself surface this
# same name (the QApplication display name + version), so it serves as the
# prefix for matching either one.
_DIALOG_NAME_PREFIX = "Deadline Cloud Cinema4D Submitter"
_EXPORT_BUTTON_NAME = "Export bundle"

_C4D_BOOT_TIMEOUT_S = 180.0
_DIALOG_VISIBLE_TIMEOUT_S = 60.0

# Most cases save `<case>.c4d` directly under actual/. These two deliberately
# differ to exercise path handling and therefore need explicit relative paths.
_SCENE_RELATIVE_PATHS = {
    "phy_apos_path": Path("it's") / "phy_apos_path.c4d",
    "redshift_textured_nonascii": Path("rs_test-\u20bf\u0119\u00f1.c4d"),
}

# A per-scene hook to drive the submitter dialog (switch tabs, set parameters,
# toggle options) after it has loaded but before Export bundle is pressed. It
# receives the dialog locator; use dialog.descendant("role[name='...']") to
# reach widgets and .set_value()/.press()/.toggle()/.select() to interact. A
# scene with no configurator exports with the dialog's default settings.
#
# Whatever a configurator changes must be reflected in that scene's
# expected_job_bundle/, since the golden comparison is exact.
DialogConfigurator = Callable[[xa11y.Locator], None]


def _prepend(new: str, existing: str, sep: str) -> str:
    """Prepend `new` to `existing` using `sep`, without leaving a dangling
    separator when `existing` is empty.

    Cinema 4D parses g_additionalModulePath strictly — a trailing separator
    leaves the last path interpreted as `<path>:` and fails to resolve.
    """
    return f"{new}{sep}{existing}" if existing else new


def _dump_plugin_diag_log(log_path: Path) -> None:
    """Echo the sidecar plugin's diagnostic log into the test output. C4D's
    stdout is detached from pytest's, so this is how the plugin's traces (scene
    load, CallCommand result, any exceptions) reach a failing run's report.
    Called before the staging dir is removed."""
    if not log_path.is_file():
        log(f"no plugin diag log at {log_path}")
        return
    log(f"--- sidecar plugin diag log ({log_path}) ---")
    print(log_path.read_text(encoding="utf-8", errors="replace"))
    log("--- end sidecar plugin diag log ---")


def _prepare_actual_dir(test_cases_folder_location: Path, case: str) -> tuple[Path, Path]:
    """Resolve the case folder and its (freshly emptied) actual/ output dir.

    Returns (case_folder, actual_dir). actual/ is the runtime working area: the
    scene is built into it and the exported bundle is copied flat into it, then
    actual/ is compared against expected/. We rmtree it first so a prior failed
    run (which leaves actual/ behind for inspection) can't leak stale files into
    this run."""
    bundle_case = JobBundleCase(test_cases_folder_location / case)
    return bundle_case.root, bundle_case.prepare_actual_dir()


def _build_cinema4d_scene(
    cinema4d_location: Path,
    case_folder: Path,
    actual_dir: Path,
    case: str,
    scene_args: tuple[str, ...] = (),
) -> Path:
    """Build the case's scene with c4dpy and return the saved scene path.

    The scene script lives at <case>/input/scene.py and is expected to save the
    scene as <case>.c4d. It is saved into actual/ (not input/) so that
    render_data RDATA_PATH = "renders/$prj" (resolved against
    doc.GetDocumentPath()) lands renders inside actual/renders/ -- where the
    render comparison looks. Same trick the existing test/integ/ test relies on.
    """
    c4dpy_location = resolve_c4d_exe(cinema4d_location, "c4dpy")
    scene_script = case_folder / "input" / "scene.py"
    scene_relative_path = _SCENE_RELATIVE_PATHS.get(case, Path(f"{case}.c4d"))
    return build_cinema4d_scene(
        c4dpy_location,
        scene_script,
        actual_dir,
        str(scene_relative_path),
        scene_args,
    )


def _build_launch_env(
    scene_path: Path,
    plugin_diag_log: Path,
    mock_env_overlay: dict,
) -> dict:
    """Build the environment for the Cinema 4D subprocess.

    Starts from ``mock_env_overlay`` (built by the ``deadline_farm`` fixture):
    that overlay already carries this process's environment plus the redirect to
    the mock Deadline backend -- endpoint override, dummy credentials, telemetry
    opt-out, isolated HOME, the temp deadline config path, and the mock-mode flag
    that switches on the sidecar's ``management.`` getaddrinfo redirect. So the
    submitter talks to the local mock, never real AWS.
    """
    return {
        **mock_env_overlay,
        # Point C4D at two plugin dirs: the real submitter plugin checked into
        # this repo, and the test-only sidecar that auto-opens the submitter.
        # C4D loads every .pyp on this path at startup; the sidecar dispatches
        # into the real, unmodified plugin via CallCommand. Same env var the
        # InstallBuilder installer sets. C4D uses ';' as the separator on every
        # platform (it is not the OS pathsep).
        "g_additionalModulePath": _prepend(
            str(_AUTO_OPEN_PLUGIN_DIR),
            _prepend(
                str(_REAL_PLUGIN_DIR),
                os.environ.get("g_additionalModulePath", ""),
                ";",
            ),
            ";",
        ),
        # C4D's bundled Python uses this for extra package resolution.
        # We need the editable submitter source plus the venv site-packages
        # (PySide6 / qtpy / deadline-client all live there).
        "C4DPYTHONPATH311": _prepend(
            build_submitter_pythonpath(_REPO_ROOT),
            os.environ.get("C4DPYTHONPATH311", ""),
            os.pathsep,
        ),
        # Where the sidecar plugin writes its diagnostics (read back on
        # failure once the subprocess is killed).
        "DEADLINE_CLOUD_DIAG_LOG": str(plugin_diag_log),
        # Pass the scene path via env var on all platforms so the sidecar
        # plugin loads it with LoadDocument before opening the submitter.
        # C4DPL_PROGRAM_STARTED fires before C4D processes argv files, so
        # without this the active document has no path when the submitter
        # opens.
        "DEADLINE_CLOUD_SCENE_PATH": str(scene_path),
    }


def _launch_cinema4d(cinema4d_gui_exe: Path, scene_path: Path, env: dict) -> subprocess.Popen:
    """Launch Cinema 4D with the submitter + sidecar plugins.

    On macOS we don't pass the scene on argv (the sidecar loads it via
    DEADLINE_CLOUD_SCENE_PATH); on Windows we pass it on argv too.
    """
    if sys.platform == "darwin":
        proc = subprocess.Popen(
            [str(cinema4d_gui_exe)],
            env=env,
        )
    else:
        proc = subprocess.Popen(
            [str(cinema4d_gui_exe), str(scene_path)],
            env=env,
        )
    return proc


def _dump_dialog_discovery_failure(app) -> None:
    """Dump the C4D app tree and the full running-app list when the submitter
    dialog never registers as its own UIA app (Windows). Diagnostics only."""
    log("dialog never registered as a UIA app; debugging info:")
    try:
        log("Cinema 4D app tree:")
        print(app.dump())
    except Exception:
        # Best-effort diagnostics; the dump itself failing must not mask the
        # original failure this function is reporting.
        pass
    try:
        log("All running apps:")
        for a in xa11y.App.list():
            print(f"  - {a.name!r} (pid={a.pid})")
    except Exception as e:
        log(f"App.list() failed: {e!r}")


def _resolve_dialog_app(proc: subprocess.Popen):
    """Attach xa11y to the launched Cinema 4D process and return the
    accessibility app that hosts the submitter dialog.

    The sidecar plugin opens the submitter automatically once C4D finishes
    starting (C4DPL_PROGRAM_STARTED). Where the dialog appears in the
    accessibility tree is platform-specific:
      - Windows UIA: Qt registers each dialog as a separate top-level UIA
        app sharing the C4D pid.
      - macOS AX: dialogs are child windows of the host app.
    """
    log(f"waiting up to {_C4D_BOOT_TIMEOUT_S:.0f}s for xa11y to attach by pid")
    if sys.platform == "win32":
        try:
            dialog_app = find_accessibility_app(
                proc.pid,
                timeout=_C4D_BOOT_TIMEOUT_S + _DIALOG_VISIBLE_TIMEOUT_S,
                name_prefix=_DIALOG_NAME_PREFIX,
            )
        except TimeoutError:
            try:
                host_app = find_accessibility_app(proc.pid, timeout=2.0)
                _dump_dialog_discovery_failure(host_app)
            except TimeoutError:
                # Host-app discovery is diagnostics-only; preserve the original
                # submitter-dialog timeout when the host is also unavailable.
                pass
            raise AssertionError(
                "Submitter dialog did not register with UIA "
                f"(expected app name prefix {_DIALOG_NAME_PREFIX!r})"
            )
        log(f"submitter dialog UIA app: {dialog_app.name!r}")
    else:
        # On macOS the dialog is a child window of the C4D app.
        dialog_app = find_accessibility_app(
            proc.pid,
            timeout=_C4D_BOOT_TIMEOUT_S,
        )
        log("macOS: using C4D app handle for dialog discovery")
    log("xa11y attached to Cinema 4D")

    # Dump the tree for diagnostics on first run / failures.
    try:
        log("dialog app tree (depth=8):")
        print(dialog_app.dump(max_depth=8))
    except Exception as e:
        log(f"dialog_app.dump() failed: {e!r}")

    return dialog_app


def _wait_for_submitter_dialog(dialog_app):
    """Wait for the submitter dialog to become visible and return its locator.

    On Windows UIA: role=dialog, name=QApplication display name.
    On macOS AX: role=window, name=window title. Try both selectors.
    """
    log(f"waiting for dialog: {_DIALOG_NAME_PREFIX!r}")
    dialog = dialog_app.locator(
        f"dialog[name^='{_DIALOG_NAME_PREFIX}'], " f"window[name^='{_DIALOG_NAME_PREFIX}']"
    )
    try:
        dialog.wait_visible(timeout=_DIALOG_VISIBLE_TIMEOUT_S)
    except Exception:
        log("dialog selector failed; final tree:")
        try:
            print(dialog_app.dump())
        except Exception:
            # Best-effort diagnostic dump; if it fails we still re-raise the
            # original error below.
            pass
        raise
    log("submitter dialog visible")
    return dialog


def _wait_for_queue_environment_loading(dialog_app) -> None:
    """Wait for the queue-environment loading caption to clear. Non-fatal if it
    times out — Export bundle may still be clickable.

    The mock returns no queue environments, so the caption ("Loading Queue
    Environments...") should appear briefly and clear almost immediately; we
    still wait for it to confirm the dialog has settled before pressing Export.
    """
    log("waiting for queue environment loading to finish")
    loading = dialog_app.locator(
        "static_text[name^='Loading Queue Environments'], "
        "static_text[name^='Reloading Queue Environments'], "
        "static_text[name^='Error loading queue environments']"
    )
    try:
        loading.wait_hidden(timeout=_DIALOG_VISIBLE_TIMEOUT_S)
        log("queue environment loading finished (loading caption hidden)")
    except Exception as e:
        log(f"loading-text wait failed (non-fatal): {e!r}")


def _press_export_bundle(dialog, dialog_app) -> None:
    """Wait for the Export bundle button to be visible and enabled, then
    press it."""
    log(f"waiting for button: {_EXPORT_BUTTON_NAME!r}")
    export_btn = SharedSubmitterDialog(dialog).button(_EXPORT_BUTTON_NAME)
    export_btn.wait_visible(timeout=_DIALOG_VISIBLE_TIMEOUT_S)
    export_btn.wait_enabled(timeout=_DIALOG_VISIBLE_TIMEOUT_S)
    log("pressing Export bundle")
    try:
        export_btn.press()
    except Exception:
        log("Export bundle press failed; final dialog tree:")
        try:
            print(dialog_app.dump())
        except Exception:
            # Best-effort diagnostic dump; if it fails we still re-raise the
            # original error below.
            pass
        raise


def _dismiss_success_popup(pid: int) -> None:
    """Dismiss the "Saved the submission as a job bundle" popup promptly.

    The popup is deadline-cloud's success QMessageBox. Two things make it
    awkward to match (both confirmed by dumping the live AX tree):

    * It is hosted by the **Cinema 4D** app, NOT the separate submitter-dialog
      app, so searching ``dialog_app`` never finds it.
    * Its title ("Cinema4D job submission") is not exposed as the dialog's AX
      name on macOS -- the role is ``dialog`` with an empty name. The reliable
      anchor is the message body static_text, which starts with "Saved the
      submission as a job bundle".

    So we poll the accessibility roots belonging to the launched Cinema 4D
    process for a dialog/window/sheet containing that body text and press its
    OK button. Restricting by PID avoids querying unrelated applications whose
    accessibility providers may be unresponsive. Best-effort and non-fatal:
    the bundle is already on disk and asserted separately.
    """
    log("dismissing success popup ('Saved the submission as a job bundle')")
    deadline_t = time.monotonic() + 5.0
    while time.monotonic() < deadline_t:
        try:
            for app in xa11y.App.list():
                if app.pid != pid:
                    continue
                ok = app.locator(
                    "dialog button[name='OK'], "
                    "window button[name='OK'], "
                    "sheet button[name='OK']"
                )
                # Only treat it as our popup if the success body text is present
                # in the same app, so we don't press an unrelated OK button.
                body = app.locator("static_text[name^='Saved the submission as a job bundle']")
                if body.exists() and ok.exists():
                    ok.press()
                    log("success popup dismissed (OK)")
                    return
        except Exception as e:
            log(f"success-popup scan raised (retrying): {e!r}")
        time.sleep(0.25)
    log("success popup not found within 5s (non-fatal, bundle already exported)")


def _dump_settings_tabs(dialog) -> None:
    """Dump each settings tab's accessibility tree (DIALOG_DUMP=1 diagnostic).

    Switches to the Shared and Job-specific tabs and prints each subtree, so a
    contributor can read the live role + accessible names to build selectors --
    these differ between macOS AX and Windows UIA, so they must be harvested per
    platform rather than guessed. See "Finding selectors" in test/AGENTS.md for
    the one-command workflow."""
    from . import submitter_ui as ui

    for tab in (ui.TAB_SHARED, ui.TAB_JOB_SPECIFIC):
        log(f"=== DIALOG_DUMP: {tab} tab (depth 15) ===")
        try:
            ui.switch_to_tab(dialog, tab)
            print(dialog.element().dump(max_depth=15))
        except Exception as e:
            log(f"dump of {tab!r} failed: {e!r}")
        log(f"=== DIALOG_DUMP: end {tab} tab ===")


def _copy_bundle_files(staged_bundle: Path, dest: Path) -> None:
    """Copy the exported bundle files flat into `dest`."""
    log(f"copying bundle files {staged_bundle} -> {dest}")
    for src in staged_bundle.iterdir():
        if src.is_file():
            copy2(src, dest / src.name)
            log(f"  copied {src.name}")


def _drive_submitter_ui(
    proc: subprocess.Popen,
    history_dir: Path,
    configure: Optional[DialogConfigurator] = None,
) -> Path:
    """Drive the running submitter dialog via xa11y and return the exported
    bundle directory.

    Waits for the dialog, lets queue-environment loading settle (the mock
    returns no queue environments, so there are no Conda parameter widgets to
    rebuild and thus no reload race), runs the optional per-scene `configure`
    hook to adjust the dialog (tabs, parameters), presses Export bundle,
    dismisses the success popup, then reads the completed bundle from
    `history_dir`.

    `configure` runs after the dialog settles and before Export. When it is None
    the dialog is exported with its default settings.
    """
    dialog_app = _resolve_dialog_app(proc)
    dialog = _wait_for_submitter_dialog(dialog_app)
    _wait_for_queue_environment_loading(dialog_app)
    # Diagnostic harvest: DIALOG_DUMP=1 dumps each settings tab's tree and raises,
    # so you can capture the live accessibility names (which differ across macOS
    # AX and Windows UIA) without hand-editing a configurator. Skips Export.
    if os.environ.get("DIALOG_DUMP") == "1":
        _dump_settings_tabs(dialog)
        raise AssertionError("DIALOG_DUMP=1: dumped settings tabs, skipping export")
    if configure is not None:
        log("running per-scene dialog configurator")
        configure(dialog)
    _press_export_bundle(dialog, dialog_app)

    # The submitter writes the bundle files and only then shows the success
    # popup (on_export_bundle in submit_job_to_deadline_dialog.py), so once the
    # popup is up the bundle is complete on disk and we can read it directly.
    _dismiss_success_popup(proc.pid)
    # Note: on Windows the submitter would normally open the bundle folder in
    # File Explorer (os.startfile); the sidecar plugin suppresses that in mock
    # mode, so there's no Explorer window to clean up here.

    staged_bundle = find_complete_job_bundle(history_dir)
    assert (
        staged_bundle is not None
    ), f"success popup shown but no complete bundle found under {history_dir}"
    log(f"bundle found: {staged_bundle}")
    return staged_bundle


def _export_job_bundle_via_submitter(
    cinema4d_location: Path,
    scene_path: Path,
    job_bundle_generated: Path,
    deadline_farm: dict,
    configure: Optional[DialogConfigurator] = None,
) -> None:
    """Launch Cinema 4D, drive the real submitter UI to export a job bundle,
    and copy the bundle files flat into `job_bundle_generated`.

    The submitter exports via create_job_history_bundle_dir, which always
    writes under <history_dir>/<YYYY-mm>/<bundle-name>/. The history dir is set
    in the temp deadline config the `deadline_farm` fixture wrote (read inside
    the C4D subprocess), so the bundle lands under that dir; we then copy the
    bundle files flat into generated_bundle/ so asserts use the same layout as
    the existing render integ tests.

    Owns all cleanup: the C4D subprocess is always killed and its diagnostic
    log echoed before the staging dir is removed, even on failure.
    """
    cinema4d_gui_exe = resolve_c4d_exe(cinema4d_location, "Cinema 4D")

    history_dir = deadline_farm["job_history_dir"]
    bundle_staging = Path(tempfile.mkdtemp(prefix="c4d-submitter-ui-"))
    plugin_diag_log = bundle_staging / "plugin-diag.log"
    log(f"bundle staging dir: {bundle_staging}; job history dir: {history_dir}")
    try:
        env = _build_launch_env(scene_path, plugin_diag_log, deadline_farm["env_overlay"])
        proc = _launch_cinema4d(cinema4d_gui_exe, scene_path, env)
        try:
            staged_bundle = _drive_submitter_ui(proc, history_dir, configure=configure)
            _copy_bundle_files(staged_bundle, job_bundle_generated)
        finally:
            kill_proc(proc)
            _dump_plugin_diag_log(plugin_diag_log)
    finally:
        rmtree(bundle_staging, ignore_errors=True)
        log(f"removed staging dir: {bundle_staging}")


def _load_configurator(
    case: str,
    configure_kwargs: Optional[dict[str, str]] = None,
) -> Optional[DialogConfigurator]:
    """Load a case's optional input/configure.py and return its `configure`
    callable, or None if the case has no configurator.

    A configure.py must define a top-level `configure(dialog, ...)` function.
    Keyword arguments let a parametrized case reuse one configurator for
    multiple settings. If the file is malformed or missing that function, we
    raise -- a broken configurator should fail loudly, not be silently skipped.
    """
    # `case` comes from the _CASES registry, but guard against a name that would
    # escape test_cases/ (path separators or ..) so a typo can't load arbitrary
    # files.
    cases_root = (Path(__file__).parent / "test_cases").resolve()
    config_path = (cases_root / case / "input" / "configure.py").resolve()
    if not config_path.is_relative_to(cases_root):
        raise ValueError(f"case {case!r} resolves outside test_cases/")
    if not config_path.is_file():
        if configure_kwargs:
            raise FileNotFoundError(f"{config_path} is required when configure arguments are set")
        return None
    spec = importlib.util.spec_from_file_location(f"_configure_{case}", config_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load configurator at {config_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    configure = getattr(module, "configure", None)
    if not callable(configure):
        raise AttributeError(f"{config_path} must define a top-level configure(dialog) function")
    if configure_kwargs:
        return lambda dialog: configure(dialog, **configure_kwargs)
    return configure


def _run_integ_case(
    cinema4d_location: Path,
    test_cases_folder_location: Path,
    deadline_farm: dict,
    case: str,
    *,
    expected_variant: Optional[str] = None,
    configure_kwargs: Optional[dict[str, str]] = None,
    scene_args: tuple[str, ...] = (),
) -> None:
    """Build, export, validate, and optionally render one case configuration."""
    case_folder, actual_dir = _prepare_actual_dir(test_cases_folder_location, case)
    configure = _load_configurator(case, configure_kwargs)

    scene_path = _build_cinema4d_scene(
        cinema4d_location,
        case_folder,
        actual_dir,
        case,
        scene_args,
    )

    _export_job_bundle_via_submitter(
        cinema4d_location=cinema4d_location,
        scene_path=scene_path,
        job_bundle_generated=actual_dir,
        deadline_farm=deadline_farm,
        configure=configure,
    )

    # The submitter ran against the mock backend, not real AWS. Prove its calls
    # reached our server and nothing hit an unmocked route. The out-of-process
    # mock exposes these counters through its admin endpoint.
    backend = deadline_farm["backend"]
    log(f"mock backend call_counts: {dict(backend.call_counts)}")
    assert (
        backend.unmatched_requests == []
    ), f"submitter hit routes the mock doesn't implement: {backend.unmatched_requests}"
    for op in ("ListFarms", "ListQueueEnvironments"):
        assert (
            backend.call_counts.get(op, 0) >= 1
        ), f"expected the submitter to call {op}; saw {dict(backend.call_counts)}"
    assert any(
        backend.call_counts.get(op, 0) >= 1 for op in ("GetQueue", "ListQueues")
    ), f"expected a queue lookup; saw {dict(backend.call_counts)}"

    assert_valid_job_bundle(actual_dir / "template.yaml")

    expected_dir = case_folder / "expected"
    if expected_variant is not None:
        expected_dir /= expected_variant
    assert_expected_job_bundle_and_generated_job_bundle_are_equal(
        expected_dir / "job_bundle", actual_dir
    )

    # Run the bundle via openjd and compare rendered output. This adaptor
    # portion only runs on Windows; on macOS the test is submitter-only (the
    # render path needs Conda-managed cinema4d-openjd, which we don't ship for
    # darwin yet). Every case keeps its output directory at actual/renders;
    # output-path cases vary only the filename.
    if sys.platform != "darwin":
        assert_openjd_run_with_cinema4d_successful(
            cinema4d_location,
            actual_dir / "template.yaml",
            actual_dir / "parameter_values.yaml",
        )
        assert_all_images_close(
            expected_dir / "renders",
            actual_dir / "renders",
        )

    # ARTIFACT_REVIEW_DELAY_S pauses here — after all assertions, before
    # cleanup — so the exported bundle and renders in actual/ can be inspected
    # manually. Pairs with DIALOG_CONFIG_OBSERVE_DELAY_S for watching the
    # dialog interactions themselves.
    review_delay = float(os.environ.get("ARTIFACT_REVIEW_DELAY_S", "0"))
    if review_delay > 0:
        log(f"pausing {review_delay:.0f}s for manual review of artifacts in {actual_dir}")
        time.sleep(review_delay)

    # Clean up if the test was successful
    rmtree(actual_dir, ignore_errors=True)


# Redshift render cases fail on GitHub-hosted Windows runners; the root cause
# is currently under investigation. macOS CI is unaffected because the render
# step doesn't run on darwin. Run these locally against a reachable license
# server for coverage.
_SKIP_REDSHIFT_IN_CI = pytest.mark.skipif(
    sys.platform == "win32" and os.environ.get("CI") == "true",
    reason="Redshift render cases fail on GitHub-hosted Windows runners",
)

# Standard test cases. Each entry is a folder name under test_cases/ with an
# input/scene.py (required) and an optional input/configure.py (loaded as the
# dialog configurator). Parametrized case-specific coverage is registered
# separately below.
_CASES = [
    "shared_job_settings",
    "job_specific_output_path",
    "job_specific_multi_pass_path",
    "job_specific_frame_range",
    "job_specific_detailed_logging",
    "job_specific_timeouts",
    "job_specific_save_project_with_assets",
    "job_specific_task_chunking",
    "job_specific_tile_rendering",
    "physical",
    "physical_textured",
    "physical_custom_fps",
    "physical_multi_takes",
    "physical_tiles_multi_takes",
    "phy_apos_path",
    pytest.param("redshift", marks=_SKIP_REDSHIFT_IN_CI),
    pytest.param("redshift_textured", marks=_SKIP_REDSHIFT_IN_CI),
    pytest.param("redshift_textured_nonascii", marks=_SKIP_REDSHIFT_IN_CI),
    pytest.param("redshift_tiles", marks=_SKIP_REDSHIFT_IN_CI),
]

_TAKE_SELECTIONS = [
    pytest.param("current", "Current Take", id="current"),
    pytest.param("main", "Main Take", id="main"),
    pytest.param("all", "All Takes", id="all"),
]


@pytest.mark.parametrize("case", _CASES)
def test_integ(
    cinema4d_location: Path,
    test_cases_folder_location: Path,
    deadline_farm: dict,
    case: str,
) -> None:
    """Exercise one standard scene through the real submitter UI."""
    _run_integ_case(
        cinema4d_location,
        test_cases_folder_location,
        deadline_farm,
        case,
    )


@pytest.mark.parametrize(("expected_variant", "selection"), _TAKE_SELECTIONS)
def test_job_specific_take_selection(
    cinema4d_location: Path,
    test_cases_folder_location: Path,
    deadline_farm: dict,
    expected_variant: str,
    selection: str,
) -> None:
    """Verify Current, Main, and All Takes produce the intended job steps."""
    _run_integ_case(
        cinema4d_location,
        test_cases_folder_location,
        deadline_farm,
        "job_specific_take_selection",
        expected_variant=expected_variant,
        configure_kwargs={"selection": selection},
        scene_args=(expected_variant,),
    )
