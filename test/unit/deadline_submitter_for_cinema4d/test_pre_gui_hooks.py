# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""Unit tests for the Cinema 4D submitter's pre-GUI hook integration.

``_show_submitter`` calls deadline-cloud's ``run_pre_gui_hooks`` (env-only, since Cinema 4D has
no on-disk bundle at pre-GUI time) and then applies the merged output with deadline-cloud's
generic ``apply_pre_gui_output``. The full submitter needs a running Cinema 4D, so it is
exercised in the integration suite; here we verify the DCC-owned pieces headless:

* ``apply_pre_gui_output`` routes hook output correctly against Cinema 4D's own
  ``RenderSubmitterUISettings`` — which has no ``.parameters`` list, so every hook parameter must
  land in the shared parameter values (name/description land on the settings object). This guards
  against a regression where ``RenderSubmitterUISettings`` gains a ``parameters`` attribute that
  would misroute hook params.
* ``_pre_gui_hook_confirm_callback`` honours the ``settings.auto_accept`` setting.

The c4d / Qt modules are stubbed by ``test/unit/deadline_submitter_for_cinema4d/__init__`` so
the module imports.
"""

from unittest.mock import patch

from deadline.cinema4d_submitter import cinema4d_render_submitter
from deadline.cinema4d_submitter.data_classes import RenderSubmitterUISettings
from deadline.client.ui.pre_gui_hooks import apply_pre_gui_output


def _settings() -> RenderSubmitterUISettings:
    s = RenderSubmitterUISettings()
    s.name = "Original"
    s.description = ""
    return s


def test_name_and_description_applied_to_settings():
    """A hook's name/description overwrite the settings fields (C4D has no .parameters list,
    so these land directly on the dataclass)."""
    settings = _settings()
    shared = {"CondaPackages": "cinema4d=2026.* cinema4d-openjd=0.1.*"}

    apply_pre_gui_output({"name": "PREGUI RAN", "description": "from pipeline"}, settings, shared)

    assert settings.name == "PREGUI RAN"
    assert settings.description == "from pipeline"


def test_hook_parameters_flow_to_shared_values():
    """C4D's RenderSubmitterUISettings has no .parameters list, so every hook parameter (queue
    params, deadline: properties) lands in the shared values the dialog is seeded with,
    overriding the C4D-computed defaults on key collision."""
    settings = _settings()
    shared = {"CondaPackages": "cinema4d=2026.* cinema4d-openjd=0.1.*"}

    apply_pre_gui_output(
        {
            "parameters": {
                "deadline:priority": 88,
                "CondaPackages": "cinema4d=2026.* custom_pkg",  # overrides the default
            }
        },
        settings,
        shared,
    )

    assert shared["deadline:priority"] == 88
    assert shared["CondaPackages"] == "cinema4d=2026.* custom_pkg"


def test_empty_output_is_a_noop():
    """No pre-GUI hook output leaves the settings and shared values unchanged."""
    settings = _settings()
    shared = {"CondaPackages": "pkg"}

    apply_pre_gui_output({}, settings, shared)

    assert settings.name == "Original"
    assert settings.description == ""
    assert shared == {"CondaPackages": "pkg"}


def test_falsy_output_is_a_noop():
    """The submitter passes ``pre_gui_output or {}`` into apply_pre_gui_output, so the values
    run_pre_gui_hooks can actually produce for the no-hooks path — ``{}`` today, or ``None`` if
    the contract ever changed — must both be safe no-ops that leave settings/shared untouched."""
    falsy_values: list[dict | None] = [{}, None]
    for falsy in falsy_values:
        settings = _settings()
        shared = {"CondaPackages": "cinema4d=2026.* cinema4d-openjd=0.1.*"}

        # Mirror the submitter call site: `pre_gui_output or {}`.
        apply_pre_gui_output(falsy or {}, settings, shared)

        assert settings.name == "Original"
        assert settings.description == ""
        assert shared == {"CondaPackages": "cinema4d=2026.* cinema4d-openjd=0.1.*"}


def test_partial_output_only_touches_present_keys():
    """Only the keys present in the output are applied; others keep their prior values."""
    settings = _settings()
    settings.description = "keep me"
    shared: dict = {}

    apply_pre_gui_output({"name": "NewName"}, settings, shared)

    assert settings.name == "NewName"
    assert settings.description == "keep me"  # not overwritten
    assert shared == {}  # no parameters in output


def test_hook_sticky_settings_reset_to_baseline_when_user_did_not_edit():
    """A pre-GUI hook that overwrote name/description must not leave those values in the scene's
    sticky settings. If the field still holds the hook's value at save time (the user left it
    untouched), it is restored to the pre-hook baseline so hook output stays scoped to the session
    -- otherwise it would persist after the hook is disabled and feed back as ``jobName`` next
    launch (PR #480)."""
    settings = _settings()
    settings.name = "PREGUI RAN"  # what the hook applied and the user left untouched
    settings.description = "from hook"

    cinema4d_render_submitter._restore_pre_gui_hook_sticky_settings(
        settings,
        {"name": ("Original", "PREGUI RAN"), "description": ("", "from hook")},
    )

    assert settings.name == "Original"
    assert settings.description == ""


def test_hook_sticky_settings_keep_user_edits():
    """If the user edited a hook-populated field in the dialog, that edit -- not the pre-hook
    baseline -- persists, because its current value differs from what the hook applied."""
    settings = _settings()
    settings.name = "MyShot_v2"  # user overrode the hook's "PREGUI RAN"
    settings.description = "from hook"  # left as the hook set it

    cinema4d_render_submitter._restore_pre_gui_hook_sticky_settings(
        settings,
        {"name": ("Original", "PREGUI RAN"), "description": ("", "from hook")},
    )

    assert settings.name == "MyShot_v2"  # user edit kept
    assert settings.description == ""  # untouched hook value scoped back out


def test_hook_sticky_settings_noop_without_reset_map():
    """No hook overwrote a sticky field (empty or None map) -> settings are left untouched, so the
    common no-hooks path persists exactly what the dialog produced."""
    reset: dict | None
    for reset in ({}, None):
        settings = _settings()
        settings.name = "Whatever"
        settings.description = "desc"

        cinema4d_render_submitter._restore_pre_gui_hook_sticky_settings(settings, reset)

        assert settings.name == "Whatever"
        assert settings.description == "desc"


def test_restore_pre_gui_hook_sticky_settings_returns_reset_fields():
    """The restore helper reports which fields it reset to baseline, so the caller can reapply the
    hook values afterwards. A field the user edited is not reset and so is not reported."""
    settings = _settings()
    settings.name = "PREGUI RAN"  # hook value, user left it
    settings.description = "MyEdit"  # user overrode the hook's "from hook"

    restored = cinema4d_render_submitter._restore_pre_gui_hook_sticky_settings(
        settings,
        {"name": ("Original", "PREGUI RAN"), "description": ("", "from hook")},
    )

    assert restored == {"name": "PREGUI RAN"}  # only the un-edited field was reset
    assert settings.name == "Original"
    assert settings.description == "MyEdit"


def test_sticky_baseline_context_restores_for_write_then_reapplies():
    """Inside the context the sticky-write sees the pre-hook baseline; on exit the live settings
    object is restored to the hook values, so a second Export/Submit in the same session still
    builds its job from what the user saw (regression guard for the in-place mutation bug)."""
    settings = _settings()
    settings.name = "PREGUI RAN"
    settings.description = "from hook"
    reset = {"name": ("Original", "PREGUI RAN"), "description": ("", "from hook")}

    seen_during_write = {}
    with cinema4d_render_submitter._pre_gui_hook_sticky_baseline(settings, reset):
        seen_during_write["name"] = settings.name
        seen_during_write["description"] = settings.description

    assert seen_during_write == {"name": "Original", "description": ""}  # baseline for the write
    assert settings.name == "PREGUI RAN"  # hook values put back for later actions
    assert settings.description == "from hook"


def test_sticky_baseline_context_keeps_user_edit_throughout():
    """A field the user edited is neither reset for the write nor touched on exit, so the user's
    value both persists to sticky settings and remains on the live object."""
    settings = _settings()
    settings.name = "MyShot_v2"  # user overrode the hook value
    settings.description = "from hook"
    reset = {"name": ("Original", "PREGUI RAN"), "description": ("", "from hook")}

    with cinema4d_render_submitter._pre_gui_hook_sticky_baseline(settings, reset):
        assert settings.name == "MyShot_v2"  # user edit untouched during the write

    assert settings.name == "MyShot_v2"
    assert settings.description == "from hook"  # reapplied hook value


def test_sticky_baseline_context_reapplies_even_if_write_raises():
    """The hook values must be restored even when save_sticky_settings raises, so a failed write
    never leaves the live settings object stuck at the baseline."""
    settings = _settings()
    settings.name = "PREGUI RAN"
    reset = {"name": ("Original", "PREGUI RAN")}

    try:
        with cinema4d_render_submitter._pre_gui_hook_sticky_baseline(settings, reset):
            raise RuntimeError("save failed")
    except RuntimeError:
        pass

    assert settings.name == "PREGUI RAN"


def test_compute_sticky_reset_maps_deadline_params_to_sticky_fields():
    """A hook that emits a deadline:* job property (routed through the shared parameter values, not
    onto the settings object) is recorded against its sticky field with the hook's value, so it can
    be scoped out of the sticky write just like name/description. deadline:priority is exactly what
    the integ fixture emits."""
    settings = _settings()  # priority defaults to 50
    reset = cinema4d_render_submitter._compute_pre_gui_hook_sticky_reset(
        settings,
        {"name": settings.name, "description": settings.description},  # unchanged -> no entry
        {"CondaPackages": "pkg"},
        {"CondaPackages": "pkg", "deadline:priority": 88},  # hook added deadline:priority
    )
    assert reset == {"priority": (50, 88)}


def test_compute_sticky_reset_covers_name_description_and_shared_together():
    """name/description (applied directly on settings) and deadline:* fields (via shared values) are
    both captured in one reset map."""
    settings = _settings()
    settings.name = "PREGUI RAN"  # post-apply state
    settings.description = "from hook"
    reset = cinema4d_render_submitter._compute_pre_gui_hook_sticky_reset(
        settings,
        {"name": "Original", "description": ""},  # pre-hook baseline
        {"CondaPackages": "pkg"},
        {"CondaPackages": "pkg", "deadline:priority": 88, "deadline:maxRetriesPerTask": 9},
    )
    assert reset["name"] == ("Original", "PREGUI RAN")
    assert reset["description"] == ("", "from hook")
    assert reset["priority"] == (50, 88)
    assert reset["max_retries_per_task"] == (5, 9)


def test_compute_sticky_reset_ignores_unchanged_and_unmapped_shared_params():
    """Only shared keys the hook actually changed AND that map to a sticky field are recorded: an
    unchanged deadline:* value and a non-sticky key (CondaPackages) are both ignored."""
    settings = _settings()
    reset = cinema4d_render_submitter._compute_pre_gui_hook_sticky_reset(
        settings,
        {"name": settings.name, "description": settings.description},
        {"CondaPackages": "pkg", "deadline:priority": 50},
        {
            "CondaPackages": "pkg2",
            "deadline:priority": 50,
        },  # CondaPackages changed (unmapped); priority same
    )
    assert reset == {}


def test_sticky_baseline_context_scopes_priority_out_of_write():
    """End to end: a deadline:priority reset flows through the sticky-baseline context manager just
    like name/description -- baseline during the write, hook value reapplied after."""
    settings = _settings()
    settings.priority = 88  # gathered from the shared Priority widget (the hook value)
    reset = {"priority": (50, 88)}

    seen = {}
    with cinema4d_render_submitter._pre_gui_hook_sticky_baseline(settings, reset):
        seen["priority"] = settings.priority

    assert seen["priority"] == 50  # sticky write sees the pre-hook baseline
    assert settings.priority == 88  # reapplied after


def test_sticky_baseline_context_keeps_user_priority_edit():
    """If the user changed Priority in the dialog away from the hook value, that edit persists to
    sticky (current value != hook value, so it is not reset)."""
    settings = _settings()
    settings.priority = 90  # user overrode the hook's 88
    reset = {"priority": (50, 88)}

    with cinema4d_render_submitter._pre_gui_hook_sticky_baseline(settings, reset):
        assert settings.priority == 90  # not reset during the write

    assert settings.priority == 90


@patch.object(cinema4d_render_submitter, "get_setting", return_value="true")
def test_confirm_callback_none_when_auto_accept_enabled(mock_get_setting):
    """With settings.auto_accept enabled, hooks run without a confirmation prompt."""
    assert cinema4d_render_submitter._pre_gui_hook_confirm_callback(parent=None) is None
    mock_get_setting.assert_called_once_with("settings.auto_accept")


@patch.object(cinema4d_render_submitter, "qt_hook_confirmation")
@patch.object(cinema4d_render_submitter, "get_setting", return_value="false")
def test_confirm_callback_prompts_when_auto_accept_disabled(mock_get_setting, mock_qt_confirm):
    """With settings.auto_accept disabled, the standard Qt confirmation callback is selected and
    built against the window passed into the submitter.

    We assert on the submitter's own contract — that it hands ``qt_hook_confirmation`` the parent
    and uses its result as the ``confirm_callback`` — rather than reaching into deadline-cloud's
    ``qt_hook_confirmation`` internals (it imports ``QMessageBox`` lazily from ``qtpy`` inside the
    returned callback; whether the dialog itself fires is covered by deadline-cloud's own tests).
    """
    sentinel = object()
    mock_qt_confirm.return_value = sentinel

    result = cinema4d_render_submitter._pre_gui_hook_confirm_callback(parent="mainwin")

    assert result is sentinel
    mock_qt_confirm.assert_called_once_with("mainwin")
