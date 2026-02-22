import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from backend.agents.base import _resolve_model_id


class AgentModelResolutionTests(unittest.TestCase):
    def test_resolve_default_alias_for_anthropic(self):
        self.assertEqual(_resolve_model_id("haiku"), "claude-3-5-haiku-latest")

    def test_resolve_default_alias_for_openrouter(self):
        self.assertEqual(
            _resolve_model_id("haiku", use_openrouter=True),
            "anthropic/claude-haiku-4.5",
        )

    def test_explicit_model_id_is_preserved(self):
        explicit = "anthropic/claude-haiku-4.5"
        self.assertEqual(_resolve_model_id(explicit), explicit)


if __name__ == "__main__":
    unittest.main()
