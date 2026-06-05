# AGENTS.md — deadline-cloud-for-cinema-4d

Python package providing a Cinema 4D submitter extension and adaptor for AWS Deadline Cloud rendering.

> **New to this repo?** Start with the `c4d-dev-setup` skill to automate your dev environment setup (install hatch, build the package, install the submitter into Cinema 4D). Ask: *"use c4d-dev-setup to set up this computer"*.

## Working in Specific Areas

When working in these areas, read the AGENTS.md in that folder first — it contains the detailed context you need:

- **Submitter code** (`src/deadline/cinema4d_submitter/`) → [`src/deadline/cinema4d_submitter/AGENTS.md`](src/deadline/cinema4d_submitter/AGENTS.md)
- **Adaptor code** (`src/deadline/cinema4d_adaptor/`) → [`src/deadline/cinema4d_adaptor/AGENTS.md`](src/deadline/cinema4d_adaptor/AGENTS.md)
- **Tests** (`test/`) → [`test/AGENTS.md`](test/AGENTS.md)

## High-Level Architecture

```
  SUBMITTER WORKSTATION                         WORKER NODE
 ┌──────────────────────┐                     ┌──────────────────────────┐
 │  Cinema 4D           │                     │  cinema4d-openjd CLI     │
 │  ├─ DeadlineCloud.pyp│   OpenJD Job Bundle │  ├─ Cinema4DAdaptor/     │
 │  └─ cinema4d_submitter│ ──────────────────►│  │    (manages C4D proc) │
 │       (job bundle)   │                     │  └─ Cinema4DClient/      │
 └──────────────────────┘                     │       (runs in C4D)      │
                                              └──────────────────────────┘
```

- **Submitter** runs inside Cinema 4D on the artist's workstation; creates job bundles
- **Cinema4DAdaptor** runs on workers as `cinema4d-openjd` CLI; manages the Cinema 4D process lifecycle
- **Cinema4DClient** runs inside Cinema 4D on workers; executes actions from the adaptor over named pipes

For architecture details, see `docs/software_arch.md` and the area-specific AGENTS.md files above.

## Build

```bash
hatch build
```

For quick submitter iteration during development, see [`src/deadline/cinema4d_submitter/AGENTS.md`](src/deadline/cinema4d_submitter/AGENTS.md). For adaptor changes, build a patched [cinema4d-openjd conda package](https://github.com/aws-deadline/deadline-cloud-samples/tree/mainline/conda_recipes/cinema4d-openjd) and deploy to workers.

## Tests

Use `hatch run test` to run unit tests — do NOT use `pytest` directly.

```bash
hatch run test                                    # All unit tests
hatch run test test/unit/<path>                   # One test file or directory
hatch run test -k "test_name"                     # One test by name
hatch run all:test                                # All supported Python versions
```

**Integration Tests (Windows Only):** See [`test/AGENTS.md`](test/AGENTS.md).

## Linting

```bash
hatch run lint     # ruff + black + mypy
hatch run fmt      # black + ruff auto-format
hatch run typing   # mypy only
```

## Python Version

- Cinema 4D 2026 uses Python 3.11
- Cinema 4D 2024–2025 uses Python 3.10
- System Python 3.10+ is sufficient for unit tests
- Integration tests use Cinema 4D's bundled Python

## Commit Messages

Use conventional commits:
- `feat:` — new features
- `fix:` — bug fixes
- `docs:` — documentation
- `test:` — tests only
- `refactor:` — code refactoring
- `perf:` — performance improvements
- `feat!:` or `fix!:` — breaking changes

## Design Docs for Major Changes

For new features or major refactors, use the `c4d-design` skill to create a structured design doc. This does NOT apply to small bug fixes.

## Supported Renderers

| Renderer | OS Support | Notes |
|----------|-----------|-------|
| Redshift | Windows, Linux | Bundled with C4D 2024+, default renderer |
| Arnold (C4DtoA) | Windows, Linux | Separate plugin |
| V-Ray | Windows, macOS | Separate plugin |
| Physical/Standard | Windows, macOS, Linux | Built-in |

## Skills (for AI agents)

This repo includes three skills in `skills/` (following the [Agent Skills standard](https://agentskills.io/)):

- **c4d-dev-setup** — Automates dev environment setup. Run when onboarding.
- **c4d-dev** — Day-to-day development: build, test, lint, debug, integration testing.
- **c4d-design** — Structured design docs for new features and major refactors.

## External References

- **Cinema 4D Python SDK:** https://developers.maxon.net/docs/py/2026/
- **User Guide:** https://docs.aws.amazon.com/deadline-cloud/latest/userguide/maxon-cinema-4d.html
- **Public conda recipes:** https://github.com/aws-deadline/deadline-cloud-samples
- **OpenJD Adaptor Runtime:** https://github.com/OpenJobDescription/openjd-adaptor-runtime-for-python
- **Software architecture:** `docs/software_arch.md`
