from pathlib import Path
import tempfile

from mas_android_adk import make_context


def test_android_build_tool_runs_in_dry_run_mode():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts" / "android").mkdir(parents=True)
        (root / "scripts" / "android" / "build_android.py").write_text(
            "print('ok')\n", encoding="utf-8"
        )
        ctx = make_context(project_root=tmp, settings_override={"runtime": {"dry_run": True, "verbose": False}})
        result = ctx.tool_registry["android_build"].run(ctx, mode="debug")
        assert result["returncode"] == 0
        assert "build_android.py" in result["stdout"]
