import json
import unittest

from repo_agent.lambda_function import (
    AgentError,
    _parse_event,
    _response_output_text,
    _validate_edit_path,
    _validate_plan,
)


class RepoAgentTests(unittest.TestCase):
    def test_parse_direct_event(self):
        self.assertEqual(
            _parse_event({"task": "Fix CI", "dry_run": True}),
            {"task": "Fix CI", "dry_run": True},
        )

    def test_parse_function_url_body(self):
        event = {"body": json.dumps({"task": "Review Terraform"})}
        self.assertEqual(
            _parse_event(event),
            {"task": "Review Terraform", "dry_run": False},
        )

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(AgentError):
            _validate_edit_path("../../secret.txt")

    def test_sensitive_path_is_rejected(self):
        with self.assertRaises(AgentError):
            _validate_edit_path("prod-secrets.json")

    def test_duplicate_edits_are_rejected(self):
        plan = {
            "edits": [
                {"path": "README.md", "content": "a", "reason": "one"},
                {"path": "README.md", "content": "b", "reason": "two"},
            ]
        }
        with self.assertRaises(AgentError):
            _validate_plan(plan)

    def test_extract_response_output_text(self):
        response = {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "{\"ok\":true}"}],
            }]
        }
        self.assertEqual(_response_output_text(response), '{"ok":true}')


if __name__ == "__main__":
    unittest.main()
