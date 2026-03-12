POLICIES = {
    "allow_internet_without_admin": False,
    "allow_environment_modification": False,
    "allow_outside_project_writes": False,
    "allow_release_without_admin": False,
    "allowed_subprocess_commands": [
        "git",
        "python",
        "pytest",
        "gradle",
        "gradlew",
        "adb",
        "emulator",
    ],
    "blocked_paths": [
        "~",
        "/",
    ],
    "secret_env_var_prefixes": [
        "GOOGLE_",
        "FIREBASE_",
        "PLAY_",
        "ADMOB_",
        "OPENAI_",
        "GEMINI_",
    ],
}