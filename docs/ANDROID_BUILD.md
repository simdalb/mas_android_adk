# Android Build Pipeline

This repository now includes a concrete Kivy-to-Android packaging path built around Buildozer.

## Included pieces
- `buildozer.spec`
- `scripts/android/build_android.py`
- `scripts/android/smoke_test_android.py`
- `android/keystore.properties.example`

## Dry-run packaging

    python mas_android_adk.py --android-package --android-mode debug

## Real debug packaging

    python mas_android_adk.py --project-root . --real-run --android-package --android-mode debug

## Smoke test

    python mas_android_adk.py --android-smoke-test

The build script writes `artifacts/android/android_build_report.json`.
The smoke test writes `artifacts/android/android_smoke_test_report.json`.
