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

REQUIRED_CONNECTIONS = {
    ("Manual Trigger", 0, "Edit Fields", 0),
    ("Edit Fields", 0, "Code in JavaScript", 0),
    ("Code in JavaScript", 0, "Validate Payload", 0),
    ("Validate Payload", 0, "If", 0),
    ("If", 0, "Mark Healthy", 0),
    ("If", 1, "Mark Unhealthy", 0),
    ("Mark Healthy", 0, "Build Success Response", 0),
    ("Mark Unhealthy", 0, "Build Failure Response", 0),
}

REQUIRED_NODE_CONTRACTS = {
    "manual-trigger": ("n8n-nodes-base.manualTrigger", 1),
    "edit-fields": ("n8n-nodes-base.set", 3.4),
    "phase1-code-node": ("n8n-nodes-base.code", 2),
    "phase1-validate-payload": ("n8n-nodes-base.if", 2.3),
    "phase1-if-status-ok": ("n8n-nodes-base.if", 2.3),
    "phase1-mark-healthy": ("n8n-nodes-base.set", 3.4),
    "phase1-mark-unhealthy": ("n8n-nodes-base.set", 3.4),
    "phase1-build-success-response": ("n8n-nodes-base.set", 3.4),
    "phase1-build-failure-response": ("n8n-nodes-base.set", 3.4),
}

REQUIRED_WORKFLOW_METADATA_TYPES = {
    "pinData": dict,
    "settings": dict,
    "tags": list,
    "nodeGroups": list,
}

REQUIRED_SETTINGS = {
    "executionOrder": "v1",
    "binaryMode": "separate",
    "availableInMCP": False,
}

REQUIRED_PARAMETER_IDS = {
    "status-assignment",
    "if-status-ok-condition",
    "validate-payload-status-present-condition",
    "health-check-result-passed-assignment",
    "health-check-result-failed-assignment",
    "workflow-assignment-phase1-build-success-response",
    "workflow-version-assignment-phase1-build-success-response",
    "response-schema-version-assignment-phase1-build-success-response",
    "execution-source-assignment-phase1-build-success-response",
    "execution-status-assignment-phase1-build-success-response",
    "workflow-assignment-phase1-build-failure-response",
    "workflow-version-assignment-phase1-build-failure-response",
    "response-schema-version-assignment-phase1-build-failure-response",
    "execution-source-assignment-phase1-build-failure-response",
    "execution-status-assignment-phase1-build-failure-response",
}


def collect_parameter_ids(value: Any) -> list[str]:
    """Collect string IDs recursively from a node parameters object."""
    identifiers: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "id" and isinstance(child, str):
                identifiers.append(child)

            identifiers.extend(collect_parameter_ids(child))

    elif isinstance(value, list):
        for child in value:
            identifiers.extend(collect_parameter_ids(child))

    return identifiers


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

    for field_name, expected_type in REQUIRED_WORKFLOW_METADATA_TYPES.items():
        if field_name not in workflow:
            errors.append(
                f"required workflow metadata field is missing: {field_name}"
            )
            continue

        field_value = workflow[field_name]

        if not isinstance(field_value, expected_type):
            errors.append(
                "workflow metadata field has invalid type: "
                f"{field_name} must be {expected_type.__name__}"
            )

    settings = workflow.get("settings")

    if isinstance(settings, dict):
        for setting_name, expected_value in REQUIRED_SETTINGS.items():
            actual_value = settings.get(setting_name)

            if actual_value != expected_value:
                errors.append(
                    "workflow setting must be "
                    f"{setting_name}={expected_value!r}, "
                    f"found {actual_value!r}"
                )

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
    node_names: list[str] = []
    parameter_ids: list[str] = []
    nodes_by_id: dict[str, dict[str, Any]] = {}

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append(f"nodes[{index}] must be an object")
            continue

        node_id = node.get("id")

        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"nodes[{index}].id must be a non-empty string")
            continue

        node_ids.append(node_id)
        nodes_by_id[node_id] = node

        node_name = node.get("name")

        if not isinstance(node_name, str) or not node_name.strip():
            errors.append(f"nodes[{index}].name must be a non-empty string")
        else:
            node_names.append(node_name)

        parameter_ids.extend(
            collect_parameter_ids(node.get("parameters", {}))
        )

    duplicate_node_ids = sorted(
        node_id for node_id in set(node_ids) if node_ids.count(node_id) > 1
    )

    for node_id in duplicate_node_ids:
        errors.append(f"duplicate node id: {node_id}")

    duplicate_node_names = sorted(
        node_name
        for node_name in set(node_names)
        if node_names.count(node_name) > 1
    )

    for node_name in duplicate_node_names:
        errors.append(f"duplicate node name: {node_name}")

    missing_node_ids = sorted(REQUIRED_NODE_IDS - set(node_ids))

    for node_id in missing_node_ids:
        errors.append(f"required node id is missing: {node_id}")

    for node_id in sorted(REQUIRED_NODE_CONTRACTS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        expected_type, expected_type_version = REQUIRED_NODE_CONTRACTS[node_id]
        actual_type = node.get("type")
        actual_type_version = node.get("typeVersion")

        if actual_type != expected_type:
            errors.append(
                f"node type mismatch for {node_id}: "
                f"expected {expected_type!r}, found {actual_type!r}"
            )

        if actual_type_version != expected_type_version:
            errors.append(
                f"node typeVersion mismatch for {node_id}: "
                f"expected {expected_type_version!r}, "
                f"found {actual_type_version!r}"
            )

    duplicate_parameter_ids = sorted(
        parameter_id
        for parameter_id in set(parameter_ids)
        if parameter_ids.count(parameter_id) > 1
    )

    for parameter_id in duplicate_parameter_ids:
        errors.append(f"duplicate parameter id: {parameter_id}")

    missing_parameter_ids = sorted(
        REQUIRED_PARAMETER_IDS - set(parameter_ids)
    )

    for parameter_id in missing_parameter_ids:
        errors.append(f"required parameter id is missing: {parameter_id}")

    connections = workflow.get("connections")

    if not isinstance(connections, dict):
        errors.append("workflow connections must be an object")
    else:
        actual_connections: set[tuple[str, int, str, int]] = set()
        node_name_set = set(node_names)

        for source_name, connection_types in connections.items():
            if source_name not in node_name_set:
                errors.append(
                    f"connection source references missing node: {source_name}"
                )
            if not isinstance(connection_types, dict):
                continue

            outputs = connection_types.get("main", [])

            if not isinstance(outputs, list):
                continue

            for output_index, targets in enumerate(outputs):
                if not isinstance(targets, list):
                    continue

                for target in targets:
                    if not isinstance(target, dict):
                        continue

                    target_name = target.get("node")
                    target_input = target.get("index", 0)

                    if isinstance(target_name, str) and isinstance(
                        target_input,
                        int,
                    ):
                        if target_name not in node_name_set:
                            errors.append(
                                "connection target references missing node: "
                                f"{target_name}"
                            )

                        actual_connections.add(
                            (
                                source_name,
                                output_index,
                                target_name,
                                target_input,
                            )
                        )

        for connection in sorted(REQUIRED_CONNECTIONS - actual_connections):
            source_name, output_index, target_name, target_input = connection
            errors.append(
                "required connection is missing: "
                f"{source_name}[{output_index}] -> "
                f"{target_name}[{target_input}]"
            )

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
