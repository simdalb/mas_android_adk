from __future__ import annotations

from pathlib import Path
import argparse
import json
import shutil
import subprocess

from mas_settings import load_settings


def run(command: list[str], cwd: Path, dry_run: bool) -> dict:
    if dry_run:
        return {"command": command, "returncode": 0, "stdout": f"[dry-run] {' '.join(command)}", "stderr": ""}
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke test Android package via adb")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--package-name", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    settings = load_settings(str(root / 'settings.yaml')) if (root / 'settings.yaml').exists() else load_settings()
    package_name = args.package_name or settings.get('android', {}).get('package_name', 'com.example.linksaver')
    report_dir = root / "artifacts" / "android"
    report_dir.mkdir(parents=True, exist_ok=True)
    adb_exe = shutil.which("adb") or "adb"

    apk_candidates = sorted((root / "bin").glob("*.apk"))
    chosen_apk = str(apk_candidates[-1]) if apk_candidates else ""

    commands = [
        run([adb_exe, "devices"], cwd=root, dry_run=args.dry_run),
    ]
    if chosen_apk:
        commands.append(run([adb_exe, "install", "-r", chosen_apk], cwd=root, dry_run=args.dry_run))
        commands.append(run([adb_exe, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"], cwd=root, dry_run=args.dry_run))
        commands.append(run([adb_exe, "shell", "pidof", package_name], cwd=root, dry_run=args.dry_run))

    errors = [entry["stderr"] or entry["stdout"] for entry in commands if entry["returncode"] != 0]
    report = {
        "ok": len(errors) == 0,
        "dry_run": bool(args.dry_run),
        "package_name": package_name,
        "apk": chosen_apk,
        "commands": commands,
        "errors": errors,
    }
    (report_dir / "android_smoke_test_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
