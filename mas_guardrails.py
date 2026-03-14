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


def _is_in_editable_root(project_root: Path, target: Path, editable_roots) -> bool:
    try:
        rel = target.resolve().relative_to(project_root.resolve())
    except Exception:
        return False

    if len(rel.parts) == 0:
        return False

    first = rel.parts[0]
    return first in set(editable_roots or [])


def guardrail_check(action: str, ctx, payload: Dict) -> Tuple[bool, str]:
    project_root = Path(ctx.project_root).resolve()
    editable_roots = ctx.policies.get("editable_roots", [])
    protected_filenames = set(ctx.policies.get("protected_filenames", []))

    if action in {"write_file", "delete_file", "move_file", "mkdir", "read_file"}:
        path_value = payload.get("path")
        if not path_value:
            return False, "Blocked: missing path for filesystem action"
        target = _resolve_under_project(project_root, path_value)
        if not _is_within(project_root, target):
            return False, f"Blocked: path outside project root: {target}"

        if action in {"write_file", "delete_file", "move_file"}:
            if target.name in protected_filenames:
                return False, f"Blocked: protected file cannot be modified automatically: {target.name}"

            if not _is_in_editable_root(project_root, target, editable_roots):
                return False, (
                    "Blocked: target is outside editable roots. "
                    f"Editable roots are: {', '.join(editable_roots)}"
                )

    if action == "subprocess":
        cwd = Path(payload.get("cwd", project_root))
        if not cwd.is_absolute():
            cwd = project_root / cwd
        if not _is_within(project_root, cwd):
            return False, f"Blocked: subprocess cwd outside project root: {cwd}"

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