from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

from mas_settings import load_settings
from app.services.integration_config import load_integration_status


def run(command: list[str], cwd: Path) -> dict:
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, check=False)
    return {"command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Android build preflight checks")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    settings = load_settings(str(root / 'settings.yaml')) if (root / 'settings.yaml').exists() else load_settings()
    integration = load_integration_status(str(root / 'settings.yaml')) if (root / 'settings.yaml').exists() else load_integration_status()

    required_tools = ['python', 'buildozer', 'adb']
    tool_status = {tool: bool(shutil.which(tool)) for tool in required_tools}
    commands = []
    adb_path = shutil.which('adb')
    if adb_path:
        commands.append(run([adb_path, 'devices'], cwd=root))

    google_services = root / settings.get('android', {}).get('google_services_json', './android/google-services.json')
    keystore_properties = root / settings.get('android', {}).get('release_keystore_properties', './android/keystore.properties')

    report = {
        'ok': all(tool_status.values()),
        'required_tools': tool_status,
        'env_hints': {
            'ANDROIDSDK': os.environ.get('ANDROIDSDK', ''),
            'ANDROID_HOME': os.environ.get('ANDROID_HOME', ''),
            'JAVA_HOME': os.environ.get('JAVA_HOME', ''),
        },
        'files': {
            'buildozer_spec': str(root / 'buildozer.spec'),
            'google_services_json_expected_at': str(google_services),
            'google_services_json_present': google_services.exists(),
            'keystore_properties_expected_at': str(keystore_properties),
            'keystore_properties_present': keystore_properties.exists(),
        },
        'android': settings.get('android', {}),
        'integrations': integration.summary(),
        'commands': commands,
    }
    out_dir = root / 'artifacts' / 'android'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'android_preflight_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
