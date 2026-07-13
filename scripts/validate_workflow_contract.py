#!/usr/bin/env python3
"""Validate deterministic repository contracts for the Phase 1 n8n workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

WORKFLOW_PATH = Path("workflows/phase1/manual-health-check.json")
EXPECTED_VERSION_ID = "phase1-manual-health-check-v2"

REQUIRED_NODE_IDS = {
    "manual-trigger",
    "edit-fields",
    "phase1-code-node",
    "phase1-validate-payload",
    "phase1-if-status-ok",
    "phase1-mark-healthy",
    "phase1-mark-unhealthy",
    "phase1-build-success-response",
    "phase1-build-failure-response",
}

PROHIBITED_KEYS = {
    "instanceId",
    "webhookId",
}


def find_prohibited_keys(value: Any, path: str = "$") -> list[str]:
    """Return JSON paths containing prohibited runtime-specific keys."""
    violations: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if key in PROHIBITED_KEYS:
                violations.append(child_path)

            violations.extend(find_prohibited_keys(child, child_path))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(find_prohibited_keys(child, f"{path}[{index}]"))

    return violations


def validate_workflow(workflow_path: Path) -> list[str]:
    """Validate the workflow and return deterministic error messages."""
    errors: list[str] = []

    if not workflow_path.is_file():
        return [f"workflow file does not exist: {workflow_path}"]

    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [
            "workflow contains invalid JSON: "
            f"line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ]

    if not isinstance(workflow, dict):
        return ["workflow root must be a JSON object"]

    if "id" in workflow:
        errors.append("workflow must not contain a top-level runtime id")

    version_id = workflow.get("versionId")
    if version_id != EXPECTED_VERSION_ID:
        errors.append(
            "workflow versionId must be "
            f"'{EXPECTED_VERSION_ID}', found {version_id!r}"
        )

    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("workflow nodes must be a non-empty array")
        return errors

    node_ids: list[str] = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue

        node_id = node.get("id")

        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"nodes[{index}].id must be a non-empty string")
            continue

        node_ids.append(node_id)

    duplicate_node_ids = sorted(
        node_id for node_id in set(node_ids) if node_ids.count(node_id) > 1
    )

    for node_id in duplicate_node_ids:
        errors.append(f"duplicate node id: {node_id}")

    missing_node_ids = sorted(REQUIRED_NODE_IDS - set(node_ids))

    for node_id in missing_node_ids:
        errors.append(f"required node id is missing: {node_id}")

    for violation in find_prohibited_keys(workflow):
        errors.append(f"prohibited runtime key found: {violation}")

    return errors


def main() -> int:
    """Run workflow contract validation."""
    errors = validate_workflow(WORKFLOW_PATH)

    if errors:
        print(f"Workflow contract validation failed: {WORKFLOW_PATH}")

        for error in errors:
            print(f"ERROR: {error}")

        return 1

    print(f"Workflow contract validation passed: {WORKFLOW_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
