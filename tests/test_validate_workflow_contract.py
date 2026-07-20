#!/usr/bin/env python3
"""Tests for the workflow contract validator."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts/validate_workflow_contract.py"
WORKFLOW_PATH = (
    REPOSITORY_ROOT / "workflows/phase1/manual-health-check.json"
)


def load_validator_module() -> ModuleType:
    """Load the validator script as an importable module."""
    spec = importlib.util.spec_from_file_location(
        "validate_workflow_contract",
        VALIDATOR_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator: {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator_module()


class WorkflowContractValidatorTests(unittest.TestCase):
    """Verify positive and negative workflow contract behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.valid_workflow = json.loads(
            WORKFLOW_PATH.read_text(encoding="utf-8")
        )

    def validate_copy(self, workflow: dict[str, Any]) -> list[str]:
        """Write a temporary workflow and return validation errors."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            workflow_path = Path(temporary_directory) / "workflow.json"
            workflow_path.write_text(
                json.dumps(workflow),
                encoding="utf-8",
            )
            return VALIDATOR.validate_workflow(workflow_path)

    def test_repository_workflow_passes(self) -> None:
        errors = VALIDATOR.validate_workflow(WORKFLOW_PATH)

        self.assertEqual([], errors)

    def test_missing_required_node_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"] = [
            node
            for node in workflow["nodes"]
            if node.get("id") != "phase1-code-node"
        ]

        errors = self.validate_copy(workflow)

        self.assertIn(
            "required node id is missing: phase1-code-node",
            errors,
        )

    def test_duplicate_node_id_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"][1]["id"] = workflow["nodes"][0]["id"]

        errors = self.validate_copy(workflow)

        self.assertIn(
            f"duplicate node id: {workflow['nodes'][0]['id']}",
            errors,
        )

    def test_prohibited_runtime_key_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["metadata"] = {
            "instanceId": "temporary-runtime-value",
        }

        errors = self.validate_copy(workflow)

        self.assertIn(
            "prohibited runtime key found: $.metadata.instanceId",
            errors,
        )

    def test_missing_required_connection_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["connections"]["If"]["main"][1] = []

        errors = self.validate_copy(workflow)

        self.assertIn(
            "required connection is missing: If[1] -> Mark Unhealthy[0]",
            errors,
        )

    def test_duplicate_node_name_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"][1]["name"] = workflow["nodes"][0]["name"]

        errors = self.validate_copy(workflow)

        self.assertIn(
            f"duplicate node name: {workflow['nodes'][0]['name']}",
            errors,
        )

    def test_missing_connection_source_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["connections"]["Missing Source"] = {
            "main": [[]],
        }

        errors = self.validate_copy(workflow)

        self.assertIn(
            "connection source references missing node: Missing Source",
            errors,
        )

    def test_missing_connection_target_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["connections"]["Manual Trigger"]["main"][0][0][
            "node"
        ] = "Missing Target"

        errors = self.validate_copy(workflow)

        self.assertIn(
            "connection target references missing node: Missing Target",
            errors,
        )

    def test_missing_required_parameter_id_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"][1]["parameters"]["assignments"]["assignments"][0][
            "id"
        ] = "temporary-status-assignment"

        errors = self.validate_copy(workflow)

        self.assertIn(
            "required parameter id is missing: status-assignment",
            errors,
        )

    def test_duplicate_parameter_id_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"][4]["parameters"]["assignments"]["assignments"][0][
            "id"
        ] = "status-assignment"

        errors = self.validate_copy(workflow)

        self.assertIn(
            "duplicate parameter id: status-assignment",
            errors,
        )

    def test_missing_workflow_metadata_field_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        del workflow["pinData"]

        errors = self.validate_copy(workflow)

        self.assertIn(
            "required workflow metadata field is missing: pinData",
            errors,
        )

    def test_invalid_workflow_metadata_type_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodeGroups"] = {}

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow metadata field has invalid type: "
            "nodeGroups must be list",
            errors,
        )

    def test_non_empty_pin_data_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["pinData"] = {
            "Manual Trigger": [
                {
                    "json": {
                        "status": "pinned",
                    }
                }
            ]
        }

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow pinData must be empty, found "
            "{'Manual Trigger': [{'json': {'status': 'pinned'}}]}",
            errors,
        )

    def test_non_empty_workflow_tags_are_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["tags"] = [
            {
                "id": "phase1-tag",
                "name": "Phase 1",
            }
        ]

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow tags must be empty, found "
            "[{'id': 'phase1-tag', 'name': 'Phase 1'}]",
            errors,
        )

    def test_non_empty_node_groups_are_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodeGroups"] = [
            {
                "id": "phase1-group",
                "name": "Phase 1 Nodes",
            }
        ]

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow nodeGroups must be empty, found "
            "[{'id': 'phase1-group', 'name': 'Phase 1 Nodes'}]",
            errors,
        )

    def test_unexpected_workflow_key_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["unexpectedMetadata"] = True

        errors = self.validate_copy(workflow)

        self.assertIn(
            "unexpected workflow field found: unexpectedMetadata",
            errors,
        )

    def test_workflow_name_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["name"] = "Renamed Health Check"

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow name must be 'Phase 1 - Manual Health Check', "
            "found 'Renamed Health Check'",
            errors,
        )

    def test_active_workflow_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["active"] = True

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow active state must be False, found True",
            errors,
        )

    def test_invalid_workflow_setting_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["settings"]["executionOrder"] = "legacy"

        errors = self.validate_copy(workflow)

        self.assertIn(
            "workflow setting must be executionOrder='v1', "
            "found 'legacy'",
            errors,
        )

    def test_unexpected_workflow_setting_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["settings"]["unexpectedSetting"] = True

        errors = self.validate_copy(workflow)

        self.assertIn(
            "unexpected workflow setting found: unexpectedSetting",
            errors,
        )

    def test_node_type_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-code-node":
                node["type"] = "n8n-nodes-base.set"
                break
        else:
            self.fail("phase1-code-node was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "node type mismatch for phase1-code-node: "
            "expected 'n8n-nodes-base.code', "
            "found 'n8n-nodes-base.set'",
            errors,
        )

    def test_node_type_version_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-if-status-ok":
                node["typeVersion"] = 1
                break
        else:
            self.fail("phase1-if-status-ok was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "node typeVersion mismatch for phase1-if-status-ok: "
            "expected 2.3, found 1",
            errors,
        )

    def test_node_position_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-code-node":
                node["position"] = [999, 999]
                break
        else:
            self.fail("phase1-code-node was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "node position mismatch for phase1-code-node: "
            "expected [416, 0], found [999, 999]",
            errors,
        )

    def test_unexpected_connection_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["connections"]["Edit Fields"]["main"][0].append(
            {
                "node": "Build Success Response",
                "type": "main",
                "index": 0,
            }
        )

        errors = self.validate_copy(workflow)

        self.assertIn(
            "unexpected connection found: "
            "Edit Fields[0] -> Build Success Response[0]",
            errors,
        )

    def test_unexpected_node_id_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"].append(
            {
                "id": "unexpected-node",
                "name": "Unexpected Node",
                "type": "n8n-nodes-base.noOp",
                "typeVersion": 1,
                "position": [0, 0],
                "parameters": {},
            }
        )

        errors = self.validate_copy(workflow)

        self.assertIn(
            "unexpected node id found: unexpected-node",
            errors,
        )

    def test_node_name_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-code-node":
                node["name"] = "Renamed Code Node"
                break
        else:
            self.fail("phase1-code-node was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "node name mismatch for phase1-code-node: "
            "expected 'Code in JavaScript', "
            "found 'Renamed Code Node'",
            errors,
        )

    def test_unexpected_parameter_id_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)
        workflow["nodes"][1]["parameters"]["assignments"]["assignments"].append(
            {
                "id": "unexpected-assignment-id",
                "name": "temporaryField",
                "value": "temporaryValue",
                "type": "string",
            }
        )

        errors = self.validate_copy(workflow)

        self.assertIn(
            "unexpected parameter id found: unexpected-assignment-id",
            errors,
        )

    def test_response_assignment_value_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-build-success-response":
                assignments = (
                    node["parameters"]["assignments"]["assignments"]
                )
                assignments[4]["value"] = "rejected"
                break
        else:
            self.fail("phase1-build-success-response was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "response assignment mismatch for "
                    "phase1-build-success-response at index 4"
                )
                for error in errors
            )
        )

    def test_response_assignment_order_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-build-failure-response":
                assignments = (
                    node["parameters"]["assignments"]["assignments"]
                )
                assignments[0], assignments[1] = (
                    assignments[1],
                    assignments[0],
                )
                break
        else:
            self.fail("phase1-build-failure-response was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "response assignment mismatch for "
                    "phase1-build-failure-response at index 0"
                )
                for error in errors
            )
        )

    def _assert_edit_fields_contract_rejected(self, mutate_workflow):
        workflow_path = Path(
            "workflows/phase1/manual-health-check.json"
        )
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

        edit_fields = next(
            node for node in workflow["nodes"]
            if node["id"] == "edit-fields"
        )

        mutate_workflow(edit_fields)

        with tempfile.TemporaryDirectory() as temporary_directory:
            candidate_path = (
                Path(temporary_directory) / "manual-health-check.json"
            )
            candidate_path.write_text(
                json.dumps(workflow, indent=2) + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/validate_workflow_contract.py",
                    str(candidate_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        output = f"{result.stdout}\n{result.stderr}"

        self.assertNotEqual(
            result.returncode,
            0,
            msg="The mutated Edit Fields contract was unexpectedly accepted.",
        )
        self.assertIn("edit-fields", output)

    def test_edit_fields_assignment_id_mismatch_is_rejected(self):
        def mutate(node):
            assignment = node["parameters"]["assignments"]["assignments"][0]
            assignment["id"] = "unexpected-status-assignment"

        self._assert_edit_fields_contract_rejected(mutate)

    def test_edit_fields_assignment_name_mismatch_is_rejected(self):
        def mutate(node):
            assignment = node["parameters"]["assignments"]["assignments"][0]
            assignment["name"] = "unexpected-status"

        self._assert_edit_fields_contract_rejected(mutate)

    def test_edit_fields_assignment_type_mismatch_is_rejected(self):
        def mutate(node):
            assignment = node["parameters"]["assignments"]["assignments"][0]
            assignment["type"] = "boolean"

        self._assert_edit_fields_contract_rejected(mutate)

    def test_edit_fields_assignment_value_mismatch_is_rejected(self):
        def mutate(node):
            assignment = node["parameters"]["assignments"]["assignments"][0]
            assignment["value"] = "not-ok"

        self._assert_edit_fields_contract_rejected(mutate)

    def test_edit_fields_missing_assignment_is_rejected(self):
        def mutate(node):
            node["parameters"]["assignments"]["assignments"] = []

        self._assert_edit_fields_contract_rejected(mutate)

    def test_edit_fields_unexpected_assignment_is_rejected(self):
        def mutate(node):
            assignments = node["parameters"]["assignments"]["assignments"]
            assignments.append(
                {
                    "id": "unexpected-assignment",
                    "name": "unexpected",
                    "type": "string",
                    "value": "unexpected",
                }
            )

        self._assert_edit_fields_contract_rejected(mutate)

    def test_mark_healthy_assignment_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-mark-healthy":
                assignment = (
                    node["parameters"]["assignments"]["assignments"][0]
                )
                assignment["value"] = "failed"
                break
        else:
            self.fail("phase1-mark-healthy was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "branch assignment contract mismatch for "
                    "phase1-mark-healthy"
                )
                for error in errors
            )
        )

    def test_mark_unhealthy_assignment_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-mark-unhealthy":
                assignment = (
                    node["parameters"]["assignments"]["assignments"][0]
                )
                assignment["value"] = "passed"
                break
        else:
            self.fail("phase1-mark-unhealthy was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "branch assignment contract mismatch for "
                    "phase1-mark-unhealthy"
                )
                for error in errors
            )
        )

    def test_health_outcome_include_other_fields_is_required(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-mark-healthy":
                node["parameters"]["includeOtherFields"] = False
                break
        else:
            self.fail("phase1-mark-healthy was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "includeOtherFields mismatch for phase1-mark-healthy: "
            "expected True, found False",
            errors,
        )

    def test_branch_condition_operator_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-if-status-ok":
                condition = (
                    node["parameters"]["conditions"]["conditions"][0]
                )
                condition["operator"]["operation"] = "notEquals"
                break
        else:
            self.fail("phase1-if-status-ok was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "branch condition contract mismatch for "
                    "phase1-if-status-ok"
                )
                for error in errors
            )
        )

    def test_branch_condition_value_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-validate-payload":
                condition = (
                    node["parameters"]["conditions"]["conditions"][0]
                )
                condition["rightValue"] = "unexpected"
                break
        else:
            self.fail("phase1-validate-payload was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "branch condition contract mismatch for "
                    "phase1-validate-payload"
                )
                for error in errors
            )
        )

    def test_branch_condition_combinator_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-if-status-ok":
                node["parameters"]["conditions"]["combinator"] = "or"
                break
        else:
            self.fail("phase1-if-status-ok was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "branch condition combinator mismatch for "
            "phase1-if-status-ok: expected 'and', found 'or'",
            errors,
        )

    def test_branch_condition_options_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-validate-payload":
                node["parameters"]["conditions"]["options"][
                    "typeValidation"
                ] = "loose"
                break
        else:
            self.fail("phase1-validate-payload was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "branch condition options mismatch for "
                    "phase1-validate-payload"
                )
                for error in errors
            )
        )

    def test_code_node_javascript_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-code-node":
                node["parameters"]["jsCode"] = (
                    "return items;"
                )
                break
        else:
            self.fail("phase1-code-node was not found")

        errors = self.validate_copy(workflow)

        self.assertTrue(
            any(
                error.startswith(
                    "code node parameter contract mismatch for "
                    "phase1-code-node"
                )
                for error in errors
            )
        )

    def test_success_response_include_other_fields_is_required(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-build-success-response":
                node["parameters"]["includeOtherFields"] = False
                break
        else:
            self.fail("phase1-build-success-response was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "includeOtherFields mismatch for "
            "phase1-build-success-response: expected True, found False",
            errors,
        )

    def test_failure_response_include_other_fields_is_required(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-build-failure-response":
                node["parameters"]["includeOtherFields"] = False
                break
        else:
            self.fail("phase1-build-failure-response was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "includeOtherFields mismatch for "
            "phase1-build-failure-response: expected True, found False",
            errors,
        )

    def test_edit_fields_options_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "edit-fields":
                node["parameters"]["options"] = {
                    "unexpected": True,
                }
                break
        else:
            self.fail("edit-fields was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "set node options mismatch for edit-fields: "
            "expected {}, found {'unexpected': True}",
            errors,
        )

    def test_success_response_options_mismatch_is_rejected(self) -> None:
        workflow = copy.deepcopy(self.valid_workflow)

        for node in workflow["nodes"]:
            if node.get("id") == "phase1-build-success-response":
                node["parameters"]["options"] = {
                    "unexpected": True,
                }
                break
        else:
            self.fail("phase1-build-success-response was not found")

        errors = self.validate_copy(workflow)

        self.assertIn(
            "set node options mismatch for "
            "phase1-build-success-response: "
            "expected {}, found {'unexpected': True}",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
