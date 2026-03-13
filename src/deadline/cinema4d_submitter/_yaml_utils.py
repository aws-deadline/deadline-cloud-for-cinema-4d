# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

# This module exists separately to avoid circular imports.
# Both cinema4d_render_submitter.py and tile_utils.py need _build_embedded_yaml,
# but cinema4d_render_submitter.py already imports from tile_utils.py.

from collections.abc import Set

from deadline.client.job_bundle._yaml import deadline_yaml_dump


def _build_embedded_yaml(data: dict[str, object], unquoted_keys: Set[str] = frozenset()) -> str:
    """Build a YAML string for use in embedded files that undergo parameter substitution.

    The Deadline service performs raw text substitution on ``{{Param.*}}``
    references *after* the job template is serialized.  This means any YAML
    quoting applied at serialization time can be broken by the substituted
    value.  For example, a single-quoted path like ``'/Users/artist's/file'``
    breaks because the apostrophe terminates the YAML string early.

    To handle this safely, values are split into two groups:

    * **Most values** are serialized with ``deadline_yaml_dump``, which
      properly handles YAML edge cases (e.g. quoting ``"true"`` so it stays
      a string, escaping tabs/newlines, preserving empty strings, etc.).
    * **Path values** (listed in *unquoted_keys*) are double-quoted.
      Double quotes safely handle apostrophes in paths and preserve empty
      strings after parameter substitution.  Double quotes in file paths
      are not a concern as they are illegal on Windows and extremely rare
      on Linux/macOS.

    When adding new fields:

    * If the value is a file path or a ``{{Param.*}}`` reference that will
      be substituted with a path, add its key to *unquoted_keys*.
    * Otherwise, leave it out of *unquoted_keys* so it gets the full YAML
      handling from ``deadline_yaml_dump``.
    """
    quoted_data = {k: v for k, v in data.items() if k not in unquoted_keys}
    unquoted_data = {k: v for k, v in data.items() if k in unquoted_keys}

    result = deadline_yaml_dump(quoted_data) if quoted_data else ""
    for key, value in unquoted_data.items():
        if value == "" or value is None:
            result += f"{key}: ''\n"
        else:
            result += f"{key}: {value}\n"
    return result
