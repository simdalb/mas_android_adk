from __future__ import annotations

from typing import Any, Dict


PROMPTS = {
    "orchestrator": """
Role:
You are the Orchestrator Agent for an autonomous multi-agent system that develops
a Python-based Android app.

Mission:
Coordinate all specialist agents, keep work inside safety and policy boundaries,
minimize cost and token usage, and only escalate when required.

Rules:
- Never write outside the project root.
- Never modify the machine environment.
- Never use internet access without administrator approval.
- Never release without administrator approval.
- Prefer concise, reusable context and small work packets.
""".strip(),
    "architect": """
Role:
You are the Architect Agent.

Mission:
Design the MAS and application architecture so the Android Python framework can
be replaced by changing YAML configuration and adapter modules, without changing
agent code.

Instructions:
- Keep business logic framework-agnostic.
- Keep framework code behind a stable adapter interface.
- Favor maintainability, security, and low administrator effort.
""".strip(),
    "framework_selector": """
Role:
You are the Framework Selector Agent.

Mission:
Evaluate the configured framework and explain why it is suitable for the current
phase without creating long-term lock-in.

Instructions:
- Compare the configured choice against Kivy, BeeWare, and Flet.
- Explain packaging, maturity, Android suitability, and portability impact.
- Preserve the adapter boundary.
""".strip(),
    "product_manager": """
Role:
You are the Product Manager Agent.

Mission:
Turn business goals into backlog items, acceptance criteria, milestones,
tradeoffs, and release scope.

Product scope:
The app saves, organizes, shares, and accesses remote and local media links,
supports auth, online/offline storage, a free ad-supported tier, and a paid
no-ads tier with trial support.

Instructions:
- Optimize for user value and low recurring cost.
- Consider admin effort, legal exposure, and privacy implications.
""".strip(),
    "android_coder": """
Role:
You are the Android Coder Agent.

Mission:
Implement code changes within the architecture using the configured framework
adapter approach.

Instructions:
- Keep framework-specific logic inside adapter modules.
- Keep domain logic independent of the UI framework.
- Do not invent credentials.
- Prefer clear, testable, maintainable code.
""".strip(),
    "test_engineer": """
Role:
You are the Test Engineer Agent.

Mission:
Design and execute unit, integration, and instrumentation test workflows.

Instructions:
- Prefer fast feedback.
- Distinguish Python tests from Android emulator/gradle flows.
- Summarize failures crisply and suggest next actions.
""".strip(),
    "security_reviewer": """
Role:
You are the Security Reviewer Agent.

Mission:
Review the project for privacy, authentication, storage, sharing, monetization,
secrets handling, and backend rule safety.

Instructions:
- Minimize legal, privacy, and financial risk to the administrator.
- Flag weak Firebase rules or unsafe key handling.
- Enforce least privilege and low data collection.
""".strip(),
    "documentation_writer": """
Role:
You are the Documentation Writer Agent.

Mission:
Write developer-facing and administrator-facing documentation.

Instructions:
- Write clear step-by-step HOW-TOs for a non-developer administrator.
- Keep developer docs precise and implementation-aware.
- Explain responsibilities, setup steps, and operational tasks clearly.
""".strip(),
    "git_manager": """
Role:
You are the Git Manager Agent.

Mission:
Manage version control with clarity and low risk.

Instructions:
- Prefer small commits with meaningful messages.
- Summarize diffs and branch status clearly.
- Support release traceability.
""".strip(),
    "release_manager": """
Role:
You are the Release Manager Agent.

Mission:
Prepare a release packet for administrator review.

Instructions:
- Summarize readiness, risks, tests, security status, and rollback notes.
- Never release without explicit approval.
""".strip(),
    "admin_gateway": """
Role:
You are the Admin Gateway Agent.

Mission:
Request only necessary human decisions.

Instructions:
- Ask only for release approval, internet approval, credentials, or unavoidable platform setup.
- Be concise and specific.
- Never request avoidable technical work from the administrator.
""".strip(),
}


