from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import subprocess


class ToolError(RuntimeError):
    pass


class BaseTool:
    name = "base_tool"
    description = "Base tool"

    def run(self, ctx, **kwargs: Any) -> Any:
        raise NotImplementedError


class SafeSubprocessTool(BaseTool):
    name = "safe_subprocess"
    description = "Executes whitelisted subprocesses"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        command = kwargs.get("command")
        cwd = kwargs.get("cwd", ctx.project_root)

        if not command or not isinstance(command, list):
            raise ToolError("command must be a list")

        exe = Path(command[0]).name
        allowed = set(ctx.policies.get("allowed_subprocess_commands", []))
        if exe not in allowed:
            raise ToolError(f"command not allowed: {exe}")

        from mas_guardrails import guardrail_check
        ok, reason = guardrail_check("subprocess", ctx, {"command": command, "cwd": cwd})
        if not ok:
            raise ToolError(reason)

        if ctx.dry_run:
            return {
                "returncode": 0,
                "stdout": f"[dry-run] {' '.join(command)}",
                "stderr": "",
            }

        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Reads UTF-8 text file"

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
    description = "Writes UTF-8 text file"

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
    description = "Writes JSON file"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        path = kwargs["path"]
        data = kwargs.get("data", {})
        content = json.dumps(data, indent=2, ensure_ascii=False)
        return FileWriteTool().run(ctx, path=path, content=content)


class GitTool(BaseTool):
    name = "git"
    description = "Runs git commands"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", [])
        return SafeSubprocessTool().run(ctx, command=["git", *args], cwd=ctx.project_root)


class GradleTool(BaseTool):
    name = "gradle"
    description = "Runs gradle wrapper"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        args = kwargs.get("args", [])
        use_wrapper = kwargs.get("use_wrapper", True)
        exe = "./gradlew" if use_wrapper else "gradle"
        return SafeSubprocessTool().run(ctx, command=[exe, *args], cwd=ctx.project_root)


class EmulatorTool(BaseTool):
    name = "emulator"
    description = "Runs adb or emulator command"

    def run(self, ctx, **kwargs: Any) -> Dict[str, Any]:
        mode = kwargs.get("mode", "adb")
        args = kwargs.get("args", [])
        exe = "adb" if mode == "adb" else "emulator"
        return SafeSubprocessTool().run(ctx, command=[exe, *args], cwd=ctx.project_root)


class InternetRequestTool(BaseTool):
    name = "internet_request"
    description = "Requests internet access"

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


TOOL_REGISTRY = {
    "safe_subprocess": SafeSubprocessTool(),
    "file_read": FileReadTool(),
    "file_write": FileWriteTool(),
    "json_write": JsonWriteTool(),
    "git": GitTool(),
    "gradle": GradleTool(),
    "emulator": EmulatorTool(),
    "internet_request": InternetRequestTool(),
}