from pathlib import Path
import json
import tempfile

from mas_android_adk import BacklogItem, make_context
from mas_autonomy import execute_work_item


def test_executor_creates_use_case_files():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": False, "verbose": False},
                "llm": {"mock_mode": True},
            },
        )

        item = BacklogItem(
            item_id="use-cases-001",
            title="Add media link use-case layer",
            description="Create use-case layer",
            acceptance_criteria=["exists"],
            attempts=1,
            metadata={"executor": "create_media_link_use_cases"},
        )

        result = execute_work_item(ctx, item)
        assert result["success"] is True
        assert (Path(tmp) / "app" / "use_cases" / "media_links.py").exists()


def test_executor_respects_missing_executor():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": False, "verbose": False},
                "llm": {"mock_mode": True},
            },
        )

        item = BacklogItem(
            item_id="bad-001",
            title="Bad edit",
            description="Should fail",
            acceptance_criteria=[],
            attempts=1,
            metadata={"executor": "nonexistent"},
        )

        result = execute_work_item(ctx, item)
        assert result["success"] is False


def test_llm_patch_plan_executes_with_fake_coder():
    class FakeCoder:
        def execute(self, ctx, **kwargs):
            plan = {
                "summary": "Append a line to the note",
                "edits": [
                    {
                        "path": "docs/note.md",
                        "operations": [
                            {"mode": "append", "text": "\nsecond line\n"}
                        ],
                    }
                ],
            }
            return {"response": json.dumps(plan)}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs = root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "note.md").write_text("first line\n", encoding="utf-8")

        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": False, "verbose": False},
                "llm": {"mock_mode": True},
            },
        )

        item = BacklogItem(
            item_id="llm-patch-001",
            title="Update docs note",
            description="Append one line to the note",
            acceptance_criteria=["note updated"],
            attempts=1,
            metadata={
                "executor": "llm_patch",
                "patch_target_hint": ["docs/note.md"],
            },
        )

        result = execute_work_item(ctx, item, agents={"android_coder": FakeCoder()})
        assert result["success"] is True
        text = (docs / "note.md").read_text(encoding="utf-8")
        assert "second line" in text
        assert "plan_artifact" in result