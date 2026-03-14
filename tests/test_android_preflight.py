import tempfile
from pathlib import Path

from mas_android_adk import make_context


def test_android_preflight_tool_runs_in_dry_run_mode():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts" / "android").mkdir(parents=True)
        (root / "scripts" / "android" / "preflight_check.py").write_text("print('ok')\n", encoding="utf-8")
        ctx = make_context(project_root=tmp, settings_override={"runtime": {"dry_run": True, "verbose": False}})
        result = ctx.tool_registry["android_preflight"].run(ctx)
        assert result["returncode"] == 0
        assert "[dry-run]" in result["stdout"]
