from pathlib import Path
import tempfile

from mas_android_adk import MultiAgentSystem, make_context


def test_autonomous_loop_writes_iteration_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": True, "verbose": False},
                "llm": {"mock_mode": True},
                "orchestration": {
                    "max_iterations": 1,
                    "backlog_file": "./artifacts/backlog.json",
                    "iteration_reports_dir": "./artifacts/iterations",
                    "auto_run_tests": True,
                },
            },
        )
        mas = MultiAgentSystem(ctx)
        results = mas.run_autonomous_development_loop("Autonomous local MVP")
        report = Path(tmp) / "artifacts" / "iterations" / "iteration_001.json"
        backlog = Path(tmp) / "artifacts" / "backlog.json"

        assert "iterations" in results
        assert report.exists()
        assert backlog.exists()