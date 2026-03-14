from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import os
import subprocess
import sys


class ToolError(RuntimeError):
    pass


class BaseTool:
    name = "base_tool"
    description = "Base tool"

    def run(self, ctx, **kwargs: Any) -> Any:
        raise NotImplementedError


class SafeSubprocessTool(BaseTool):
    name = "safe_subprocess"
    description = "Runs whitelisted subprocess commands inside the project"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        from mas_guardrails import guardrail_check

        command = kwargs.get("command")
        cwd = kwargs.get("cwd", ctx.project_root)
        env_overrides = kwargs.get("env") or {}

        if not command or not isinstance(command, list):
            raise ToolError("command must be a list")

        executable_name = Path(command[0]).name.lower()
        executable_stem = Path(command[0]).stem.lower()
        allowed = {str(item).lower() for item in ctx.policies.get("allowed_subprocess_commands", [])}
        if executable_name not in allowed and executable_stem not in allowed:
            raise ToolError(f"command not allowed: {executable_name}")

        ok, reason = guardrail_check("subprocess", ctx, {"command": command, "cwd": cwd})
        if not ok:
            raise ToolError(reason)

        if ctx.dry_run:
            return {
                "returncode": 0,
                "stdout": f"[dry-run] {' '.join(command)}",
                "stderr": "",
            }

        env = os.environ.copy()
        env.update({str(k): str(v) for k, v in env_overrides.items()})
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Reads a UTF-8 file inside the project"

    def run(self, ctx, **kwargs: Any) -> str:
        from mas_guardrails import guardrail_check

        path = kwargs["path"]
        ok, reason = guardrail_check("read_file", ctx, {"path": path})
        if not ok:
            raise ToolError(reason)

        full = Path(path)
        if not full.is_absolute():
            full = Path(ctx.project_root) / full
        return full.read_text(encoding="utf-8")


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Writes a UTF-8 file inside the project"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        from mas_guardrails import guardrail_check

        path = kwargs["path"]
        content = kwargs.get("content", "")

        ok, reason = guardrail_check("write_file", ctx, {"path": path})
        if not ok:
            raise ToolError(reason)

        full = Path(path)
        if not full.is_absolute():
            full = Path(ctx.project_root) / full
        full.parent.mkdir(parents=True, exist_ok=True)

        if ctx.dry_run:
            return {"path": str(full), "written": False, "dry_run": True}

        full.write_text(content, encoding="utf-8")
        return {"path": str(full), "written": True, "dry_run": False}


class JsonWriteTool(BaseTool):
    name = "json_write"
    description = "Writes a JSON file inside the project"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs["path"]
        data = kwargs.get("data", {})
        return FileWriteTool().run(
            ctx,
            path=path,
            content=json.dumps(data, indent=2, ensure_ascii=False),
        )


class SettingsViewTool(BaseTool):
    name = "settings_view"
    description = "Returns current merged settings"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        return ctx.settings


class EnvTemplateViewTool(BaseTool):
    name = "env_template_view"
    description = "Returns the .env.example content if present"

    def run(self, ctx, **kwargs: Any) -> str:
        env_example = Path(ctx.project_root) / ".env.example"
        if not env_example.exists():
            return ""
        return env_example.read_text(encoding="utf-8")


class DirectoryTreeTool(BaseTool):
    name = "directory_tree"
    description = "Builds a small text tree of the project structure"

    def run(self, ctx, **kwargs: Any) -> str:
        root = Path(ctx.project_root)
        max_depth = int(kwargs.get("max_depth", 3))
        lines: List[str] = [root.name + "/"]

        def walk(path: Path, depth: int) -> None:
            if depth > max_depth:
                return
            for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                indent = "  " * depth
                suffix = "/" if child.is_dir() else ""
                lines.append(f"{indent}{child.name}{suffix}")
                if child.is_dir():
                    walk(child, depth + 1)

        walk(root, 1)
        return "\n".join(lines)


class BacklogViewTool(BaseTool):
    name = "backlog_view"
    description = "Returns the current backlog file contents if present"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        backlog_rel = ctx.get_setting("orchestration", "backlog_file", default="./artifacts/backlog.json")
        backlog_path = Path(ctx.project_root) / Path(backlog_rel)
        if not backlog_path.exists():
            return {"items": []}
        return json.loads(backlog_path.read_text(encoding="utf-8"))


