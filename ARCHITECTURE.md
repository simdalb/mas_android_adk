
# ARCHITECTURE

## 1. Goal

This project is a multi-agent system (MAS) scaffold for autonomously developing a
Python-based Android app that saves, organizes, shares, and accesses remote and
local media links.

The system must:
- minimize administrator effort
- preserve framework portability
- be safe by default
- remain understandable by human developers
- support future Android build/test automation

---

## 2. Initial framework choice

### Selected initially: Kivy

Kivy is selected for the initial scaffold because it is Python-first, practical
for quick prototyping, and commonly used in Python-to-Android workflows.

### Why the project is not locked to Kivy

The system isolates framework-specific code behind the `FrameworkAdapter`
interface and the `app_frameworks/` modules.

The framework is selected only by configuration:

```yaml
framework:
  selected: "kivy"
  adapter_module: "app_frameworks.kivy_adapter"

That means a future switch to BeeWare or Flet should require only:

updating YAML settings

improving or replacing the corresponding adapter module

Agent code should not change.

3. MAS architecture
Orchestrator

Coordinates the overall system and decides the sequence of workflows.

Architect

Designs the MAS and app structure.

Framework Selector

Explains and validates framework choice while enforcing portability.

Product Manager

Owns priorities, backlog, acceptance criteria, and milestones.

Android Coder

Implements app and scaffold code while respecting adapter boundaries.

Test Engineer

Owns unit/integration/instrumentation test planning and summaries.

Security Reviewer

Reviews data handling, secrets, auth, storage, sharing, and backend risk.

Documentation Writer

Produces both developer docs and admin HOW-TOs.

Git Manager

Owns repo hygiene, diff summaries, and release traceability.

Release Manager

Prepares the release packet.

Admin Gateway

Collects only required human approvals.

4. Workflow design
Bootstrap workflow

Produces:

architecture reasoning

framework reasoning

initial backlog

documentation plan

Delivery iteration workflow

Produces:

implementation summary

testing summary

security review summary

git summary

Release workflow

Produces:

release packet

explicit admin approval request

5. Prompt design

Each LLM agent has:

a base role prompt

a prompt builder that injects runtime context

a tool list

explicit constraints

This reduces repetition while keeping prompts specific.

6. Tooling design

The current tool registry includes:

safe subprocess runner

file read/write

JSON write

settings viewer

env template viewer

directory tree

git status/diff

gradle task runner

emulator status

pytest runner

internet approval checker

All tools must pass through centralized guardrails where relevant.

7. Guardrails

Guardrails are centralized in mas_guardrails.py.

They currently enforce:

no writes outside the project root

no reads outside the project root

no subprocess working directory outside the project root

no internet without admin approval

no environment modification

no release without admin approval

These guardrails are mandatory and tool-facing.

8. App architecture

The app is separated into:

app/domain/ for business entities

app/services/ for use-case supporting services

app/adapters/ for stable adapter contracts

app_frameworks/ for concrete UI/runtime implementations

This supports maintainability and framework portability.

9. LLM strategy

The project uses a replaceable LLM adapter layer in mas_llms.py.

Initial target:

Google ADK / Gemini

Current safe behavior:

mock mode by default

Reasoning:

keeps the system runnable

avoids accidental paid calls

preserves the integration seam for later live usage

Smaller/faster models are preferred for:

planning

implementation guidance

reviews

docs

A stronger model can be added later for security or release-critical tasks.

10. Testing

The current automated tests cover:

guardrails

settings/config loading

framework adapter loading

MAS smoke execution

Future testing should add:

Firebase service tests

adapter-specific UI tests

Android packaging tests

instrumentation tests on emulator/device

11. Security direction

The project is designed to protect the administrator by:

minimizing required human steps

isolating secrets outside source control

using explicit approvals for risky actions

keeping backend, auth, and monetization behind defined service boundaries

supporting future least-privilege Firebase rules

12. Next implementation phase

The next phase should add:

live Google ADK calls

Firebase-backed auth and sync services

Android packaging/build scaffolding

gradle/emulator orchestration flows

instrumentation test execution

production documentation for release operations


---