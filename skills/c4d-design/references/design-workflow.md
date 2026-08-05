# Cinema 4D Design Workflow Guide

This guide walks through creating a comprehensive design document for a new Cinema 4D feature.

## Step 1: Understand the Feature Request

Before starting the design:
1. Clarify the user's goal and expected outcome
2. Identify which renderers are affected (Redshift, Arnold, V-Ray, Physical, etc.)
3. Determine if this is a submitter change, adaptor change, or both
4. Determine if this affects Windows, macOS, Linux, or all platforms
5. Ask clarifying questions if the scope is unclear

## Step 2: Research Phase

### 2.1 Search Cinema 4D Documentation

Look up relevant Cinema 4D Python APIs:
- The `c4d` module and its classes
- Renderer-specific settings and properties
- Scene object access patterns
- Take system APIs

Key search terms:
- "Cinema 4D Python API [topic]"
- "c4d module [class name]"
- "Redshift Cinema 4D [feature]"
- "Cinema 4D SDK [topic]"

### 2.2 Check Existing Implementation

Review the current codebase:
- How does the submitter handle similar features? (`cinema4d_render_submitter.py`, `data_classes.py`)
- How does the adaptor handle similar actions? (`cinema4d_handler.py`, `cinema4d_client.py`)
- What patterns exist in the job templates? (`adaptor_cinema4d_job_template.yaml`)
- How are takes handled? (`takes.py`)
- How are assets discovered? (`assets.py`)

### 2.3 Internet Research

Search for:
- Community solutions and workarounds
- Known issues and limitations
- Version compatibility notes (Cinema 4D 2024 vs 2025 vs 2026)
- Renderer-specific documentation (Redshift, Arnold, V-Ray)

## Step 3: Design the Data Structures

Data structures anchor the design — **always include full definitions** for new types:

```python
from typing import Any, Optional
from dataclasses import dataclass
from enum import Enum

class FeatureMode(Enum):
    """Mode options for Feature X."""
    OPTION_A = "option_a"
    OPTION_B = "option_b"

@dataclass
class FeatureSettings:
    """Settings for Feature X workflow."""

    enabled: bool = False
    mode: FeatureMode = FeatureMode.OPTION_A
    output_path: Optional[str] = None
```

Consider:
- What data flows from submitter to adaptor?
- What state needs to be maintained during rendering?
- How does this interact with the take system?
- Does this affect asset discovery?

**Note:** Data structures are the exception to the "concise snippets" rule — show them in full since they anchor the entire design.

## Step 4: Design the UX

Sketch out the submitter dialog changes:

1. **Control Type**: Dropdown, checkbox, text field, etc.
2. **Placement**: Which group/section does it belong to?
3. **Default Value**: What's the sensible default?
4. **Validation**: What values are valid?
5. **Dependencies**: Does it depend on other settings?
6. **Take Interaction**: Does this setting vary per take?

Example:
```
Group: Render Settings
├── [Checkbox] Enable Feature X (default: unchecked)
│   └── [Dropdown] Feature X Mode (visible when enabled)
│       ├── Option A
│       └── Option B
└── [Text Field] Custom Path (optional)
```

## Step 5: Design Job Template Changes

Define the job bundle modifications:

```yaml
parameterDefinitions:
  - name: FeatureXEnabled
    type: STRING
    default: "false"
    allowedValues: ["true", "false"]

  - name: FeatureXMode
    type: STRING
    default: "option_a"
    allowedValues: ["option_a", "option_b"]
    userInterface:
      control: DROPDOWN
      label: "Feature X Mode"
```

Consider:
- Parameter types and constraints
- Conditional parameters
- Asset references
- How parameters map to adaptor init_data or run_data

## Step 6: Design Adaptor and Client Changes

Plan the runtime implementation using **concise inline snippets**:

### Adaptor Changes (Cinema4DAdaptor)
```python
class Cinema4DAdaptor:
    def on_run(self, run_data: dict) -> None:
        ...existing logic...

        # NEW: Send feature X action
        if run_data.get("feature_x_enabled"):
            self._client.enqueue_action("feature_x", {"mode": run_data["feature_x_mode"]})
```

### Client Changes (Cinema4DClient)
```python
class Cinema4DHandler:
    def __init__(self):
        ...existing init...

        # NEW: Register feature X action
        self.action_dict["feature_x"] = self.configure_feature_x

    def configure_feature_x(self, data: dict) -> None:
        """Configure Feature X before rendering."""
        # See Appendix A.1 for full implementation
        ...
```

Put full implementations in the **Appendix** section with review flags.

## Step 7: Plan Testing

### Unit Tests
```python
def test_feature_x_configuration(self):
    """Test Feature X is correctly configured."""
    handler = Cinema4DHandler()
    handler.configure_feature_x({"enabled": True, "mode": "option_a"})
    # Verify expected behavior
```

### Integration Tests
Consider adding a new case under `test/integ/test_cases/` if the feature
affects the submitter UI, job bundle, or rendering output. Bundle validation
runs on Windows and macOS; rendering assertions run on Windows. Follow
`test/AGENTS.md` and the `c4d-dev` skill's xa11y authoring workflow.

## Step 8: Document Files to Modify

Create a summary table:

| File | Changes |
|------|---------|
| `src/deadline/cinema4d_submitter/data_classes.py` | Add data models |
| `src/deadline/cinema4d_submitter/ui/...` | Add UI controls |
| `src/deadline/cinema4d_submitter/adaptor_cinema4d_job_template.yaml` | Add parameters |
| `src/deadline/cinema4d_adaptor/Cinema4DAdaptor/adaptor.py` | Add adaptor logic |
| `src/deadline/cinema4d_adaptor/Cinema4DClient/cinema4d_handler.py` | Add handler method |
| `test/unit/.../test_handler.py` | Add unit tests |

## Common Pitfalls

1. **Forgetting multi-renderer support**: Always consider Redshift, Arnold, V-Ray, and Physical renderer
2. **Missing platform handling**: Cinema 4D runs on Windows, macOS, and Linux
3. **Take system interaction**: Features may need to work differently per take
4. **Schema versioning**: Changes to `init_data.schema.json` or `run_data.schema.json` require updating `integration_data_interface_version`
5. **Asset discovery**: New file references need to be included in asset discovery (`assets.py`)
6. **Path mapping**: Cross-platform path handling for worker vs. workstation paths

## Step 9: Create the Appendix

Put all full code implementations in a clearly marked appendix at the end of the design document.

### Appendix Format

```markdown
---

## Appendix: Full Code Implementations

<!-- REVIEW: Brief description of what's new -->

### A.1 Cinema4DHandler.configure_feature (Full Implementation)

**File:** `src/deadline/cinema4d_adaptor/Cinema4DClient/cinema4d_handler.py`

\`\`\`python
def configure_feature(self, data: dict) -> None:
    """
    Full docstring here.
    """
    # Complete implementation
    ...
\`\`\`
```

### Guidelines

1. **Flag sections for review** with `<!-- REVIEW: description -->` HTML comments
2. **Include file paths** for each code block
3. **Number appendix sections** (A.1, A.2, etc.) for easy reference
4. **Don't include review tags** in final generated code — they're for design review only
5. **Reference appendix from main sections** with "See Appendix A.X for full implementation"