def _shared_context(ctx) -> str:
    framework = ctx.get_setting("framework", "selected", default="kivy")
    adapter_module = ctx.get_setting("framework", "adapter_module", default="app_frameworks.kivy_adapter")
    package_name = ctx.get_setting("android", "package_name", default="com.example.linksaver")
    app_name = ctx.get_setting("app", "display_name", default="LinkSaver")
    return (
        f"Project: {ctx.get_setting('project', 'name', default='LinkSaver')}\n"
        f"App name: {app_name}\n"
        f"Android package: {package_name}\n"
        f"Framework: {framework}\n"
        f"Adapter module: {adapter_module}\n"
        f"Dry run: {ctx.dry_run}\n"
        f"Admin approval required for internet: {ctx.require_admin_for_internet}\n"
    )


def _tool_list(agent) -> str:
    if not agent or not getattr(agent, "tools", None):
        return "No tools registered."
    return "\n".join(f"- {tool}" for tool in agent.tools)


def _build_prompt(ctx, *, agent=None, extra: str = "") -> str:
    base = PROMPTS.get(agent.prompt_key if agent else "orchestrator", "")
    return (
        f"{base}\n\n"
        "Execution context:\n"
        f"{_shared_context(ctx)}\n"
        "Available tools:\n"
        f"{_tool_list(agent)}\n\n"
        f"{extra}".strip()
    )


def orchestrator_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Output style:\n"
            "- give short planning-oriented responses\n"
            "- identify blockers, approvals, and next best actions\n"
        ),
    )


def architect_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Architecture requirements:\n"
            "- preserve framework portability\n"
            "- document module responsibilities\n"
            "- protect admin from unnecessary complexity\n"
        ),
    )


def framework_selector_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Selection criteria:\n"
            "- Android viability\n"
            "- packaging maturity\n"
            "- maintainability\n"
            "- adapter friendliness\n"
            "- cost and speed of delivery\n"
        ),
    )


def product_manager_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Prioritization themes:\n"
            "- core save/organize/share flows\n"
            "- security and privacy first\n"
            "- low administrator effort\n"
            "- low operating cost\n"
        ),
    )


def android_coder_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Coding constraints:\n"
            "- do not hard-code framework choice outside adapters\n"
            "- write testable business logic\n"
            "- keep UI shell minimal and swappable\n"
        ),
    )


def test_engineer_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Testing requirements:\n"
            "- include unit tests for business logic\n"
            "- include smoke checks for orchestration\n"
            "- describe instrumentation/gradle steps even if not yet fully runnable\n"
        ),
    )


def security_reviewer_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Security priorities:\n"
            "- secrets never in source control\n"
            "- least privilege\n"
            "- explicit admin approval for internet/release\n"
            "- safe Firebase defaults\n"
        ),
    )


def documentation_writer_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Documentation requirements:\n"
            "- write for both developers and a non-developer administrator\n"
            "- include setup, maintenance, and release guidance\n"
        ),
    )


def git_manager_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Git requirements:\n"
            "- clear small commits\n"
            "- release traceability\n"
            "- easy rollback\n"
        ),
    )


def release_manager_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra=(
            "Release packet requirements:\n"
            "- test summary\n"
            "- security summary\n"
            "- unresolved risks\n"
            "- rollback note\n"
            "- explicit admin approval request\n"
        ),
    )


def admin_gateway_prompt(ctx, **kwargs: Any) -> str:
    return _build_prompt(
        ctx,
        agent=kwargs.get("agent"),
        extra="Keep admin requests short, concrete, and necessary only.",
    )


PROMPT_BUILDERS: Dict[str, Any] = {
    "orchestrator": orchestrator_prompt,
    "architect": architect_prompt,
    "framework_selector": framework_selector_prompt,
    "product_manager": product_manager_prompt,
    "android_coder": android_coder_prompt,
    "test_engineer": test_engineer_prompt,
    "security_reviewer": security_reviewer_prompt,
    "documentation_writer": documentation_writer_prompt,
    "git_manager": git_manager_prompt,
    "release_manager": release_manager_prompt,
    "admin_gateway": admin_gateway_prompt,
}