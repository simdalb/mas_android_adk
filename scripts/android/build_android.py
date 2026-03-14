from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

from mas_settings import load_settings
from app.services.integration_config import load_integration_status


def run(command: list[str], cwd: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"command": command, "returncode": 0, "stdout": f"[dry-run] {' '.join(command)}", "stderr": ""}
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build LinkSaver for Android")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--mode", choices=["debug", "release"], default="debug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    settings = load_settings(str(root / 'settings.yaml')) if (root / 'settings.yaml').exists() else load_settings()
    integration = load_integration_status(str(root / 'settings.yaml')) if (root / 'settings.yaml').exists() else load_integration_status()
    report_dir = root / "artifacts" / "android"
    report_dir.mkdir(parents=True, exist_ok=True)
    spec = root / "buildozer.spec"
    if not spec.exists():
        raise SystemExit("buildozer.spec is missing. Run the packaging generator first.")

    commands: list[dict] = []
    errors: list[str] = []
    buildozer_exe = shutil.which("buildozer") or "buildozer"

    if (root / 'scripts' / 'android' / 'preflight_check.py').exists():
        preflight = run([shutil.which('python') or 'python', str(root / 'scripts' / 'android' / 'preflight_check.py'), '--project-root', str(root)], cwd=root, dry_run=args.dry_run)
        commands.append(preflight)
        if preflight['returncode'] != 0 and not args.dry_run:
            errors.append('Android preflight failed')

    commands.append(run([buildozer_exe, "android", args.mode], cwd=root, dry_run=args.dry_run))
    if commands[-1]["returncode"] != 0:
        errors.append(commands[-1]["stderr"] or commands[-1]["stdout"])

    artifact_candidates = sorted((root / "bin").glob("*.apk")) + sorted((root / "bin").glob("*.aab"))
    report = {
        "ok": len(errors) == 0,
        "mode": args.mode,
        "dry_run": bool(args.dry_run),
        "android": settings.get('android', {}),
        "integrations": integration.summary(),
        "commands": commands,
        "artifacts": [str(path) for path in artifact_candidates],
        "errors": errors,
        "env_hints": {
            "ANDROIDSDK": os.environ.get("ANDROIDSDK", ""),
            "ANDROID_HOME": os.environ.get("ANDROID_HOME", ""),
            "JAVA_HOME": os.environ.get("JAVA_HOME", ""),
        },
    }
    (report_dir / "android_build_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
