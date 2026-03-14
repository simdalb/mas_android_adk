"""
mas_android_adk.py

Phase-7 multi-agent system orchestration for autonomous Android app development
in Python.

This phase adds:
- failure-aware repair context in the autonomous loop
- a second controlled llm_patch backlog item for app validation UX
- persistent failure summaries for retries
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import importlib
import json
import time
import traceback
import uuid


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
_AUTONOMY = _import_optional("mas_autonomy")


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
        "provider_mode": "mixed",
        "planner_model": "openai:gpt-5.4",
        "coder_model": "openai:gpt-5.4",
        "reviewer_model": "google:gemini-3-flash-preview",
        "documenter_model": "google:gemini-3-flash-preview",
        "fallback_fast_model": "google:gemini-2.5-flash",
        "fallback_strong_model": "openai:gpt-5.4",
        "cost_mode": "balanced",
        "mock_mode": False,
    },
    "orchestration": {
        "max_iterations": 6,
        "max_repair_attempts": 3,
        "autonomous_mode": True,
        "require_admin_for_release": True,
        "require_admin_for_internet": True,
        "stop_on_failed_guardrail": True,
        "write_iteration_artifacts": True,
        "backlog_file": "./artifacts/backlog.json",
        "iteration_reports_dir": "./artifacts/iterations",
        "plan_artifacts_dir": "./artifacts/plans",
        "run_state_file": "./artifacts/run_state.json",
        "auto_run_tests": True,
        "auto_build_android": False,
        "auto_smoke_test_android": False,
        "app_spec_file": "./artifacts/app_spec.json",
    },
    "android": {
        "package_name": "com.example.linksaver",
        "smoke_test_package_name": "com.example.linksaver",
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
        "buildozer",
        "python3",
        "python.exe",
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

AUTONOMY_EXECUTE_WORK_ITEM = _get_attr(_AUTONOMY, "execute_work_item", None)
AUTONOMY_RESTORE_SNAPSHOT = _get_attr(_AUTONOMY, "restore_snapshot", None)
AUTONOMY_PENDING_ADMIN_REQUESTS = _get_attr(_AUTONOMY, "pending_admin_requests", None)
AUTONOMY_REQUEST_ADMIN_APPROVAL = _get_attr(_AUTONOMY, "request_admin_approval", None)
AUTONOMY_RECORD_ADMIN_RESPONSE = _get_attr(_AUTONOMY, "record_admin_response", None)


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
class BacklogItem:
    item_id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    status: str = "pending"
    attempts: int = 0
    notes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacklogItem":
        return cls(
            item_id=str(data["item_id"]),
            title=str(data["title"]),
            description=str(data["description"]),
            acceptance_criteria=list(data.get("acceptance_criteria", [])),
            status=str(data.get("status", "pending")),
            attempts=int(data.get("attempts", 0)),
            notes=list(data.get("notes", [])),
            metadata=dict(data.get("metadata", {})),
        )


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

    def resolve_path(self, path_value: str) -> Path:
        path = Path(path_value)
        if not path.is_absolute():
            path = Path(self.project_root) / path
        return path.resolve()

    def write_json(self, relative_path: str, data: Any) -> Path:
        target = self.resolve_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def read_json(self, relative_path: str, default: Any) -> Any:
        target = self.resolve_path(relative_path)
        if not target.exists():
            return default
        return json.loads(target.read_text(encoding="utf-8"))

    def write_text(self, relative_path: str, text: str) -> Path:
        target = self.resolve_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target


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
        return {
            "agent": self.name,
            "response": response,
            "model": getattr(llm, "model_name", "unknown"),
        }


class CustomAgent(Agent):
    def __init__(self, *args: Any, handler: Optional[Callable[..., Dict[str, Any]]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = handler

    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        if self.handler is None:
            raise AgentError(f"No handler configured for custom agent {self.name}")
        return self.handler(ctx=ctx, agent=self, **kwargs)


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
                    "Confirm the framework selection and explain how the adapter boundary keeps the app swappable."
                ),
            ),
            "product_manager": agents["product_manager"].execute(
                ctx,
                user_prompt=(
                    "Create a local-first backlog for LinkSaver, starting with Kivy CRUD, search, and persistence."
                ),
            ),
            "documentation_writer": agents["documentation_writer"].execute(
                ctx,
                user_prompt=(
                    "Summarize the docs needed for a developer and the administrator at this phase."
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
        backlog_item = kwargs.get("backlog_item")

        details = {
            "coder": agents["android_coder"].execute(
                ctx,
                user_prompt=(
                    f"Scope:\n{scope}\n\n"
                    "Summarize implementation intent, files involved, and key constraints."
                ),
            ),
            "tester": agents["test_engineer"].execute(
                ctx,
                user_prompt=(
                    "Review current test coverage and summarize how to validate this iteration."
                ),
            ),
            "security": agents["security_reviewer"].execute(
                ctx,
                user_prompt=(
                    "Review privacy, local storage, key handling, and unintended data exposure risks for this iteration."
                ),
            ),
            "git": agents["git_manager"].execute(
                ctx,
                user_prompt=(
                    "Summarize expected git changes and recommended commit grouping for this iteration."
                ),
            ),
            "backlog_item": asdict(backlog_item) if isinstance(backlog_item, BacklogItem) else None,
        }

        if ctx.get_setting("orchestration", "auto_run_tests", default=True):
            pytest_runner = ctx.tool_registry.get("pytest_runner")
            if pytest_runner is not None:
                details["pytest"] = pytest_runner.run(ctx, args=["-q"])

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
                "Prepare a release readiness packet with test status, security status, open risks, and rollback notes."
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

    if callable(AUTONOMY_REQUEST_ADMIN_APPROVAL):
        return AUTONOMY_REQUEST_ADMIN_APPROVAL(ctx, request_type=action, payload=payload)

    return {
        "agent": agent.name,
        "action": action,
        "approved": False,
        "requires_human": True,
        "payload": payload,
    }


def _run_hook(name: str, ctx: ExecutionContext) -> None:
    hook = WORKFLOW_HOOKS.get(name)
    if callable(hook):
        try:
            hook(ctx)
        except Exception as exc:
            ctx.log(f"Hook {name} failed: {exc}")


def build_agents(ctx: ExecutionContext) -> Dict[str, Agent]:
    planner_model = ctx.get_setting("llm", "planner_model", default="openai:gpt-5.4")
    coder_model = ctx.get_setting("llm", "coder_model", default="openai:gpt-5.4")
    reviewer_model = ctx.get_setting("llm", "reviewer_model", default="google:gemini-3-flash-preview")
    documenter_model = ctx.get_setting("llm", "documenter_model", default="google:gemini-3-flash-preview")

    return {
        "orchestrator": CustomAgent(
            name="orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
            description="Coordinates all workflows and execution.",
            prompt_key="orchestrator",
            tools=["file_read", "file_write", "git_status", "backlog_view"],
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
            tools=["settings_view", "file_read", "backlog_view"],
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
            tools=["pytest_runner", "gradle_tasks", "git_status", "file_read", "backlog_view"],
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

    def backlog_file_path(self) -> str:
        return self.ctx.get_setting("orchestration", "backlog_file", default="./artifacts/backlog.json")

    def iteration_reports_dir(self) -> str:
        return self.ctx.get_setting("orchestration", "iteration_reports_dir", default="./artifacts/iterations")

    def run_state_file_path(self) -> str:
        return self.ctx.get_setting("orchestration", "run_state_file", default="./artifacts/run_state.json")

    def default_backlog(self) -> List[BacklogItem]:
        return [
            BacklogItem(
                item_id="use-cases-001",
                title="Add media link use-case layer",
                description="Create a framework-agnostic use-case layer for CRUD and search over media links.",
                acceptance_criteria=[
                    "Use-case module exists",
                    "It wraps repository CRUD operations",
                    "It is independent of the UI framework",
                ],
                metadata={"executor": "create_media_link_use_cases"},
            ),
            BacklogItem(
                item_id="use-cases-tests-001",
                title="Add use-case tests",
                description="Create tests for the media link use-case layer.",
                acceptance_criteria=[
                    "Use-case tests exist",
                    "Tests pass under pytest",
                ],
                metadata={"executor": "create_media_link_use_case_tests"},
            ),
            BacklogItem(
                item_id="kivy-use-cases-001",
                title="Switch Kivy adapter to use use-case layer",
                description="Move Kivy CRUD UI off direct repository calls and onto the framework-agnostic use-case layer.",
                acceptance_criteria=[
                    "Kivy adapter imports use-case layer",
                    "Kivy CRUD operations go through use cases",
                    "Tests still pass",
                ],
                metadata={"executor": "switch_kivy_to_use_cases"},
            ),
            BacklogItem(
                item_id="autonomy-docs-001",
                title="Write autonomous mode runbook",
                description="Create documentation explaining autonomous runs, approvals, pause/resume, and artifacts.",
                acceptance_criteria=[
                    "Runbook exists",
                    "Approval queue is explained",
                    "Resume process is explained",
                ],
                metadata={"executor": "create_autonomy_runbook"},
            ),
            BacklogItem(
                item_id="autonomy-status-docs-001",
                title="Document status inspection",
                description="Add run-state status inspection to autonomous mode docs.",
                acceptance_criteria=[
                    "Status command documented",
                ],
                metadata={"executor": "document_status_command"},
            ),
            BacklogItem(
                item_id="llm-patch-docs-001",
                title="Improve autonomous mode documentation with troubleshooting note",
                description="Use the guarded llm_patch path to add a short troubleshooting note to autonomous mode documentation.",
                acceptance_criteria=[
                    "The autonomous mode doc includes a troubleshooting section",
                    "The change is applied through llm_patch",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": ["docs/AUTONOMOUS_MODE.md"],
                },
            ),
            BacklogItem(
                item_id="llm-patch-ui-001",
                title="Improve UI validation guidance",
                description="Use the guarded llm_patch path to improve Kivy UI validation messages and add a duplicate warning hint.",
                acceptance_criteria=[
                    "Validation failures are clearer to the user",
                    "The Kivy UI contains a duplicate guidance message",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": [
                        "app/use_cases/media_links.py",
                        "app_frameworks/kivy_adapter.py",
                    ],
                },
            ),
        ]

    def load_backlog(self) -> List[BacklogItem]:
        raw = self.ctx.read_json(self.backlog_file_path(), default=None)
        if not raw:
            backlog = self.default_backlog()
            self.save_backlog(backlog)
            return backlog
        return [BacklogItem.from_dict(item) for item in raw]

    def save_backlog(self, items: List[BacklogItem]) -> None:
        self.ctx.write_json(self.backlog_file_path(), [asdict(item) for item in items])

    def load_run_state(self) -> Dict[str, Any]:
        return self.ctx.read_json(
            self.run_state_file_path(),
            default={
                "status": "not_started",
                "objective": "",
                "updated_at": None,
                "current_iteration": 0,
                "current_backlog_item": None,
                "last_iteration_report": None,
                "pending_admin_requests": [],
            },
        )

    def save_run_state(self, payload: Dict[str, Any]) -> Path:
        payload = dict(payload)
        payload["updated_at"] = time.time()
        return self.ctx.write_json(self.run_state_file_path(), payload)

    def next_pending_backlog_item(self, items: List[BacklogItem]) -> Optional[BacklogItem]:
        for item in items:
            if item.status == "pending":
                return item
        return None

    def write_iteration_report(self, iteration_number: int, payload: Dict[str, Any]) -> Path:
        rel = f"{self.iteration_reports_dir().rstrip('/')}/iteration_{iteration_number:03d}.json"
        return self.ctx.write_json(rel, payload)

    def _pending_admin_requests(self) -> List[Dict[str, Any]]:
        if callable(AUTONOMY_PENDING_ADMIN_REQUESTS):
            return AUTONOMY_PENDING_ADMIN_REQUESTS(self.ctx)
        return []

    def _execute_backlog_item_work(self, item: BacklogItem) -> Dict[str, Any]:
        if not callable(AUTONOMY_EXECUTE_WORK_ITEM):
            return {"success": False, "summary": "No autonomy executor available", "changed_files": []}
        return AUTONOMY_EXECUTE_WORK_ITEM(self.ctx, item, agents=self.agents)

    def _restore_snapshot(self, snapshot_manifest_path: Optional[str]) -> None:
        if snapshot_manifest_path and callable(AUTONOMY_RESTORE_SNAPSHOT):
            AUTONOMY_RESTORE_SNAPSHOT(self.ctx, snapshot_manifest_path)

    def _short_failure_summary(self, pytest_result: Dict[str, Any]) -> str:
        stdout = str(pytest_result.get("stdout", "")).strip()
        stderr = str(pytest_result.get("stderr", "")).strip()
        combined = "\n".join(part for part in [stdout, stderr] if part).strip()
        if not combined:
            return "Tests failed with no output."
        lines = [line.rstrip() for line in combined.splitlines() if line.strip()]
        return "\n".join(lines[-20:])

    def _build_or_smoke_failure_summary(self, result: Dict[str, Any], default_message: str) -> str:
        stdout = str(result.get("stdout", "")).strip()
        stderr = str(result.get("stderr", "")).strip()
        try:
            payload = json.loads(stdout) if stdout.startswith("{") else {}
        except Exception:
            payload = {}
        report_errors = payload.get("errors", []) if isinstance(payload, dict) else []
        pieces = [part for part in [stderr, "\n".join(report_errors), stdout] if part]
        combined = "\n".join(pieces).strip()
        if not combined:
            return default_message
        lines = [line.rstrip() for line in combined.splitlines() if line.strip()]
        return "\n".join(lines[-25:])

    def _run_android_validation(self) -> Dict[str, Any]:
        validation: Dict[str, Any] = {"build": None, "smoke_test": None, "ok": True}
        if self.ctx.get_setting("orchestration", "auto_build_android", default=False):
            build_result = self.ctx.tool_registry["android_build"].run(self.ctx, mode="debug", dry_run=self.ctx.dry_run)
            validation["build"] = build_result
            validation["ok"] = validation["ok"] and build_result.get("returncode", 1) == 0
            if validation["ok"] and self.ctx.get_setting("orchestration", "auto_smoke_test_android", default=False):
                smoke_result = self.ctx.tool_registry["android_smoke_test"].run(
                    self.ctx,
                    package_name=self.ctx.get_setting("android", "smoke_test_package_name", default=self.ctx.get_setting("android", "package_name", default="com.example.linksaver")),
                    dry_run=self.ctx.dry_run,
                )
                validation["smoke_test"] = smoke_result
                validation["ok"] = validation["ok"] and smoke_result.get("returncode", 1) == 0
        return validation

    def run_autonomous_development_loop(self, objective: str) -> Dict[str, Any]:
        self.ctx.log("Starting autonomous development loop")
        summary: Dict[str, Any] = {
            "objective": objective,
            "bootstrap": None,
            "iterations": [],
            "release": None,
            "status": "running",
        }

        pending = self._pending_admin_requests()
        if pending:
            summary["status"] = "paused_waiting_admin"
            summary["pending_admin_requests"] = pending
            self.save_run_state(summary)
            return summary

        summary["orchestrator"] = self.agents["orchestrator"].execute(self.ctx, objective=objective)
        summary["bootstrap"] = self.run_workflow("bootstrap")
        self.save_run_state(
            {
                "status": "running",
                "objective": objective,
                "current_iteration": 0,
                "current_backlog_item": None,
                "last_iteration_report": None,
                "pending_admin_requests": [],
            }
        )

        max_iterations = int(self.ctx.get_setting("orchestration", "max_iterations", default=3))
        max_repair_attempts = int(self.ctx.get_setting("orchestration", "max_repair_attempts", default=2))

        for iteration_number in range(1, max_iterations + 1):
            pending = self._pending_admin_requests()
            if pending:
                summary["status"] = "paused_waiting_admin"
                summary["pending_admin_requests"] = pending
                self.save_run_state(
                    {
                        "status": "paused_waiting_admin",
                        "objective": objective,
                        "current_iteration": iteration_number - 1,
                        "current_backlog_item": None,
                        "last_iteration_report": summary["iterations"][-1]["report_path"] if summary["iterations"] else None,
                        "pending_admin_requests": pending,
                    }
                )
                break

            backlog = self.load_backlog()
            item = self.next_pending_backlog_item(backlog)
            if item is None:
                self.ctx.log("No pending backlog items remain")
                summary["status"] = "completed_backlog"
                self.save_run_state(
                    {
                        "status": "completed_backlog",
                        "objective": objective,
                        "current_iteration": iteration_number - 1,
                        "current_backlog_item": None,
                        "last_iteration_report": summary["iterations"][-1]["report_path"] if summary["iterations"] else None,
                        "pending_admin_requests": [],
                    }
                )
                break

            item.status = "active"
            item.attempts += 1
            self.save_backlog(backlog)

            self.save_run_state(
                {
                    "status": "running",
                    "objective": objective,
                    "current_iteration": iteration_number,
                    "current_backlog_item": asdict(item),
                    "last_iteration_report": summary["iterations"][-1]["report_path"] if summary["iterations"] else None,
                    "pending_admin_requests": [],
                }
            )

            work_result = self._execute_backlog_item_work(item)

            scope = (
                f"{item.title}\n\n"
                f"{item.description}\n\n"
                "Acceptance criteria:\n- " + "\n- ".join(item.acceptance_criteria)
            )
            result = self.run_workflow("delivery_iteration", scope=scope, backlog_item=item)

            pytest_result = result.details.get("pytest", {})
            tests_ok = bool(pytest_result.get("returncode", 0) == 0)
            android_validation = self._run_android_validation() if tests_ok and work_result.get("success", False) else {"build": None, "smoke_test": None, "ok": tests_ok}
            fully_valid = bool(tests_ok and work_result.get("success", False) and android_validation.get("ok", True))

            if fully_valid:
                item.status = "done"
                item.notes.append(f"Iteration {iteration_number}: work executed and validation passed")
                item.metadata.pop("last_failure_summary", None)
            else:
                snapshot_manifest = work_result.get("snapshot_manifest")
                if snapshot_manifest:
                    self._restore_snapshot(snapshot_manifest)

                if not tests_ok:
                    failure_summary = self._short_failure_summary(pytest_result)
                elif android_validation.get("build") and android_validation["build"].get("returncode", 1) != 0:
                    failure_summary = self._build_or_smoke_failure_summary(android_validation["build"], "Android build failed")
                elif android_validation.get("smoke_test") and android_validation["smoke_test"].get("returncode", 1) != 0:
                    failure_summary = self._build_or_smoke_failure_summary(android_validation["smoke_test"], "Android smoke test failed")
                else:
                    failure_summary = str(work_result.get("summary", "Work execution failed")).strip() or "Work execution failed"
                item.metadata["last_failure_summary"] = failure_summary

                if item.attempts >= max_repair_attempts:
                    item.status = "failed"
                    item.notes.append(
                        f"Iteration {iteration_number}: failed after max attempts; rolled back latest snapshot"
                    )
                else:
                    item.status = "pending"
                    item.notes.append(
                        f"Iteration {iteration_number}: failed validation; rolled back and returned to backlog"
                    )

            backlog = self.load_backlog()
            for idx, candidate in enumerate(backlog):
                if candidate.item_id == item.item_id:
                    backlog[idx] = item
                    break
            self.save_backlog(backlog)

            payload = {
                "iteration_number": iteration_number,
                "backlog_item": asdict(item),
                "work_result": work_result,
                "workflow_result": {
                    "success": result.success,
                    "summary": result.summary,
                    "details": result.details,
                },
                "tests_ok": tests_ok,
                "android_validation": android_validation,
                "validation_ok": fully_valid,
            }
            report_path = self.write_iteration_report(iteration_number, payload)
            payload["report_path"] = str(report_path)

            self.ctx.add_artifact(
                Artifact(
                    name=f"iteration_{iteration_number:03d}_report",
                    path=str(report_path),
                    kind="iteration_report",
                    created_by="orchestrator",
                    metadata={"iteration_number": iteration_number, "tests_ok": tests_ok},
                )
            )
            summary["iterations"].append(payload)

            self.save_run_state(
                {
                    "status": "running",
                    "objective": objective,
                    "current_iteration": iteration_number,
                    "current_backlog_item": asdict(item),
                    "last_iteration_report": str(report_path),
                    "pending_admin_requests": [],
                }
            )

        if summary.get("status") not in {"paused_waiting_admin"}:
            summary["release"] = self.run_workflow("release")
            pending = self._pending_admin_requests()
            if pending or summary["release"].details.get("admin_gateway", {}).get("status") == "pending":
                summary["status"] = "paused_waiting_admin"
                summary["pending_admin_requests"] = pending
            else:
                summary["status"] = summary.get("status", "finished")

        self.save_run_state(
            {
                "status": summary.get("status", "finished"),
                "objective": objective,
                "current_iteration": len(summary.get("iterations", [])),
                "current_backlog_item": summary["iterations"][-1]["backlog_item"] if summary.get("iterations") else None,
                "last_iteration_report": summary["iterations"][-1]["report_path"] if summary.get("iterations") else None,
                "pending_admin_requests": summary.get("pending_admin_requests", self._pending_admin_requests()),
            }
        )
        return summary


def ensure_directories(ctx: ExecutionContext) -> None:
    project_root = Path(ctx.project_root)
    for key in ("artifacts_dir", "logs_dir", "docs_dir"):
        directory = project_root / Path(ctx.get_setting("project", key, default=f"./{key}"))
        if ctx.dry_run:
            ctx.log(f"[dry-run] ensure directory {directory}")
        else:
            directory.mkdir(parents=True, exist_ok=True)

    extra_dirs = [
        ctx.get_setting("orchestration", "iteration_reports_dir", default="./artifacts/iterations"),
        ctx.get_setting("orchestration", "plan_artifacts_dir", default="./artifacts/plans"),
        "./artifacts/admin/requests",
        "./artifacts/admin/responses",
        "./artifacts/snapshots",
        "./artifacts/android",
        "./scripts/android",
        "./android",
    ]
    for rel in extra_dirs:
        directory = project_root / Path(rel)
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


def print_summary(results: Dict[str, Any]) -> None:
    print("\n=== MAS SUMMARY ===")
    for key, value in results.items():
        if isinstance(value, WorkflowResult):
            print(f"- {key}: success={value.success} summary={value.summary}")
        elif isinstance(value, list):
            print(f"- {key}: {len(value)} entries")
        else:
            print(f"- {key}: {type(value).__name__}")


def compile_app_spec_to_backlog(spec: Dict[str, Any]) -> List[BacklogItem]:
    app_name = str(spec.get("app_name") or "Generated Android App").strip() or "Generated Android App"
    features = list(spec.get("features") or [])
    screens = list(spec.get("screens") or [])
    data_models = list(spec.get("data_models") or [])
    integrations = list(spec.get("integrations") or [])

    items: List[BacklogItem] = [
        BacklogItem(
            item_id="spec-bootstrap-001",
            title=f"Align project for {app_name}",
            description=(
                f"Update documentation, packaging metadata, and generated artifacts so the repo reflects the app spec for {app_name}."
            ),
            acceptance_criteria=[
                "Project artifacts mention the target app name",
                "Packaging metadata remains valid",
                "Tests still pass",
            ],
            metadata={
                "executor": "llm_patch",
                "patch_target_hint": ["README.md", "buildozer.spec", "docs/ANDROID_BUILD.md"],
            },
        )
    ]

    for index, screen in enumerate(screens, start=1):
        screen_name = str(screen.get("name") or f"Screen {index}").strip() or f"Screen {index}"
        purpose = str(screen.get("purpose") or "support the requested workflow").strip()
        items.append(
            BacklogItem(
                item_id=f"spec-screen-{index:03d}",
                title=f"Implement {screen_name} screen flow",
                description=f"Extend the Kivy app to support the {screen_name} screen so it can {purpose}.",
                acceptance_criteria=[
                    f"The UI exposes the {screen_name} flow",
                    "The behavior is reflected in the Kivy adapter or use cases",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": ["app_frameworks/kivy_adapter.py", "app/use_cases/media_links.py"],
                    "spec_context": screen,
                },
            )
        )

    for index, feature in enumerate(features, start=1):
        if isinstance(feature, dict):
            title = str(feature.get("name") or feature.get("title") or f"Feature {index}").strip() or f"Feature {index}"
            description = str(feature.get("description") or feature.get("goal") or "Implement the requested feature.").strip()
        else:
            title = str(feature).strip() or f"Feature {index}"
            description = f"Implement the feature: {title}."
        items.append(
            BacklogItem(
                item_id=f"spec-feature-{index:03d}",
                title=f"Implement feature: {title}",
                description=description,
                acceptance_criteria=[
                    f"The feature '{title}' is implemented or scaffolded in the Kivy app",
                    "Relevant code paths are updated consistently",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": ["app/use_cases/media_links.py", "app_frameworks/kivy_adapter.py", "README.md"],
                    "spec_context": feature,
                },
            )
        )

    if data_models:
        items.append(
            BacklogItem(
                item_id="spec-data-models-001",
                title="Align data model layer to app spec",
                description="Update domain and storage layers so the requested data models are represented in the codebase.",
                acceptance_criteria=[
                    "Requested data models are represented in the codebase or documented as scaffolding",
                    "Storage/use-case layers stay coherent",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": ["app/domain/models.py", "app/services/storage.py", "app/use_cases/media_links.py"],
                    "spec_context": data_models,
                },
            )
        )

    if integrations:
        items.append(
            BacklogItem(
                item_id="spec-integrations-001",
                title="Document and scaffold requested integrations",
                description="Document requested external integrations and add safe scaffolding points where practical.",
                acceptance_criteria=[
                    "Requested integrations are documented",
                    "Safe scaffolding points exist for future live wiring",
                    "Tests still pass",
                ],
                metadata={
                    "executor": "llm_patch",
                    "patch_target_hint": ["README.md", ".env.example", "docs/ANDROID_BUILD.md"],
                    "spec_context": integrations,
                },
            )
        )

    items.append(
        BacklogItem(
            item_id="spec-android-validation-001",
            title="Validate Android packaging path for spec-driven build",
            description="Run the packaging path for the current app spec and persist structured build artifacts.",
            acceptance_criteria=[
                "Android build command is runnable",
                "Android build report is generated",
                "The project is ready for smoke testing",
            ],
            metadata={"executor": "create_android_packaging_files"},
        )
    )
    return items


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or [])
    if not argv:
        import sys
        argv = list(sys.argv[1:])

    project_root = "."
    dry_run = True
    autonomous = False
    show_status = False
    objective = (
        "Autonomously develop a high-quality Android app in Python for saving, "
        "organizing, sharing, and accessing remote and local media links."
    )
    approve_request_id: Optional[str] = None
    decision: Optional[str] = None
    note = ""
    android_package = False
    android_smoke_test = False
    android_mode = "debug"
    app_spec_path: Optional[str] = None
    compile_spec_only = False

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--project-root" and i + 1 < len(argv):
            project_root = argv[i + 1]
            i += 2
        elif arg == "--real-run":
            dry_run = False
            i += 1
        elif arg == "--autonomous":
            autonomous = True
            i += 1
        elif arg == "--status":
            show_status = True
            i += 1
        elif arg == "--objective" and i + 1 < len(argv):
            objective = argv[i + 1]
            i += 2
        elif arg == "--approve-request" and i + 1 < len(argv):
            approve_request_id = argv[i + 1]
            i += 2
        elif arg == "--android-package":
            android_package = True
            i += 1
        elif arg == "--android-smoke-test":
            android_smoke_test = True
            i += 1
        elif arg == "--android-mode" and i + 1 < len(argv):
            android_mode = argv[i + 1]
            i += 2
        elif arg == "--app-spec" and i + 1 < len(argv):
            app_spec_path = argv[i + 1]
            i += 2
        elif arg == "--compile-spec":
            compile_spec_only = True
            i += 1
        elif arg == "--decision" and i + 1 < len(argv):
            decision = argv[i + 1].strip().lower()
            i += 2
        elif arg == "--note" and i + 1 < len(argv):
            note = argv[i + 1]
            i += 2
        else:
            print(f"Unknown argument: {arg}")
            return 2

    ctx = make_context(project_root=project_root)
    ctx.dry_run = dry_run

    try:
        ensure_directories(ctx)
        mas = MultiAgentSystem(ctx)

        if app_spec_path:
            spec_data = json.loads(ctx.resolve_path(app_spec_path).read_text(encoding="utf-8"))
            backlog_items = compile_app_spec_to_backlog(spec_data)
            mas.save_backlog(backlog_items)
            ctx.write_json(ctx.get_setting("orchestration", "app_spec_file", default="./artifacts/app_spec.json"), spec_data)
            if compile_spec_only:
                print(json.dumps({"compiled": True, "backlog_items": len(backlog_items), "app_name": spec_data.get("app_name", "")}, indent=2))
                return 0

        if show_status:
            print(json.dumps(mas.load_run_state(), indent=2))
            return 0

        if android_package:
            result = ctx.tool_registry["android_build"].run(ctx, mode=android_mode, dry_run=dry_run)
            print(json.dumps(result, indent=2))
            return 0

        if android_smoke_test:
            result = ctx.tool_registry["android_smoke_test"].run(
                ctx,
                package_name=ctx.get_setting("android", "package_name", default="com.example.linksaver"),
                dry_run=dry_run,
            )
            print(json.dumps(result, indent=2))
            return 0

        if approve_request_id:
            if not callable(AUTONOMY_RECORD_ADMIN_RESPONSE):
                print("Approval recording is not available.")
                return 1
            if decision not in {"approved", "rejected"}:
                print("Use --decision approved or --decision rejected")
                return 2
            payload = AUTONOMY_RECORD_ADMIN_RESPONSE(
                ctx,
                request_id=approve_request_id,
                approved=(decision == "approved"),
                note=note,
            )
            print(json.dumps(payload, indent=2))
            return 0

        if autonomous:
            results = mas.run_autonomous_development_loop(objective=objective)
        else:
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