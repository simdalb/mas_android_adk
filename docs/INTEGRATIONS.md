# Live integrations wiring

This repo is now prepared so you can add your live Android/Firebase/Billing/AdMob values later without changing the Python scaffolding.

## Where to place files

- Firebase Android config: `android/google-services.json`
- Release signing properties: `android/keystore.properties`
- Example template already included: `android/keystore.properties.example`
- Runtime secrets and IDs: `.env`

## Which environment variables are supported

### Firebase
- `FIREBASE_PROJECT_ID`
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_ANDROID_APP_ID`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_USE_AUTH`
- `FIREBASE_USE_FIRESTORE`
- `FIREBASE_USE_STORAGE`
- `FIREBASE_USE_FUNCTIONS`
- `FIREBASE_USE_ANALYTICS`
- `FIREBASE_USE_CRASHLYTICS`

### Billing
- `BILLING_PREMIUM_SUBSCRIPTION_ID`
- `BILLING_REMOVE_ADS_PRODUCT_ID`

### AdMob
- `ADMOB_APP_ID`
- `ADMOB_BANNER_AD_UNIT_ID`
- `ADMOB_INTERSTITIAL_AD_UNIT_ID`
- `ADMOB_REWARDED_AD_UNIT_ID`
- `ADMOB_APP_OPEN_AD_UNIT_ID`

### App / Android identity
- `APP_DISPLAY_NAME`
- `ANDROID_APP_NAME`
- `GOOGLE_PLAY_PACKAGE_NAME`

## Preflight check

Run this before a real build:

```bash
python scripts/android/preflight_check.py --project-root .
```

It writes `artifacts/android/android_preflight_report.json` and tells you:
- which tools are available
- which drop-in files are still missing
- which environment keys are still missing

## Notes

The repo exposes integration readiness in `app.services.integration_config` and prints it in `python -m app.main`.
That means you can verify whether the project is fully configured before starting a real autonomous run.
