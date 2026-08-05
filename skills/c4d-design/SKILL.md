---
name: c4d-design
description: AI-guided design for Cinema 4D features and major changes in Deadline Cloud integration. Use when designing new features, planning major refactors, creating design docs, or making architectural decisions for deadline-cloud-for-cinema-4d. Triggers on requests like "design a feature", "write a design doc", "plan a major change", or "architect a solution".
tags: [skill, deadline-cloud, deadline-cloud-for-cinema-4d, deadline-cloud-for-c4d, design, architecture, feature-design]
---

# Cinema 4D Design

## Overview

AI-guided interactive design process for Cinema 4D features in Deadline Cloud. The agent drives the conversation — researching, proposing options, and prompting the user for decisions at each step. Progress is saved to disk after each section.

## Usage

Use this skill when:
- Designing a new **major** feature for the Cinema 4D integration
- Planning a major refactor or architectural change
- Creating or refining a design document in `docs/designs/`

Do **not** use this skill for small bug fixes, minor enhancements, or changes that can be adequately described in a PR description.

## Core Concepts

### Agent Role

You are the design driver. The user provides goals and makes decisions. You do everything else:
- **Research** the codebase, `AGENTS.md`, and references
- **Draft** each section with concrete proposals
- **Present** options with pros/cons for every design decision
- **Prompt** the user to choose, confirm, or redirect
- **Challenge** your own proposals — surface weaknesses and edge cases before the user asks
- **Iterate** based on user feedback before moving to the next section

You **MUST NOT** dump an entire design doc at once. Work through it section by section, getting user sign-off on each before proceeding.

### Saving Progress

You **MUST** write the design doc to `docs/designs/<feature-name>.md` incrementally — after each section is approved, write it to disk. This ensures:
- Work survives context window limits
- A new session can resume by reading the file
- The user can review progress at any time

On session start, always check `docs/designs/` for an existing draft to resume.

### Design Flow

The design doc follows a four-section structure. See [references/design-doc-structure.md](references/design-doc-structure.md) for the full structure and [references/design-workflow.md](references/design-workflow.md) for the step-by-step workflow.

#### Step 1: Kickoff

Prompt the user:
```
What would you like to do?
1. Start a new design
2. Refine an existing design (from docs/designs/)
```

**If new design:** Ask the user to describe the feature and any known constraints/specs.

**If refining:** Read the existing doc, ask what needs to change.

#### Step 2: Research

Before drafting anything, you **MUST**:
1. Read `AGENTS.md` at the repo root for high-level architecture
2. Read the relevant area-specific AGENTS.md files for the components you'll touch:
   - `src/deadline/cinema4d_submitter/AGENTS.md` for submitter work
   - `src/deadline/cinema4d_adaptor/AGENTS.md` for adaptor/client work
   - `test/AGENTS.md` for test structure
3. Read `docs/software_arch.md` for additional architectural context
4. Search the codebase for existing patterns related to the feature
5. Read [references/research-guide.md](references/research-guide.md) for Cinema 4D API patterns
6. Read any linked docs, tickets, or prior art the user mentions

Summarize findings to the user. Ask if anything is missing.

#### Step 3: Work through the four design sections

Work through each section with the user, getting sign-off before moving on:

1. **Data Structures to Change or Add**
2. **UX Changes (Submitter Dialog)**
3. **Job Template and Bundle Changes**
4. **Adaptor and Client Changes**

For each design decision:
1. Research options — read code, check APIs, look at existing patterns
2. Present 2-3 options with pros/cons, self-challenge weaknesses
3. Wait for user decision

Write each approved section to disk.

#### Step 4: Testing Plan

Define unit tests and, if applicable, integration tests. Bundle validation runs
on Windows and macOS; rendering assertions run on Windows.

#### Step 5: Create the Appendix

Put all full code implementations in a clearly marked appendix at the end of the design document.

### Prompting Patterns

At every decision point, you **MUST** end with a clear question.

You **MUST NOT**:
- Proceed to the next section without user confirmation
- Make design decisions without presenting options
- Skip research — always check the codebase first

## Code Snippet Style Guide

Use **concise inline snippets** in the main sections and put **full implementations in an appendix**.

### Inline Code Format

Show only the relevant changes with context:

```python
def existing_function():
    ...existing logic...

    # NEW: Add feature X support
    if feature_x_enabled:
        self._configure_feature_x(data)

    ...rest of function...
```

### Guidelines

1. **Data structures are the exception**: Always show full definitions — they anchor the design
2. **Other sections**: Show what changes and where, not full implementations
3. **Use `...` or comments** to indicate existing/unchanged code
4. **Flag new sections** with `<!-- REVIEW: description -->` comments in the appendix

## Quick Reference

| Resource | Location |
|----------|----------|
| Design doc structure | `references/design-doc-structure.md` |
| Step-by-step workflow | `references/design-workflow.md` |
| Cinema 4D API research | `references/research-guide.md` |
| Architecture guide | `references/deadline-cloud-architecture.md` |
| External references | `references/external-references.md` |
| Output directory | `docs/designs/` |
| Repo architecture | `AGENTS.md` (repo root) |
