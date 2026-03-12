"""
mas_android_adk.py

Phase-2 multi-agent system orchestration for autonomous Android app development
in Python, using Google ADK initially behind a replaceable LLM adapter layer.

This file is designed to remain stable while companion modules evolve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import importlib
import json
import traceback
import uuid


# =============================================================================
# Dynamic import helpers
# =============================================================================

def _import_optional(module_name: str) -> Optional[Any]:
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def _get_attr(module: Optional[Any], attr_name: str, default: Any) -> Any:
    if module is None:
        return default
    return getattr(module, attr_name, default)


_SETTINGS = _import_optional("mas_settings")
_PROMPTS = _import_optional("mas_prompts")
_GUARDRAILS = _import_optional("mas_guardrails")
_TOOLS = _import_optional("mas_tools")
_LLMS = _import_optional("mas_llms")
_POLICIES = _import_optional("mas_policies")
_HOOKS = _import_optional("mas_workflow_hooks")


# =============================================================================
# Defaults and fallbacks
# =============================================================================

DEFAULT_SETTINGS: Dict[str, Any] = {
    "project": {
        "name": "LinkSaver",
        "root_dir": ".",
        "artifacts_dir": "./artifacts",
        "logs_dir": "./logs",
        "docs_dir": "./docs",
    },
    "framework": {
        "selected": "kivy",
        "available": ["kivy", "beeware", "flet"],
        "adapter_module": "app_frameworks.kivy_adapter",
    },
    "llm": {
        "provider": "google_adk",
        "planner_model": "gemini-2.0-flash",
        "coder_model": "gemini-2.0-flash",
        "reviewer_model": "gemini-2.0-flash",
        "documenter_model": "gemini-2.0-flash",
        "cost_mode": "balanced",
        "mock_mode": True,
    },
    "orchestration": {
        "max_iterations": 3,
        "max_repair_attempts": 2,
        "autonomous_mode": True,
        "require_admin_for_release": True,
        "require_admin_for_internet": True,
        "stop_on_failed_guardrail": True,
    },
    "runtime": {
        "dry_run": True,
        "verbose": True,
        "fail_fast": False,
    },
}

DEFAULT_PROMPTS: Dict[str, str] = {
    "orchestrator": "You are the Orchestrator Agent.",
    "architect": "You are the Architect Agent.",
    "framework_selector": "You are the Framework Selector Agent.",
    "product_manager": "You are the Product Manager Agent.",
    "android_coder": "You are the Android Coder Agent.",
    "test_engineer": "You are the Test Engineer Agent.",
    "security_reviewer": "You are the Security Reviewer Agent.",
    "documentation_writer": "You are the Documentation Writer Agent.",
    "git_manager": "You are the Git Manager Agent.",
    "release_manager": "You are the Release Manager Agent.",
    "admin_gateway": "You are the Admin Gateway Agent.",
}

DEFAULT_POLICIES: Dict[str, Any] = {
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
}

DEFAULT_TOOL_REGISTRY: Dict[str, Any] = {}
DEFAULT_LLM_REGISTRY: Dict[str, Any] = {}
DEFAULT_HOOKS: Dict[str, Callable[..., None]] = {}


def _default_guardrail_check(action: str, ctx: "ExecutionContext", payload: Dict[str, Any]) -> Tuple[bool, str]:
    project_root = Path(ctx.project_root).resolve()

    if action in {"write_file", "delete_file", "move_file", "mkdir", "read_file"}:
        target = payload.get("path")
        if target:
            target_path = Path(target)
            if not target_path.is_absolute():
                target_path = project_root / target_path
            target_path = target_path.resolve()
            if project_root not in [target_path, *target_path.parents]:
                return False, f"Path outside project root blocked: {target_path}"

    if action == "internet_access" and ctx.require_admin_for_internet:
        return False, "Internet access requires administrator approval."

    if action == "modify_environment":
        return False, "Environment modification is blocked by policy."

    if action == "release" and ctx.settings.get("orchestration", {}).get("require_admin_for_release", True):
        return False, "Release requires administrator approval."

    return True, "Allowed by default fallback guardrail."


SETTINGS = _get_attr(_SETTINGS, "SETTINGS", DEFAULT_SETTINGS)
PROMPTS = _get_attr(_PROMPTS, "PROMPTS", DEFAULT_PROMPTS)
PROMPT_BUILDERS = _get_attr(_PROMPTS, "PROMPT_BUILDERS", {})
GUARDRAIL_CHECK = _get_attr(_GUARDRAILS, "guardrail_check", _default_guardrail_check)
TOOL_REGISTRY = _get_attr(_TOOLS, "TOOL_REGISTRY", DEFAULT_TOOL_REGISTRY)
LLM_REGISTRY = _get_attr(_LLMS, "LLM_REGISTRY", DEFAULT_LLM_REGISTRY)
POLICIES = _get_attr(_POLICIES, "POLICIES", DEFAULT_POLICIES)
WORKFLOW_HOOKS = _get_attr(_HOOKS, "WORKFLOW_HOOKS", DEFAULT_HOOKS)


# =============================================================================
# Core types
# =============================================================================

class AgentType(str, Enum):
    ORCHESTRATOR = "orchestrator"
    ANALYSIS = "analysis"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTATION = "documentation"
    GIT = "git"
    RELEASE = "release"
    ADMIN = "admin"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    NEEDS_ADMIN = "needs_admin"


@dataclass
class Artifact:
    name: str
    path: str
    kind: str
    created_by: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    sender: str
    recipient: str
    subject: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    title: str
    description: str
    owner: str
    status: TaskStatus = TaskStatus.PENDING
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    depends_on: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    project_root: str
    settings: Dict[str, Any]
    prompts: Dict[str, str]
    policies: Dict[str, Any]
    tool_registry: Dict[str, Any]
    llm_registry: Dict[str, Any]
    prompt_builders: Dict[str, Callable[..., str]] = field(default_factory=dict)
    artifacts: List[Artifact] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    tasks: Dict[str, Task] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    verbose: bool = True
    require_admin_for_internet: bool = True

    def log(self, text: str) -> None:
        if self.verbose:
            print(f"[MAS] {text}")

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts.append(artifact)
        self.log(f"Artifact registered: {artifact.name} ({artifact.kind})")

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.log(f"Message: {message.sender} -> {message.recipient}: {message.subject}")

    def add_task(self, task: Task) -> None:
        self.tasks[task.task_id] = task
        self.log(f"Task added: {task.title} [{task.task_id}]")

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            self.log(f"Task updated: {task_id} -> {status.value}")

    def get_setting(self, *path: str, default: Any = None) -> Any:
        node: Any = self.settings
        for part in path:
            if not isinstance(node, dict):
                return default
            node = node.get(part)
            if node is None:
                return default
        return node

    def build_prompt(self, key: str, **kwargs: Any) -> str:
        builder = self.prompt_builders.get(key)
        if callable(builder):
            try:
                return builder(self, **kwargs)
            except Exception as exc:
                self.log(f"Prompt builder failed for {key}: {exc}")
        return self.prompts.get(key, f"You are {key}.")


# =============================================================================
# Agent base
# =============================================================================

class AgentError(RuntimeError):
    pass


@dataclass
class Agent:
    name: str
    agent_type: AgentType
    description: str
    prompt_key: str
    tools: List[str] = field(default_factory=list)
    llm_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_prompt(self, ctx: ExecutionContext, **kwargs: Any) -> str:
        return ctx.build_prompt(self.prompt_key, agent=self, **kwargs)

    def get_llm(self, ctx: ExecutionContext):
        if not self.llm_name:
            return None
        return ctx.llm_registry.get(self.llm_name)

    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError


class LLMWorkerAgent(Agent):
    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        llm = self.get_llm(ctx)
        if llm is None:
            raise AgentError(f"No LLM configured for agent {self.name}")

        system_prompt = self.get_prompt(ctx, **kwargs)
        user_prompt = kwargs.get("user_prompt", "")

        llm_kwargs = dict(kwargs)
        llm_kwargs.pop("user_prompt", None)

        response = llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            **llm_kwargs,
        )
        return {"agent": self.name, "response": response, "model": getattr(llm, "model_name", "unknown")}


class CustomAgent(Agent):
    def __init__(self, *args: Any, handler: Optional[Callable[..., Dict[str, Any]]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = handler

    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        if self.handler is None:
            raise AgentError(f"No handler configured for custom agent {self.name}")
        return self.handler(ctx=ctx, agent=self, **kwargs)


# =============================================================================
# Workflow base
# =============================================================================

@dataclass
class WorkflowResult:
    success: bool
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)


class Workflow:
    name = "workflow"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        raise NotImplementedError


class BootstrapWorkflow(Workflow):
    name = "bootstrap"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        ctx.log("Starting bootstrap workflow")
        _run_hook("before_bootstrap", ctx)

        framework = ctx.get_setting("framework", "selected", default="kivy")
        project_name = ctx.get_setting("project", "name", default="LinkSaver")

        details = {
            "architect": agents["architect"].execute(
                ctx,
                user_prompt=(
                    f"Design the MAS and Android app architecture for project '{project_name}'. "
                    f"The selected framework is '{framework}'. Preserve framework portability."
                ),
            ),
            "framework_selector": agents["framework_selector"].execute(
                ctx,
                user_prompt=(
                    "Confirm the current framework selection and describe the adapter boundary "
                    "that allows future replacement by YAML configuration."
                ),
            ),
            "product_manager": agents["product_manager"].execute(
                ctx,
                user_prompt=(
                    "Create the initial prioritized backlog and milestone plan for a media links app "
                    "with authentication, sync, offline support, ads, and subscriptions."
                ),
            ),
            "documentation_writer": agents["documentation_writer"].execute(
                ctx,
                user_prompt=(
                    "Summarize the documentation deliverables that must exist for developers and the administrator."
                ),
            ),
        }

        ctx.shared_state["bootstrap"] = details
        _run_hook("after_bootstrap", ctx)
        return WorkflowResult(True, "Bootstrap workflow completed", details)


class DeliveryIterationWorkflow(Workflow):
    name = "delivery_iteration"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        ctx.log("Starting delivery iteration workflow")
        _run_hook("before_delivery_iteration", ctx)
        scope = kwargs.get("scope", "Implement the next prioritized backlog item.")

        details = {
            "coder": agents["android_coder"].execute(
                ctx,
                user_prompt=(
                    f"{scope}\n"
                    "Respect the framework adapter boundary and keep business logic outside framework-specific code."
                ),
            ),
            "tester": agents["test_engineer"].execute(
                ctx,
                user_prompt=(
                    "Review the current implementation and test plan. Summarize unit, integration, and instrumentation coverage."
                ),
            ),
            "security": agents["security_reviewer"].execute(
                ctx,
                user_prompt=(
                    "Review the current architecture and scaffolding for privacy, security, secrets handling, and Firebase risk."
                ),
            ),
            "git": agents["git_manager"].execute(
                ctx,
                user_prompt=(
                    "Summarize the change set, propose commits, and describe the current repo state expectations."
                ),
            ),
        }

        ctx.shared_state.setdefault("iterations", []).append(details)
        _run_hook("after_delivery_iteration", ctx)
        return WorkflowResult(True, "Delivery iteration completed", details)


class ReleaseWorkflow(Workflow):
    name = "release"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        ctx.log("Starting release workflow")
        _run_hook("before_release", ctx)

        release_packet = agents["release_manager"].execute(
            ctx,
            user_prompt=(
                "Prepare a release readiness packet with test status, risks, docs status, security status, and rollback notes."
            ),
        )

        admin_result = agents["admin_gateway"].execute(
            ctx,
            action="request_release_decision",
            payload={
                "release_packet": release_packet,
                "reason": "Final administrator approval is required before release.",
            },
        )

        details = {
            "release_manager": release_packet,
            "admin_gateway": admin_result,
        }
        ctx.shared_state["release"] = details

        _run_hook("after_release", ctx)
        return WorkflowResult(
            success=bool(admin_result.get("approved", False)),
            summary="Release workflow completed",
            details=details,
        )


# =============================================================================
# Custom handlers
# =============================================================================

def orchestrator_handler(ctx: ExecutionContext, agent: Agent, **kwargs: Any) -> Dict[str, Any]:
    objective = kwargs.get("objective", "Build and improve the Android app autonomously.")
    max_iterations = int(ctx.get_setting("orchestration", "max_iterations", default=3))

    return {
        "agent": agent.name,
        "objective": objective,
        "max_iterations": max_iterations,
        "framework": ctx.get_setting("framework", "selected", default="kivy"),
        "status": "planned",
    }


def admin_gateway_handler(ctx: ExecutionContext, agent: Agent, **kwargs: Any) -> Dict[str, Any]:
    action = kwargs.get("action", "request_decision")
    payload = kwargs.get("payload", {})

    ctx.add_message(
        Message(
            sender=agent.name,
            recipient="administrator",
            subject=action,
            content=json.dumps(payload, indent=2, default=str),
        )
    )

    approved = False
    if action == "request_internet_access":
        approved = False
    elif action == "request_release_decision":
        approved = False

    return {
        "agent": agent.name,
        "action": action,
        "approved": approved,
        "requires_human": True,
        "payload": payload,
    }


# =============================================================================
# Hooks
# =============================================================================

def _run_hook(name: str, ctx: ExecutionContext) -> None:
    hook = WORKFLOW_HOOKS.get(name)
    if callable(hook):
        try:
            hook(ctx)
        except Exception as exc:
            ctx.log(f"Hook {name} failed: {exc}")


# =============================================================================
# Agent factory
# =============================================================================

def build_agents(ctx: ExecutionContext) -> Dict[str, Agent]:
    planner_model = ctx.get_setting("llm", "planner_model", default="gemini-2.0-flash")
    coder_model = ctx.get_setting("llm", "coder_model", default="gemini-2.0-flash")
    reviewer_model = ctx.get_setting("llm", "reviewer_model", default="gemini-2.0-flash")
    documenter_model = ctx.get_setting("llm", "documenter_model", default="gemini-2.0-flash")

    return {
        "orchestrator": CustomAgent(
            name="orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
            description="Coordinates all workflows and execution.",
            prompt_key="orchestrator",
            tools=["file_read", "file_write", "git_status"],
            handler=orchestrator_handler,
        ),
        "architect": LLMWorkerAgent(
            name="architect",
            agent_type=AgentType.ANALYSIS,
            description="Designs the MAS and app architecture.",
            prompt_key="architect",
            tools=["file_read", "directory_tree", "settings_view"],
            llm_name=planner_model,
        ),
        "framework_selector": LLMWorkerAgent(
            name="framework_selector",
            agent_type=AgentType.ANALYSIS,
            description="Confirms framework choice and portability boundaries.",
            prompt_key="framework_selector",
            tools=["settings_view", "file_read"],
            llm_name=planner_model,
        ),
        "product_manager": LLMWorkerAgent(
            name="product_manager",
            agent_type=AgentType.ANALYSIS,
            description="Defines backlog, priorities, and acceptance criteria.",
            prompt_key="product_manager",
            tools=["settings_view", "file_read"],
            llm_name=planner_model,
        ),
        "android_coder": LLMWorkerAgent(
            name="android_coder",
            agent_type=AgentType.CODER,
            description="Implements app code, adapters, and integration scaffolding.",
            prompt_key="android_coder",
            tools=["file_read", "file_write", "directory_tree", "git_diff", "settings_view"],
            llm_name=coder_model,
        ),
        "test_engineer": LLMWorkerAgent(
            name="test_engineer",
            agent_type=AgentType.TESTER,
            description="Plans and runs tests, including instrumentation workflows.",
            prompt_key="test_engineer",
            tools=["pytest_runner", "gradle_tasks", "emulator_status", "file_read"],
            llm_name=reviewer_model,
        ),
        "security_reviewer": LLMWorkerAgent(
            name="security_reviewer",
            agent_type=AgentType.REVIEWER,
            description="Reviews secrets handling, access control, privacy, and backend risk.",
            prompt_key="security_reviewer",
            tools=["file_read", "settings_view", "env_template_view"],
            llm_name=reviewer_model,
        ),
        "documentation_writer": LLMWorkerAgent(
            name="documentation_writer",
            agent_type=AgentType.DOCUMENTATION,
            description="Writes developer docs, admin HOW-TOs, and operational notes.",
            prompt_key="documentation_writer",
            tools=["file_read", "directory_tree", "settings_view"],
            llm_name=documenter_model,
        ),
        "git_manager": LLMWorkerAgent(
            name="git_manager",
            agent_type=AgentType.GIT,
            description="Manages repo status, diffs, commit planning, and release traceability.",
            prompt_key="git_manager",
            tools=["git_status", "git_diff"],
            llm_name=reviewer_model,
        ),
        "release_manager": LLMWorkerAgent(
            name="release_manager",
            agent_type=AgentType.RELEASE,
            description="Prepares release evidence and decision packet.",
            prompt_key="release_manager",
            tools=["pytest_runner", "gradle_tasks", "git_status", "file_read"],
            llm_name=reviewer_model,
        ),
        "admin_gateway": CustomAgent(
            name="admin_gateway",
            agent_type=AgentType.ADMIN,
            description="Requests only essential human approvals.",
            prompt_key="admin_gateway",
            tools=["internet_request"],
            handler=admin_gateway_handler,
        ),
    }


# =============================================================================
# MAS system
# =============================================================================

class MultiAgentSystem:
    def __init__(self, ctx: ExecutionContext) -> None:
        self.ctx = ctx
        self.agents = build_agents(ctx)
        self.workflows: Dict[str, Workflow] = {
            "bootstrap": BootstrapWorkflow(),
            "delivery_iteration": DeliveryIterationWorkflow(),
            "release": ReleaseWorkflow(),
        }

    def run_workflow(self, workflow_name: str, **kwargs: Any) -> WorkflowResult:
        workflow = self.workflows.get(workflow_name)
        if workflow is None:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        return workflow.run(self.ctx, self.agents, **kwargs)

    def run_full_cycle(self, objective: str) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        results["orchestrator"] = self.agents["orchestrator"].execute(self.ctx, objective=objective)
        results["bootstrap"] = self.run_workflow("bootstrap")

        max_iterations = int(self.ctx.get_setting("orchestration", "max_iterations", default=3))
        for i in range(max_iterations):
            results.setdefault("iterations", []).append(
                self.run_workflow(
                    "delivery_iteration",
                    scope=f"Iteration {i + 1}: implement the next prioritized feature or fix.",
                )
            )

        results["release"] = self.run_workflow("release")
        return results


# =============================================================================
# Project helpers
# =============================================================================

def ensure_directories(ctx: ExecutionContext) -> None:
    project_root = Path(ctx.project_root)
    for key in ("artifacts_dir", "logs_dir", "docs_dir"):
        directory = project_root / Path(ctx.get_setting("project", key, default=f"./{key}"))
        if ctx.dry_run:
            ctx.log(f"[dry-run] ensure directory {directory}")
        else:
            directory.mkdir(parents=True, exist_ok=True)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def make_context(project_root: Optional[str] = None, settings_override: Optional[Dict[str, Any]] = None) -> ExecutionContext:
    settings = json.loads(json.dumps(SETTINGS))
    if settings_override:
        settings = _deep_merge(settings, settings_override)

    root = str(Path(project_root or settings["project"]["root_dir"]).resolve())

    return ExecutionContext(
        project_root=root,
        settings=settings,
        prompts={**DEFAULT_PROMPTS, **PROMPTS},
        policies={**DEFAULT_POLICIES, **POLICIES},
        tool_registry=TOOL_REGISTRY,
        llm_registry=LLM_REGISTRY,
        prompt_builders=PROMPT_BUILDERS,
        dry_run=bool(settings.get("runtime", {}).get("dry_run", True)),
        verbose=bool(settings.get("runtime", {}).get("verbose", True)),
        require_admin_for_internet=bool(settings.get("orchestration", {}).get("require_admin_for_internet", True)),
    )


# =============================================================================
# CLI
# =============================================================================

def print_summary(results: Dict[str, Any]) -> None:
    print("\n=== MAS SUMMARY ===")
    for key, value in results.items():
        if isinstance(value, WorkflowResult):
            print(f"- {key}: success={value.success} summary={value.summary}")
        elif isinstance(value, list):
            print(f"- {key}: {len(value)} entries")
        else:
            print(f"- {key}: {type(value).__name__}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or [])
    if not argv:
        import sys
        argv = list(sys.argv[1:])

    project_root = "."
    dry_run = True
    objective = (
        "Autonomously develop a high-quality Android app in Python for saving, "
        "organizing, sharing, and accessing remote and local media links."
    )

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--project-root" and i + 1 < len(argv):
            project_root = argv[i + 1]
            i += 2
        elif arg == "--real-run":
            dry_run = False
            i += 1
        elif arg == "--objective" and i + 1 < len(argv):
            objective = argv[i + 1]
            i += 2
        else:
            print(f"Unknown argument: {arg}")
            return 2

    ctx = make_context(project_root=project_root)
    ctx.dry_run = dry_run

    try:
        ensure_directories(ctx)
        mas = MultiAgentSystem(ctx)
        results = mas.run_full_cycle(objective=objective)
        print_summary(results)
        return 0
    except Exception as exc:
        print("MAS execution failed:")
        print(str(exc))
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())