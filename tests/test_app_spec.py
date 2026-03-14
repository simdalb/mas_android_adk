from pathlib import Path
import json
import tempfile

from mas_android_adk import MultiAgentSystem, compile_app_spec_to_backlog, main, make_context


def test_compile_app_spec_to_backlog_creates_spec_driven_items():
    spec = {
        "app_name": "Spec Demo",
        "features": ["favorites", {"name": "sharing", "description": "share links"}],
        "screens": [{"name": "Library", "purpose": "browse links"}],
        "data_models": [{"name": "MediaLink"}],
        "integrations": ["future cloud sync"],
    }
    backlog = compile_app_spec_to_backlog(spec)
    titles = [item.title for item in backlog]

    assert backlog[0].item_id == "spec-bootstrap-001"
    assert any("Library" in title for title in titles)
    assert any("favorites" in title.lower() for title in titles)
    assert any(item.metadata.get("executor") == "llm_patch" for item in backlog)
    assert backlog[-1].item_id == "spec-android-validation-001"


def test_main_can_compile_spec_file_into_backlog():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        spec_path = root / "spec.json"
        spec_path.write_text(json.dumps({"app_name": "CLI Demo", "features": ["favorites"]}), encoding="utf-8")

        exit_code = main(["--project-root", str(root), "--app-spec", str(spec_path), "--compile-spec"])
        assert exit_code == 0

        backlog_path = root / "artifacts" / "backlog.json"
        app_spec_path = root / "artifacts" / "app_spec.json"
        assert backlog_path.exists()
        assert app_spec_path.exists()

        payload = json.loads(backlog_path.read_text(encoding="utf-8"))
        assert any(item["item_id"] == "spec-bootstrap-001" for item in payload)


def test_autonomous_loop_runs_android_validation_when_enabled():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts" / "android").mkdir(parents=True)
        (root / "scripts" / "android" / "build_android.py").write_text("print('ok')\n", encoding="utf-8")
        (root / "scripts" / "android" / "smoke_test_android.py").write_text("print('ok')\n", encoding="utf-8")
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": True, "verbose": False},
                "llm": {"mock_mode": True},
                "orchestration": {
                    "max_iterations": 1,
                    "max_repair_attempts": 1,
                    "auto_run_tests": True,
                    "auto_build_android": True,
                    "auto_smoke_test_android": True,
                },
            },
        )
        mas = MultiAgentSystem(ctx)
        results = mas.run_autonomous_development_loop("Validate android loop")
        iteration = results["iterations"][0]
        assert iteration["android_validation"]["build"]["returncode"] == 0
        assert iteration["android_validation"]["smoke_test"]["returncode"] == 0
        assert iteration["validation_ok"] is True
