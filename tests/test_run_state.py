from pathlib import Path
import tempfile

from mas_android_adk import MultiAgentSystem, make_context


def test_run_state_written_after_autonomous_loop():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": True, "verbose": False},
                "llm": {"mock_mode": True},
                "orchestration": {
                    "max_iterations": 1,
                    "run_state_file": "./artifacts/run_state.json",
                },
            },
        )
        mas = MultiAgentSystem(ctx)
        mas.run_autonomous_development_loop("state file test")

        state_path = Path(tmp) / "artifacts" / "run_state.json"
        assert state_path.exists()

        state = mas.load_run_state()
        assert "status" in state
        assert "objective" in state