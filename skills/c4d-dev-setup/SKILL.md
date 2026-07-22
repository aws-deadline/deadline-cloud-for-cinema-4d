---
name: c4d-dev-setup
description: Automated dev environment setup for deadline-cloud-for-cinema-4d. Use when onboarding, setting up the Cinema 4D integration repo, building the package, or installing the submitter. The agent automates all steps and only prompts when user input is required.
tags: [skill, deadline-cloud, deadline-cloud-for-cinema-4d, deadline-cloud-for-c4d, dev-setup, onboarding, submitter-install]
---

# Cinema 4D Dev Setup

## Overview

AI-guided automated setup for the `deadline-cloud-for-cinema-4d` project. The agent executes all steps, validates results, and only prompts the user when manual intervention is truly required.

## Usage

Use this skill when:
- Setting up a new dev environment for the Cinema 4D integration
- Onboarding to the `deadline-cloud-for-cinema-4d` repo
- Installing the submitter into Cinema 4D for the first time

## Core Concepts

**Platforms:**
- Windows: full support (submitter + adaptor development, integration tests)
- macOS: submitter development only
- Linux: adaptor development only (no submitter UI)

**Python:** Cinema 4D 2026 uses Python 3.11; Cinema 4D 2024–2025 uses Python 3.10.

**Build system:** Hatch.

## Agent Behavior

You **MUST** automate all possible steps by running commands directly.
You **MUST** only prompt the user when their input is required (Cinema 4D version, custom paths).
You **MUST** validate each step's output before proceeding to the next.
You **MUST** inform the user clearly when manual intervention is needed.
You **SHOULD** report progress at each step.

## Setup Workflow

Follow the detailed step-by-step workflow in [references/setup-guide.md](references/setup-guide.md).

Summary of steps:
1. Detect OS and warn about platform limitations
2. Prompt for Cinema 4D version (default: 2026)
3. Verify Cinema 4D installation
4. Verify Python 3.10+
5. Read project documentation (`README.md`, `DEVELOPMENT.md`, `docs/software_arch.md`)
6. Install Hatch
7. Build the package (`hatch build`)
8. Build the installer (optional, requires InstallBuilder)
9. Install the submitter into Cinema 4D
10. Set up Windows integration rendering prerequisites, when applicable
11. Display summary

## Troubleshooting

Refer to [references/troubleshooting.md](references/troubleshooting.md) for common issues and solutions.

## Quick Reference

| Resource | Location |
|----------|----------|
| Setup workflow | `references/setup-guide.md` |
| Troubleshooting | `references/troubleshooting.md` |
| Architecture context | `AGENTS.md` (repo root) |
| Project docs | `README.md`, `DEVELOPMENT.md`, `docs/software_arch.md` |
