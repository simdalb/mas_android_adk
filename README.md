# Android MAS Project

This project is a framework-switchable, guarded multi-agent system (MAS) starter
for building a Python-based Android app called **LinkSaver**.

The current phase now includes:
- MAS orchestration modules
- prompt builders for each agent
- centralized guardrails
- richer tool registry
- app scaffold with domain/services/adapter split
- framework adapter stubs for Kivy, BeeWare, and Flet
- automated Python tests
- administrator and developer documentation

---

# 1. What is implemented now

## MAS layer
- agent definitions
- workflow orchestration
- prompt builders
- safety policy loading
- guardrail enforcement
- tool registry
- logging hooks

## App layer
- framework-agnostic domain models
- local storage service
- auth boundary
- monetization boundary
- framework adapter interface
- Kivy/BeeWare/Flet adapter stubs
- demo app entrypoint

## Test layer
- guardrail tests
- settings/config tests
- framework adapter tests
- MAS smoke test

---

# 2. What is still intentionally placeholder

These are scaffolded but not yet connected to live platform behavior:
- live Google ADK API calls
- real Firebase auth/storage integration
- real Android packaging/build files
- real instrumentation test execution
- real ad SDK wiring
- real billing/subscription wiring
- real release publishing

That is deliberate. The architecture is ready for those pieces without forcing
unsafe or brittle assumptions into the scaffold.

---

# 3. Project structure

- `mas_android_adk.py` — top-level orchestration entrypoint
- `mas_settings.py` — settings loader
- `mas_prompts.py` — base prompts and prompt builders
- `mas_guardrails.py` — centralized safety checks
- `mas_tools.py` — tool registry and implementations
- `mas_llms.py` — replaceable LLM adapter layer
- `mas_policies.py` — policy controls
- `mas_workflow_hooks.py` — logging hooks
- `app/` — framework-agnostic app code
- `app_frameworks/` — swappable framework adapters
- `tests/` — automated Python tests

---

# 4. How framework switching works

The selected UI/runtime framework is controlled in `settings.yaml`:

```yaml
framework:
  selected: "kivy"
  adapter_module: "app_frameworks.kivy_adapter"

To switch framework later, update only the settings:

framework:
  selected: "flet"
  adapter_module: "app_frameworks.flet_adapter"

The MAS code and app domain logic should not need editing for that switch.

5. Running the MAS

Dry-run mode is the safe default:

python mas_android_adk.py
6. Running the app scaffold
python -m app.main

This launches the currently selected adapter placeholder and prints a demo screen model.

7. Running tests
pytest -q
8. Administrator responsibilities

Your responsibilities remain:

maintain accounts and credentials

approve release decisions

approve internet access when needed

keep .env and settings.yaml accurate

keep secrets private

manage business/legal/store-owner decisions

9. Developer direction

Future implementation steps should add:

live ADK model calls

Firebase integration services

Android packaging scaffold

gradle/emulator command flows

instrumentation test harness

release packet generation from real artifacts


---