class GitStatusTool(BaseTool):
    name = "git_status"
    description = "Returns git status"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        return SafeSubprocessTool().run(ctx, command=["git", "status", "--short", "--branch"], cwd=ctx.project_root)


class GitDiffTool(BaseTool):
    name = "git_diff"
    description = "Returns git diff"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", ["--stat"])
        return SafeSubprocessTool().run(ctx, command=["git", "diff", *args], cwd=ctx.project_root)


class GitTool(BaseTool):
    name = "git"
    description = "Runs arbitrary git subcommands"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", [])
        return SafeSubprocessTool().run(ctx, command=["git", *args], cwd=ctx.project_root)


class GradleTasksTool(BaseTool):
    name = "gradle_tasks"
    description = "Lists or runs gradle tasks"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", ["tasks", "--all"])
        use_wrapper = kwargs.get("use_wrapper", True)
        exe = "./gradlew" if use_wrapper else "gradle"
        return SafeSubprocessTool().run(ctx, command=[exe, *args], cwd=ctx.project_root)


class EmulatorStatusTool(BaseTool):
    name = "emulator_status"
    description = "Returns adb devices"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        return SafeSubprocessTool().run(ctx, command=["adb", "devices"], cwd=ctx.project_root)


class InternetRequestTool(BaseTool):
    name = "internet_request"
    description = "Checks whether internet access would require admin approval"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        from mas_guardrails import guardrail_check

        purpose = kwargs.get("purpose", "unspecified")
        ok, reason = guardrail_check("internet_access", ctx, {"purpose": purpose})
        return {
            "approved": ok,
            "reason": reason,
            "requires_admin": not ok,
            "purpose": purpose,
        }


class PytestRunnerTool(BaseTool):
    name = "pytest_runner"
    description = "Runs the Python test suite"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", ["-q"])
        return SafeSubprocessTool().run(ctx, command=["pytest", *args], cwd=ctx.project_root)




class AndroidPreflightTool(BaseTool):
    name = "android_preflight"
    description = "Runs the scripted Android preflight checks"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        script = Path(ctx.project_root) / "scripts" / "android" / "preflight_check.py"
        if not script.exists():
            raise ToolError("Android preflight script is missing")
        command = [sys.executable, str(script), "--project-root", ctx.project_root]
        return SafeSubprocessTool().run(ctx, command=command, cwd=ctx.project_root)


class AndroidBuildTool(BaseTool):
    name = "android_build"
    description = "Runs the scripted Android packaging flow"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        mode = kwargs.get("mode", "debug")
        script = Path(ctx.project_root) / "scripts" / "android" / "build_android.py"
        if not script.exists():
            raise ToolError("Android build script is missing")
        command = [sys.executable, str(script), "--project-root", ctx.project_root, "--mode", mode]
        if ctx.dry_run or kwargs.get("dry_run"):
            command.append("--dry-run")
        return SafeSubprocessTool().run(ctx, command=command, cwd=ctx.project_root)


class AndroidSmokeTestTool(BaseTool):
    name = "android_smoke_test"
    description = "Runs the scripted Android adb smoke test flow"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        script = Path(ctx.project_root) / "scripts" / "android" / "smoke_test_android.py"
        if not script.exists():
            raise ToolError("Android smoke test script is missing")
        command = [sys.executable, str(script), "--project-root", ctx.project_root]
        if ctx.dry_run or kwargs.get("dry_run"):
            command.append("--dry-run")
        package_name = kwargs.get("package_name")
        if package_name:
            command.extend(["--package-name", package_name])
        return SafeSubprocessTool().run(ctx, command=command, cwd=ctx.project_root)


TOOL_REGISTRY = {
    "safe_subprocess": SafeSubprocessTool(),
    "file_read": FileReadTool(),
    "file_write": FileWriteTool(),
    "json_write": JsonWriteTool(),
    "settings_view": SettingsViewTool(),
    "env_template_view": EnvTemplateViewTool(),
    "directory_tree": DirectoryTreeTool(),
    "backlog_view": BacklogViewTool(),
    "git_status": GitStatusTool(),
    "git_diff": GitDiffTool(),
    "git": GitTool(),
    "gradle_tasks": GradleTasksTool(),
    "emulator_status": EmulatorStatusTool(),
    "internet_request": InternetRequestTool(),
    "pytest_runner": PytestRunnerTool(),
    "android_preflight": AndroidPreflightTool(),
    "android_build": AndroidBuildTool(),
    "android_smoke_test": AndroidSmokeTestTool(),
}
