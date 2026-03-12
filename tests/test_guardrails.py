from pathlib import Path
import tempfile

from mas_android_adk import make_context
from mas_guardrails import guardrail_check


def test_write_inside_project_allowed():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(project_root=tmp, settings_override={"runtime": {"dry_run": True}})
        ok, reason = guardrail_check("write_file", ctx, {"path": "docs/test.md"})
        assert ok, reason


def test_write_outside_project_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(project_root=tmp, settings_override={"runtime": {"dry_run": True}})
        outside = str(Path(tmp).parent / "escape.txt")
        ok, reason = guardrail_check("write_file", ctx, {"path": outside})
        assert not ok
        assert "outside project root" in reason.lower()


def test_internet_requires_admin_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(project_root=tmp, settings_override={"runtime": {"dry_run": True}})
        ok, reason = guardrail_check("internet_access", ctx, {"purpose": "package lookup"})
        assert not ok
        assert "administrator approval" in reason.lower()