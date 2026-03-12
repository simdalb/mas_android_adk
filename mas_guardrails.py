from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple


def _resolve_under_project(project_root: Path, path_value: str) -> Path:
    target = Path(path_value)
    if not target.is_absolute():
        target = project_root / target
    return target.resolve()


def _is_within(root: Path, target: Path) -> bool:
    root = root.resolve()
    target = target.resolve()
    return root == target or root in target.parents


def guardrail_check(action: str, ctx, payload: Dict) -> Tuple[bool, str]:
    project_root = Path(ctx.project_root).resolve()

    if action in {"write_file", "delete_file", "move_file", "mkdir", "read_file"}:
        path_value = payload.get("path")
        if not path_value:
            return False, "Blocked: missing path for filesystem action"
        target = _resolve_under_project(project_root, path_value)
        if not _is_within(project_root, target):
            return False, f"Blocked: path outside project root: {target}"

    if action == "subprocess":
        cwd = payload.get("cwd", str(project_root))
        cwd_path = _resolve_under_project(project_root, str(cwd))
        if not _is_within(project_root, cwd_path):
            return False, f"Blocked: subprocess cwd outside project root: {cwd_path}"

    if action == "internet_access":
        if ctx.policies.get("allow_internet_without_admin", False):
            return True, "Allowed: internet access enabled by policy"
        return False, "Blocked: internet access requires administrator approval"

    if action == "modify_environment":
        if ctx.policies.get("allow_environment_modification", False):
            return True, "Allowed: environment modification enabled by policy"
        return False, "Blocked: environment modification is not permitted"

    if action == "release":
        if ctx.policies.get("allow_release_without_admin", False):
            return True, "Allowed: release enabled by policy"
        return False, "Blocked: release requires administrator approval"

    return True, "Allowed"