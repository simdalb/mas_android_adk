"""
mas_android_adk.py

Initial multi-agent system orchestration skeleton for autonomous Android app
development in Python, using Google ADK initially.

This file is intentionally designed so it should NOT need modification when the
future companion modules are created. It imports from not-yet-existing modules
using stable import points and safe fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
import importlib
import json
import subprocess
import sys
import time
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
        "name": "android-mas-project",
        "root_dir": ".",
        "artifacts_dir": "./artifacts",
        "logs_dir": "./logs",
        "docs_dir": "./docs",
    },
    "framework": {
        "selected": "kivy",
        "available": ["kivy", "beeware", "flet"],
    },
    "llm": {
        "planner_model": "gemini-2.0-flash",
        "coder_model": "gemini-2.0-flash",
        "reviewer_model": "gemini-2.0-flash",
        "documenter_model": "gemini-2.0-flash",
        "cost_mode": "balanced",
    },
    "orchestration": {
        "max_iterations": 3,
        "max_repair_attempts": 2,
        "autonomous_mode": True,
        "require_admin_for_release": True,
        "require_admin_for_internet": True,
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

    if action in {"write_file", "delete_file", "move_file", "mkdir"}:
        target = payload.get("path")
        if target:
            try:
                target_path = Path(target).resolve()
                if project_root not in [target_path, *target_path.parents]:
                    return False, f"Path outside project root blocked: {target_path}"
            except Exception as exc:
                return False, f"Invalid filesystem path: {exc}"

    if action == "internet_access" and ctx.require_admin_for_internet:
        return False, "Internet access requires administrator approval."

    if action == "modify_environment":
        return False, "Environment modification is blocked by policy."

    return True, "Allowed by default fallback guardrail."


SETTINGS = _get_attr(_SETTINGS, "SETTINGS", DEFAULT_SETTINGS)
PROMPTS = _get_attr(_PROMPTS, "PROMPTS", DEFAULT_PROMPTS)
GUARDRAIL_CHECK = _get_attr(_GUARDRAILS, "guardrail_check", _default_guardrail_check)
TOOL_REGISTRY = _get_attr(_TOOLS, "TOOL_REGISTRY", DEFAULT_TOOL_REGISTRY)
LLM_REGISTRY = _get_attr(_LLMS, "LLM_REGISTRY", DEFAULT_LLM_REGISTRY)
POLICIES = _get_attr(_POLICIES, "POLICIES", DEFAULT_POLICIES)
WORKFLOW_HOOKS = _get_attr(_HOOKS, "WORKFLOW_HOOKS", DEFAULT_HOOKS)


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
    timestamp: float = field(default_factory=time.time)


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

    def get_setting(self, *path: str, default: Any = None) -> Any:
        node: Any = self.settings
        for part in path:
            if not isinstance(node, dict):
                return default
            node = node.get(part)
            if node is None:
                return default
        return node


class ToolError(RuntimeError):
    pass


class BaseTool:
    name = "base_tool"
    description = "Base tool"

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Any:
        raise NotImplementedError


class SafeSubprocessTool(BaseTool):
    name = "safe_subprocess"
    description = "Run whitelisted subprocess commands within project root"

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        command = kwargs.get("command")
        cwd = kwargs.get("cwd", ctx.project_root)

        if not command or not isinstance(command, list):
            raise ToolError("Command must be a list.")

        exe = Path(command[0]).name
        allowed = set(ctx.policies.get("allowed_subprocess_commands", []))
        if exe not in allowed:
            raise ToolError(f"Command not allowed by policy: {exe}")

        ok, reason = GUARDRAIL_CHECK("subprocess", ctx, {"command": command, "cwd": cwd})
        if not ok:
            raise ToolError(reason)

        ctx.log(f"Subprocess: {' '.join(command)}")

        if ctx.dry_run:
            return {"returncode": 0, "stdout": "[dry-run]", "stderr": ""}

        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
        return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read a file within project root"

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> str:
        path = kwargs["path"]
        full = Path(path)
        if not full.is_absolute():
            full = Path(ctx.project_root) / full
        return full.read_text(encoding="utf-8")


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Write a file within project root"

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs["path"]
        content = kwargs.get("content", "")
        target = Path(path)
        if not target.is_absolute():
            target = Path(ctx.project_root) / target

        ok, reason = GUARDRAIL_CHECK("write_file", ctx, {"path": str(target)})
        if not ok:
            raise ToolError(reason)

        target.parent.mkdir(parents=True, exist_ok=True)

        if ctx.dry_run:
            ctx.log(f"[dry-run] write {target}")
            return {"path": str(target), "written": False, "dry_run": True}

        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "written": True, "dry_run": False}


class GitTool(BaseTool):
    name = "git"
    description = "Run git commands"

    def __init__(self) -> None:
        self.proc = SafeSubprocessTool()

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        return self.proc.run(ctx, command=["git", *kwargs.get("args", [])], cwd=ctx.project_root)


class GradleTool(BaseTool):
    name = "gradle"
    description = "Run gradle/gradlew commands"

    def __init__(self) -> None:
        self.proc = SafeSubprocessTool()

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        use_wrapper = kwargs.get("use_wrapper", True)
        exe = "./gradlew" if use_wrapper else "gradle"
        return self.proc.run(ctx, command=[exe, *kwargs.get("args", [])], cwd=ctx.project_root)


class EmulatorTool(BaseTool):
    name = "emulator"
    description = "Run adb/emulator commands"

    def __init__(self) -> None:
        self.proc = SafeSubprocessTool()

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        mode = kwargs.get("mode", "adb")
        exe = "adb" if mode == "adb" else "emulator"
        return self.proc.run(ctx, command=[exe, *kwargs.get("args", [])], cwd=ctx.project_root)


class InternetRequestTool(BaseTool):
    name = "internet_request"
    description = "Request internet via admin workflow"

    def run(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        purpose = kwargs.get("purpose", "unspecified")
        ok, reason = GUARDRAIL_CHECK("internet_access", ctx, {"purpose": purpose})
        return {"approved": ok, "reason": reason, "requires_admin": not ok, "purpose": purpose}


BUILTIN_TOOLS: Dict[str, BaseTool] = {
    "safe_subprocess": SafeSubprocessTool(),
    "file_read": FileReadTool(),
    "file_write": FileWriteTool(),
    "git": GitTool(),
    "gradle": GradleTool(),
    "emulator": EmulatorTool(),
    "internet_request": InternetRequestTool(),
}
MERGED_TOOL_REGISTRY: Dict[str, Any] = {**BUILTIN_TOOLS, **TOOL_REGISTRY}


class BaseLLM:
    model_name = "base-llm"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    model_name = "mock-llm"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return f"[MOCK]\nSYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"


class GoogleADKLLMAdapter(BaseLLM):
    def __init__(self, model_name: str = "gemini-2.0-flash") -> None:
        self.model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return f"[GOOGLE ADK PLACEHOLDER {self.model_name}]\nSYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"


BUILTIN_LLMS: Dict[str, BaseLLM] = {
    "mock": MockLLM(),
    "gemini-2.0-flash": GoogleADKLLMAdapter("gemini-2.0-flash"),
    "gemini-2.5-pro": GoogleADKLLMAdapter("gemini-2.5-pro"),
}
MERGED_LLM_REGISTRY: Dict[str, BaseLLM] = {**BUILTIN_LLMS, **LLM_REGISTRY}


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

    def get_prompt(self, ctx: ExecutionContext) -> str:
        return ctx.prompts.get(self.prompt_key, f"You are {self.name}.")

    def get_llm(self, ctx: ExecutionContext) -> Optional[BaseLLM]:
        if not self.llm_name:
            return None
        return ctx.llm_registry.get(self.llm_name)

    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError


class LLMWorkerAgent(Agent):
    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        llm = self.get_llm(ctx)
        if llm is None:
            raise AgentError(f"No LLM for {self.name}")
        response = llm.generate(
            system_prompt=self.get_prompt(ctx),
            user_prompt=kwargs.get("user_prompt", ""),
        )
        return {"agent": self.name, "response": response}


class CustomAgent(Agent):
    def __init__(self, *args: Any, handler: Optional[Callable[..., Dict[str, Any]]] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.handler = handler

    def execute(self, ctx: ExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        if self.handler is None:
            raise AgentError(f"No handler for {self.name}")
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
        _run_hook("before_bootstrap", ctx)
        framework = ctx.get_setting("framework", "selected", default="kivy")
        project_name = ctx.get_setting("project", "name", default="android-mas-project")

        details = {
            "architect": agents["architect"].execute(
                ctx,
                user_prompt=f"Design initial MAS and app architecture for {project_name} using selected framework {framework}.",
            ),
            "framework_selector": agents["framework_selector"].execute(
                ctx,
                user_prompt="Explain the framework choice and the abstraction needed to swap frameworks by YAML change.",
            ),
            "product_manager": agents["product_manager"].execute(
                ctx,
                user_prompt="Create an initial backlog for a media-links Android app with auth, sync, ads, subscriptions, and offline support.",
            ),
            "documentation_writer": agents["documentation_writer"].execute(
                ctx,
                user_prompt="Draft the initial documentation plan for ARCHITECTURE.md and admin HOW-TO guides.",
            ),
        }
        ctx.shared_state["bootstrap"] = details
        _run_hook("after_bootstrap", ctx)
        return WorkflowResult(True, "Bootstrap workflow completed", details)


class DeliveryIterationWorkflow(Workflow):
    name = "delivery_iteration"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        _run_hook("before_delivery_iteration", ctx)
        scope = kwargs.get("scope", "Implement next backlog item.")
        details = {
            "coder": agents["android_coder"].execute(ctx, user_prompt=scope),
            "tester": agents["test_engineer"].execute(
                ctx,
                user_prompt="Create or run unit, integration, and instrumentation test steps for the latest implementation.",
            ),
            "security": agents["security_reviewer"].execute(
                ctx,
                user_prompt="Review the latest changes for privacy, security, secrets handling, and backend rule safety.",
            ),
            "git": agents["git_manager"].execute(
                ctx,
                user_prompt="Prepare commit plan and branch summary for the current changes.",
            ),
        }
        ctx.shared_state.setdefault("iterations", []).append(details)
        _run_hook("after_delivery_iteration", ctx)
        return WorkflowResult(True, "Delivery iteration completed", details)


class ReleaseWorkflow(Workflow):
    name = "release"

    def run(self, ctx: ExecutionContext, agents: Dict[str, Agent], **kwargs: Any) -> WorkflowResult:
        _run_hook("before_release", ctx)
        release_packet = agents["release_manager"].execute(
            ctx,
            user_prompt="Prepare release readiness packet including tests, risks, security summary, and admin decision request.",
        )
        admin = agents["admin_gateway"].execute(
            ctx,
            action="request_release_decision",
            payload={"release_packet": release_packet},
        )
        result = {"release_manager": release_packet, "admin_gateway": admin}
        ctx.shared_state["release"] = result
        _run_hook("after_release", ctx)
        return WorkflowResult(bool(admin.get("approved", False)), "Release workflow completed", result)


def orchestrator_handler(ctx: ExecutionContext, agent: Agent, **kwargs: Any) -> Dict[str, Any]:
    objective = kwargs.get("objective", "Build the Android app.")
    max_iterations = int(ctx.get_setting("orchestration", "max_iterations", default=3))
    return {
        "agent": agent.name,
        "objective": objective,
        "max_iterations": max_iterations,
        "status": "planned",
    }


def admin_gateway_handler(ctx: ExecutionContext, agent: Agent, **kwargs: Any) -> Dict[str, Any]:
    action = kwargs.get("action", "request_decision")
    payload = kwargs.get("payload", {})
    ctx.messages.append(
        Message(
            sender=agent.name,
            recipient="administrator",
            subject=action,
            content=json.dumps(payload, indent=2, default=str),
        )
    )
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
        hook(ctx)


def build_agents(ctx: ExecutionContext) -> Dict[str, Agent]:
    planner_model = ctx.get_setting("llm", "planner_model", default="gemini-2.0-flash")
    coder_model = ctx.get_setting("llm", "coder_model", default="gemini-2.0-flash")
    reviewer_model = ctx.get_setting("llm", "reviewer_model", default="gemini-2.0-flash")
    documenter_model = ctx.get_setting("llm", "documenter_model", default="gemini-2.0-flash")

    return {
        "orchestrator": CustomAgent(
            name="orchestrator",
            agent_type=AgentType.ORCHESTRATOR,
            description="Coordinates workflows and execution.",
            prompt_key="orchestrator",
            tools=["git", "file_read", "file_write"],
            handler=orchestrator_handler,
        ),
        "architect": LLMWorkerAgent(
            name="architect",
            agent_type=AgentType.ANALYSIS,
            description="Designs MAS and app architecture.",
            prompt_key="architect",
            tools=["file_read", "file_write"],
            llm_name=planner_model,
        ),
        "framework_selector": LLMWorkerAgent(
            name="framework_selector",
            agent_type=AgentType.ANALYSIS,
            description="Selects framework while preserving portability.",
            prompt_key="framework_selector",
            tools=["file_read"],
            llm_name=planner_model,
        ),
        "product_manager": LLMWorkerAgent(
            name="product_manager",
            agent_type=AgentType.ANALYSIS,
            description="Defines backlog and scope.",
            prompt_key="product_manager",
            tools=["file_read", "file_write"],
            llm_name=planner_model,
        ),
        "android_coder": LLMWorkerAgent(
            name="android_coder",
            agent_type=AgentType.CODER,
            description="Implements app changes.",
            prompt_key="android_coder",
            tools=["file_read", "file_write", "git", "gradle"],
            llm_name=coder_model,
        ),
        "test_engineer": LLMWorkerAgent(
            name="test_engineer",
            agent_type=AgentType.TESTER,
            description="Plans and runs tests.",
            prompt_key="test_engineer",
            tools=["file_read", "file_write", "gradle", "emulator"],
            llm_name=reviewer_model,
        ),
        "security_reviewer": LLMWorkerAgent(
            name="security_reviewer",
            agent_type=AgentType.REVIEWER,
            description="Reviews security and privacy.",
            prompt_key="security_reviewer",
            tools=["file_read"],
            llm_name=reviewer_model,
        ),
        "documentation_writer": LLMWorkerAgent(
            name="documentation_writer",
            agent_type=AgentType.DOCUMENTATION,
            description="Writes docs and HOW-TOs.",
            prompt_key="documentation_writer",
            tools=["file_read", "file_write"],
            llm_name=documenter_model,
        ),
        "git_manager": LLMWorkerAgent(
            name="git_manager",
            agent_type=AgentType.GIT,
            description="Manages git workflow.",
            prompt_key="git_manager",
            tools=["git", "file_read"],
            llm_name=reviewer_model,
        ),
        "release_manager": LLMWorkerAgent(
            name="release_manager",
            agent_type=AgentType.RELEASE,
            description="Prepares release evidence and packet.",
            prompt_key="release_manager",
            tools=["file_read", "git", "gradle"],
            llm_name=reviewer_model,
        ),
        "admin_gateway": CustomAgent(
            name="admin_gateway",
            agent_type=AgentType.ADMIN,
            description="Requests admin approvals only when needed.",
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
        workflow = self.workflows[workflow_name]
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
                    scope=f"Iteration {i + 1}: implement next prioritized feature or fix.",
                )
            )

        results["release"] = self.run_workflow("release")
        return results


def ensure_directories(ctx: ExecutionContext) -> None:
    root = Path(ctx.project_root)
    for key in ("artifacts_dir", "logs_dir", "docs_dir"):
        d = root / Path(ctx.get_setting("project", key, default=f"./{key}"))
        if ctx.dry_run:
            ctx.log(f"[dry-run] ensure directory {d}")
        else:
            d.mkdir(parents=True, exist_ok=True)


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
        tool_registry=MERGED_TOOL_REGISTRY,
        llm_registry=MERGED_LLM_REGISTRY,
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv or sys.argv[1:])
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