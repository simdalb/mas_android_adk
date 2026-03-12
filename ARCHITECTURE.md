# ARCHITECTURE

## 1. Goal

This project is a starter architecture for a multi-agent system (MAS) that can
autonomously build and evolve an Android app in Python, while keeping the
administrator's work as small as possible and preserving strong safety controls.

The target app is a media-link manager for saving, organizing, sharing, and
accessing remote and local media links, with:
- authentication
- online and offline storage
- free ad-supported tier
- paid no-ads tier with trial
- strong privacy and security practices

---

## 2. Initial framework choice

### Selected initially: Kivy

Kivy is chosen for the initial scaffold because:
- it has a relatively mature Python-first approach
- it is well known for packaging Python apps for Android
- it is suitable for quick iteration from Python
- it allows the MAS to start from a practical baseline

### Why not lock in?

The project must not be tightly coupled to Kivy, BeeWare, or any single
framework. For that reason, the MAS is designed around a framework adapter
boundary:
- the selected framework is declared in `settings.yaml`
- framework-specific code is expected to live in adapter modules
- agent code reads configuration and does not hard-code framework assumptions

This means the framework can be swapped later with minimal changes, ideally only
through configuration and adapter replacement.

---

## 3. MAS design principles

1. **Autonomy by default**
   Agents should proceed without human intervention except where policy requires
   approval.

2. **Administrator protection**
   The MAS must minimize:
   - financial risk
   - security risk
   - privacy risk
   - operational burden

3. **Framework portability**
   The MAS should not assume one permanent UI/runtime framework.

4. **Cost-aware LLM usage**
   Use smaller models for planning, coding, reviewing, and documentation where
   possible. Escalate only when needed.

5. **Strict guardrails**
   Agents must not:
   - write outside project root
   - change the system environment
   - use internet without approval
   - release without administrator approval

6. **Developer accessibility**
   The resulting project must be understandable and maintainable by human
   developers.

---

## 4. Agent roles

## Orchestrator
Coordinates the system, schedules workflows, and keeps progress aligned with the goal.

## Architect
Designs the MAS structure and app architecture.

## Framework Selector
Evaluates Python Android frameworks and recommends the current choice.

## Product Manager
Owns backlog, scope, milestones, priorities, and acceptance criteria.

## Android Coder
Implements code changes inside architectural boundaries.

## Test Engineer
Designs and runs unit, integration, and instrumentation tests.

## Security Reviewer
Reviews code and plans for security, privacy, auth, storage, sharing, and backend rules.

## Documentation Writer
Produces developer docs, admin HOW-TOs, architecture rationale, and onboarding docs.

## Git Manager
Manages commit strategy, change summaries, and version-control hygiene.

## Release Manager
Prepares release evidence and admin decision packet.

## Admin Gateway
Collects only necessary human decisions:
- internet approval
- credentials
- release approval
- platform-account tasks

---

## 5. Workflow design

### Bootstrap workflow
Purpose:
- create initial architecture
- evaluate framework
- create backlog
- prepare documentation plan

### Delivery iteration workflow
Purpose:
- implement next scoped item
- test it
- review for security
- prepare git summary

### Release workflow
Purpose:
- prepare release packet
- request administrator decision
- block release until approved

---

## 6. LLM strategy

The initial starter project uses a Google ADK-oriented adapter layer.

### Why Google ADK initially?
- it gives a clean starting point for agent-based orchestration in Python
- it aligns with the user's request for initial implementation direction
- it can later be replaced behind a stable interface

### Model strategy
Use cheaper/faster models for most work:
- planner: balanced, fast model
- coder: balanced, fast model
- reviewer: balanced, fast model
- documenter: balanced, fast model

A stronger model can be introduced later for:
- high-risk refactors
- security review escalation
- release-critical analysis

This supports the goal of minimizing token cost while keeping quality high.

---

## 7. Tools

The architecture expects the following tool categories:
- safe subprocess execution
- file read/write
- git execution
- gradle execution
- emulator/adb execution
- internet access request tool

The current starter project includes placeholders for these.

---

## 8. Guardrails

Guardrails are mandatory and centralized:
- path-based file restrictions
- subprocess working-directory restrictions
- no environment modification
- internet requires admin approval
- release requires admin approval

These are implemented in `mas_guardrails.py` and enforced by tool calls.

---

## 9. Android app architectural direction

The future app should likely be organized into:
- `core/` for business logic
- `domain/` for entities and use cases
- `adapters/` for framework-specific code
- `services/` for auth, storage, monetization, sync, and sharing
- `tests/` for automated verification
- `docs/` for admin and developer documentation

This separation supports framework portability and maintainability.

---

## 10. Security direction

The app and MAS must be designed with:
- least-privilege access
- minimal data collection
- secure secret handling
- strict Firebase rules
- safe local storage
- auditable release decisions
- clear admin responsibilities

The administrator should not be expected to understand deep software engineering.
Documentation must be explicit and step-by-step.

---

## 11. Future work

Next implementation phases should add:
- real ADK integration
- actual prompt payload builders
- richer tools
- approval queue / admin response mechanism
- Android project scaffolding
- framework adapter implementations
- Firebase integration setup files
- monetization integration scaffolds
- instrumentation test runners