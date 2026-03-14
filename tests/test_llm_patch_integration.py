from pathlib import Path
import tempfile

from mas_android_adk import MultiAgentSystem, make_context


class FakeCoder:
    def execute(self, ctx, **kwargs):
        return {
            "response": """
{
  "summary": "Add troubleshooting section",
  "edits": [
    {
      "path": "docs/AUTONOMOUS_MODE.md",
      "operations": [
        {
          "mode": "append",
          "text": "\\n## Troubleshooting\\nIf an autonomous run fails, inspect the latest iteration report and run state file.\\n"
        }
      ]
    }
  ]
}
""".strip()
        }


def test_mas_passes_agents_into_llm_patch_executor():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs = root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "AUTONOMOUS_MODE.md").write_text("# Autonomous Mode Runbook\n", encoding="utf-8")

        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": False, "verbose": False},
                "llm": {"mock_mode": True},
                "orchestration": {
                    "max_iterations": 1,
                    "auto_run_tests": False,
                },
            },
        )

        mas = MultiAgentSystem(ctx)
        mas.agents["android_coder"] = FakeCoder()

        backlog = [
            {
                "item_id": "llm-patch-docs-001",
                "title": "Improve autonomous mode documentation with troubleshooting note",
                "description": "Use llm_patch to add a troubleshooting note",
                "acceptance_criteria": ["doc updated"],
                "status": "pending",
                "attempts": 0,
                "notes": [],
                "metadata": {
                    "executor": "llm_patch",
                    "patch_target_hint": ["docs/AUTONOMOUS_MODE.md"],
                },
            }
        ]
        ctx.write_json("./artifacts/backlog.json", backlog)

        results = mas.run_autonomous_development_loop("integration test")
        assert results["iterations"]
        text = (docs / "AUTONOMOUS_MODE.md").read_text(encoding="utf-8")
        assert "Troubleshooting" in text