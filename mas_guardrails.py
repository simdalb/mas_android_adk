from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple


def _is_within(root: Path, target: Path) -> bool:
    root = root.resolve()
    target = target.resolve()
    return root == target or root in target.parents


def guardrail_check(action: str, ctx, payload: Dict) -> Tuple[bool, str]:
    project_root = Path(ctx.project_root).resolve()

    if action in {"write_file", "delete_file", "move_file", "mkdir", "read_file"}:
        path_value = payload.get("path")
        if path_value:
            target = Path(path_value)
            if not target.is_absolute():
                target = project_root / target
            if not _is_within(project_root, target):
                return False, f"Blocked: path outside project root: {target}"

    if action == "subprocess":
        cwd = Path(payload.get("cwd", project_root))
        if not cwd.is_absolute():
            cwd = project_root / cwd
        if not _is_within(project_root, cwd):
            return False, f"Blocked: subprocess cwd outside project root: {cwd}"

    if action == "internet_access":
        if ctx.policies.get("allow_internet_without_admin", False):
            return True, "Internet allowed by policy"
        return False, "Blocked: internet access requires administrator approval"

    if action == "modify_environment":
        if ctx.policies.get("allow_environment_modification", False):
            return True, "Environment changes allowed by policy"
        return False, "Blocked: environment modification is not permitted"

    if action == "release":
        if ctx.policies.get("allow_release_without_admin", False):
            return True, "Release allowed by policy"
        return False, "Blocked: release requires administrator approval"

    return True, "Allowed"