import tempfile

from mas_android_adk import MultiAgentSystem, make_context


def test_mas_runs_smoke_cycle():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": True, "verbose": False},
                "orchestration": {"max_iterations": 1},
            },
        )
        mas = MultiAgentSystem(ctx)
        results = mas.run_full_cycle("Smoke test objective")
        assert "bootstrap" in results
        assert "release" in results