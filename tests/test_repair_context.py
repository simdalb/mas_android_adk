from pathlib import Path
import tempfile

from mas_android_adk import MultiAgentSystem, make_context


def test_failed_iteration_stores_failure_summary():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs = root / "docs"
        tests_dir = root / "tests"
        docs.mkdir(parents=True, exist_ok=True)
        tests_dir.mkdir(parents=True, exist_ok=True)
        (docs / "AUTONOMOUS_MODE.md").write_text("# Autonomous Mode Runbook\n", encoding="utf-8")
        (tests_dir / "test_failure.py").write_text(
            "def test_forced_failure():\n    assert False, 'forced failure for repair summary'\n",
            encoding="utf-8",
        )

        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": False, "verbose": False},
                "llm": {"mock_mode": True},
                "orchestration": {"max_iterations": 1, "auto_run_tests": True},
            },
        )

        mas = MultiAgentSystem(ctx)
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

        mas.run_autonomous_development_loop("repair context test")
        backlog_after = ctx.read_json("./artifacts/backlog.json", default=[])

        assert backlog_after
        first = backlog_after[0]
        assert "last_failure_summary" in first["metadata"]
        assert first["metadata"]["last_failure_summary"]
