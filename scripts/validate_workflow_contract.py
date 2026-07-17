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
    "manual-trigger": (
        "Manual Trigger",
        "n8n-nodes-base.manualTrigger",
        1,
    ),
    "edit-fields": (
        "Edit Fields",
        "n8n-nodes-base.set",
        3.4,
    ),
    "phase1-code-node": (
        "Code in JavaScript",
        "n8n-nodes-base.code",
        2,
    ),
    "phase1-validate-payload": (
        "Validate Payload",
        "n8n-nodes-base.if",
        2.3,
    ),
    "phase1-if-status-ok": (
        "If",
        "n8n-nodes-base.if",
        2.3,
    ),
    "phase1-mark-healthy": (
        "Mark Healthy",
        "n8n-nodes-base.set",
        3.4,
    ),
    "phase1-mark-unhealthy": (
        "Mark Unhealthy",
        "n8n-nodes-base.set",
        3.4,
    ),
    "phase1-build-success-response": (
        "Build Success Response",
        "n8n-nodes-base.set",
        3.4,
    ),
    "phase1-build-failure-response": (
        "Build Failure Response",
        "n8n-nodes-base.set",
        3.4,
    ),
}

REQUIRED_NODE_POSITIONS = {
    "manual-trigger": [0, 0],
    "edit-fields": [208, 0],
    "phase1-code-node": [416, 0],
    "phase1-validate-payload": [64, -48],
    "phase1-if-status-ok": [592, 0],
    "phase1-mark-healthy": [240, -144],
    "phase1-mark-unhealthy": [240, 48],
    "phase1-build-success-response": [448, -144],
    "phase1-build-failure-response": [448, 48],
}

REQUIRED_BRANCH_ASSIGNMENTS = {
    "edit-fields": [
        (
            "status-assignment",
            "status",
            "ok",
            "string",
        ),
    ],
    "phase1-mark-healthy": [
        (
            "health-check-result-passed-assignment",
            "healthCheckResult",
            "passed",
            "string",
        ),
    ],
    "phase1-mark-unhealthy": [
        (
            "health-check-result-failed-assignment",
            "healthCheckResult",
            "failed",
            "string",
        ),
    ],
}

REQUIRED_INCLUDE_OTHER_FIELDS = {
    "phase1-mark-healthy": True,
    "phase1-mark-unhealthy": True,
    "phase1-build-success-response": True,
    "phase1-build-failure-response": True,
}

REQUIRED_BRANCH_CONDITIONS = {
    "phase1-if-status-ok": [
        (
            "if-status-ok-condition",
            "={{ $json.status }}",
            {
                "operation": "equals",
                "type": "string",
            },
            "ok",
        ),
    ],
    "phase1-validate-payload": [
        (
            "validate-payload-status-present-condition",
            "={{ $json.status }}",
            {
                "operation": "notEmpty",
                "singleValue": True,
                "type": "string",
            },
            "",
        ),
    ],
}

REQUIRED_CONDITION_OPTIONS = {
    "caseSensitive": True,
    "leftValue": "",
    "typeValidation": "strict",
    "version": 3,
}

REQUIRED_CODE_NODE_PARAMETERS = {
    "phase1-code-node": {
        "jsCode": (
            "return items.map(item => {\n"
            "  item.json.checkedBy = 'code-node';\n"
            "  return item;\n"
            "});"
        ),
    },
}

REQUIRED_SET_NODE_OPTIONS = {
    "edit-fields": {},
    "phase1-mark-healthy": {},
    "phase1-mark-unhealthy": {},
    "phase1-build-success-response": {},
    "phase1-build-failure-response": {},
}

REQUIRED_RESPONSE_ASSIGNMENTS = {
    "phase1-build-success-response": [
        (
            "workflow-assignment-phase1-build-success-response",
            "workflow",
            "manual-health-check",
            "string",
        ),
        (
            "workflow-version-assignment-phase1-build-success-response",
            "workflowVersion",
            "phase1-v1",
            "string",
        ),
        (
            "response-schema-version-assignment-phase1-build-success-response",
            "responseSchemaVersion",
            "health-check-response-v1",
            "string",
        ),
        (
            "execution-source-assignment-phase1-build-success-response",
            "executionSource",
            "manual-trigger",
            "string",
        ),
        (
            "execution-status-assignment-phase1-build-success-response",
            "executionStatus",
            "completed",
            "string",
        ),
    ],
    "phase1-build-failure-response": [
        (
            "workflow-assignment-phase1-build-failure-response",
            "workflow",
            "manual-health-check",
            "string",
        ),
        (
            "workflow-version-assignment-phase1-build-failure-response",
            "workflowVersion",
            "phase1-v1",
            "string",
        ),
        (
            "response-schema-version-assignment-phase1-build-failure-response",
            "responseSchemaVersion",
            "health-check-response-v1",
            "string",
        ),
        (
            "execution-source-assignment-phase1-build-failure-response",
            "executionSource",
            "manual-trigger",
            "string",
        ),
        (
            "execution-status-assignment-phase1-build-failure-response",
            "executionStatus",
            "completed",
            "string",
        ),
    ],
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

    node_id_set = set(node_ids)

    missing_node_ids = sorted(REQUIRED_NODE_IDS - node_id_set)

    for node_id in missing_node_ids:
        errors.append(f"required node id is missing: {node_id}")

    unexpected_node_ids = sorted(node_id_set - REQUIRED_NODE_IDS)

    for node_id in unexpected_node_ids:
        errors.append(f"unexpected node id found: {node_id}")

    for node_id in sorted(REQUIRED_NODE_CONTRACTS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        (
            expected_name,
            expected_type,
            expected_type_version,
        ) = REQUIRED_NODE_CONTRACTS[node_id]

        actual_name = node.get("name")
        actual_type = node.get("type")
        actual_type_version = node.get("typeVersion")

        if actual_name != expected_name:
            errors.append(
                f"node name mismatch for {node_id}: "
                f"expected {expected_name!r}, found {actual_name!r}"
            )

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

    for node_id in sorted(REQUIRED_NODE_POSITIONS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        expected_position = REQUIRED_NODE_POSITIONS[node_id]
        actual_position = node.get("position")

        if actual_position != expected_position:
            errors.append(
                f"node position mismatch for {node_id}: "
                f"expected {expected_position!r}, "
                f"found {actual_position!r}"
            )

    for node_id in sorted(REQUIRED_BRANCH_ASSIGNMENTS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        assignments = (
            node.get("parameters", {})
            .get("assignments", {})
            .get("assignments")
        )

        expected_assignments = REQUIRED_BRANCH_ASSIGNMENTS[node_id]

        if not isinstance(assignments, list):
            errors.append(
                f"branch assignments must be a list for {node_id}"
            )
            continue

        actual_assignments = [
            (
                assignment.get("id"),
                assignment.get("name"),
                assignment.get("value"),
                assignment.get("type"),
            )
            if isinstance(assignment, dict)
            else (None, None, None, None)
            for assignment in assignments
        ]

        if actual_assignments != expected_assignments:
            errors.append(
                f"branch assignment contract mismatch for {node_id}: "
                f"expected {expected_assignments!r}, "
                f"found {actual_assignments!r}"
            )

    for node_id in sorted(REQUIRED_INCLUDE_OTHER_FIELDS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        actual_include_other_fields = (
            node.get("parameters", {}).get("includeOtherFields")
        )
        expected_include_other_fields = (
            REQUIRED_INCLUDE_OTHER_FIELDS[node_id]
        )

        if actual_include_other_fields != expected_include_other_fields:
            errors.append(
                f"includeOtherFields mismatch for {node_id}: "
                f"expected {expected_include_other_fields!r}, "
                f"found {actual_include_other_fields!r}"
            )

    for node_id in sorted(REQUIRED_BRANCH_CONDITIONS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        condition_container = (
            node.get("parameters", {})
            .get("conditions", {})
        )
        conditions = condition_container.get("conditions")
        combinator = condition_container.get("combinator")
        condition_options = condition_container.get("options")

        expected_conditions = REQUIRED_BRANCH_CONDITIONS[node_id]

        if not isinstance(conditions, list):
            errors.append(
                f"branch conditions must be a list for {node_id}"
            )
            continue

        actual_conditions = [
            (
                condition.get("id"),
                condition.get("leftValue"),
                condition.get("operator"),
                condition.get("rightValue"),
            )
            if isinstance(condition, dict)
            else (None, None, None, None)
            for condition in conditions
        ]

        if actual_conditions != expected_conditions:
            errors.append(
                f"branch condition contract mismatch for {node_id}: "
                f"expected {expected_conditions!r}, "
                f"found {actual_conditions!r}"
            )

        if combinator != "and":
            errors.append(
                f"branch condition combinator mismatch for {node_id}: "
                f"expected 'and', found {combinator!r}"
            )

        if condition_options != REQUIRED_CONDITION_OPTIONS:
            errors.append(
                f"branch condition options mismatch for {node_id}: "
                f"expected {REQUIRED_CONDITION_OPTIONS!r}, "
                f"found {condition_options!r}"
            )

    for node_id in sorted(REQUIRED_CODE_NODE_PARAMETERS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        actual_parameters = node.get("parameters")
        expected_parameters = REQUIRED_CODE_NODE_PARAMETERS[node_id]

        if actual_parameters != expected_parameters:
            errors.append(
                f"code node parameter contract mismatch for {node_id}: "
                f"expected {expected_parameters!r}, "
                f"found {actual_parameters!r}"
            )

    for node_id in sorted(REQUIRED_SET_NODE_OPTIONS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        actual_options = node.get("parameters", {}).get("options")
        expected_options = REQUIRED_SET_NODE_OPTIONS[node_id]

        if actual_options != expected_options:
            errors.append(
                f"set node options mismatch for {node_id}: "
                f"expected {expected_options!r}, "
                f"found {actual_options!r}"
            )

    for node_id in sorted(REQUIRED_RESPONSE_ASSIGNMENTS):
        node = nodes_by_id.get(node_id)

        if node is None:
            continue

        assignments = (
            node.get("parameters", {})
            .get("assignments", {})
            .get("assignments")
        )

        expected_assignments = REQUIRED_RESPONSE_ASSIGNMENTS[node_id]

        if not isinstance(assignments, list):
            errors.append(
                f"response assignments must be a list for {node_id}"
            )
            continue

        if len(assignments) != len(expected_assignments):
            errors.append(
                f"response assignment count mismatch for {node_id}: "
                f"expected {len(expected_assignments)}, "
                f"found {len(assignments)}"
            )
            continue

        actual_assignments: list[tuple[Any, Any, Any, Any]] = []

        for assignment in assignments:
            if not isinstance(assignment, dict):
                actual_assignments.append((None, None, None, None))
                continue

            actual_assignments.append(
                (
                    assignment.get("id"),
                    assignment.get("name"),
                    assignment.get("value"),
                    assignment.get("type"),
                )
            )

        for index, (
            expected_assignment,
            actual_assignment,
        ) in enumerate(zip(expected_assignments, actual_assignments)):
            if actual_assignment != expected_assignment:
                errors.append(
                    f"response assignment mismatch for {node_id} "
                    f"at index {index}: expected "
                    f"{expected_assignment!r}, found "
                    f"{actual_assignment!r}"
                )

    duplicate_parameter_ids = sorted(
        parameter_id
        for parameter_id in set(parameter_ids)
        if parameter_ids.count(parameter_id) > 1
    )

    for parameter_id in duplicate_parameter_ids:
        errors.append(f"duplicate parameter id: {parameter_id}")

    parameter_id_set = set(parameter_ids)

    missing_parameter_ids = sorted(
        REQUIRED_PARAMETER_IDS - parameter_id_set
    )

    for parameter_id in missing_parameter_ids:
        errors.append(f"required parameter id is missing: {parameter_id}")

    unexpected_parameter_ids = sorted(
        parameter_id_set - REQUIRED_PARAMETER_IDS
    )

    for parameter_id in unexpected_parameter_ids:
        errors.append(f"unexpected parameter id found: {parameter_id}")

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

        for connection in sorted(actual_connections - REQUIRED_CONNECTIONS):
            source_name, output_index, target_name, target_input = connection
            errors.append(
                "unexpected connection found: "
                f"{source_name}[{output_index}] -> "
                f"{target_name}[{target_input}]"
            )

    for violation in find_prohibited_keys(workflow):
        errors.append(f"prohibited runtime key found: {violation}")

    return errors


def main() -> int:
    """Run workflow contract validation."""
    if len(sys.argv) > 2:
        print(
            "Usage: validate_workflow_contract.py [workflow-path]",
            file=sys.stderr,
        )
        return 2

    workflow_path = (
        Path(sys.argv[1])
        if len(sys.argv) == 2
        else WORKFLOW_PATH
    )

    errors = validate_workflow(workflow_path)

    if errors:
        print(f"Workflow contract validation failed: {workflow_path}")

        for error in errors:
            print(f"ERROR: {error}")

        return 1

    print(f"Workflow contract validation passed: {workflow_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
