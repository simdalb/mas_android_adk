from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import py_compile
import re
import time


def _admin_requests_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/admin/requests")


def _admin_responses_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/admin/responses")


def _snapshots_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/snapshots")


def _plans_dir(ctx) -> Path:
    rel = ctx.get_setting("orchestration", "plan_artifacts_dir", default="./artifacts/plans")
    return ctx.resolve_path(rel)


def _stable_request_id(request_type: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps({"request_type": request_type, "payload": payload}, sort_keys=True, default=str)
    return sha1(raw.encode("utf-8")).hexdigest()[:16]


def request_admin_approval(ctx, request_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    request_id = _stable_request_id(request_type, payload)
    req_dir = _admin_requests_dir(ctx)
    res_dir = _admin_responses_dir(ctx)
    req_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    request_path = req_dir / f"{request_id}.json"
    response_path = res_dir / f"{request_id}.json"

    request_record = {
        "request_id": request_id,
        "request_type": request_type,
        "payload": payload,
        "status": "pending",
        "created_at": time.time(),
    }

    if not request_path.exists():
        request_path.write_text(json.dumps(request_record, indent=2, ensure_ascii=False), encoding="utf-8")

    if response_path.exists():
        response = json.loads(response_path.read_text(encoding="utf-8"))
        return {
            "request_id": request_id,
            "request_type": request_type,
            "status": "resolved",
            "approved": bool(response.get("approved", False)),
            "response": response,
            "requires_human": False,
        }

    return {
        "request_id": request_id,
        "request_type": request_type,
        "status": "pending",
        "approved": False,
        "requires_human": True,
        "request_file": str(request_path),
        "response_file": str(response_path),
    }


def record_admin_response(ctx, request_id: str, approved: bool, note: str = "") -> Dict[str, Any]:
    res_dir = _admin_responses_dir(ctx)
    res_dir.mkdir(parents=True, exist_ok=True)
    response_path = res_dir / f"{request_id}.json"
    payload = {
        "request_id": request_id,
        "approved": bool(approved),
        "note": note,
        "resolved_at": time.time(),
    }
    response_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def pending_admin_requests(ctx) -> List[Dict[str, Any]]:
    req_dir = _admin_requests_dir(ctx)
    res_dir = _admin_responses_dir(ctx)
    req_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)

    items: List[Dict[str, Any]] = []
    for request_file in sorted(req_dir.glob("*.json")):
        response_file = res_dir / request_file.name
        if response_file.exists():
            continue
        items.append(json.loads(request_file.read_text(encoding="utf-8")))
    return items


def _snapshot_files(ctx, item_id: str, files: Dict[str, str], attempt: int) -> str:
    root = _snapshots_dir(ctx) / item_id / f"attempt_{attempt:02d}"
    root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "item_id": item_id,
        "attempt": attempt,
        "files": [],
        "created_at": time.time(),
    }

    for rel_path in files:
        target = ctx.resolve_path(rel_path)
        backup_path = root / rel_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            backup_path.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            original_exists = True
        else:
            original_exists = False

        manifest["files"].append(
            {
                "path": rel_path,
                "backup_path": str(backup_path),
                "original_exists": original_exists,
            }
        )

    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(manifest_path)


def restore_snapshot(ctx, manifest_path: str) -> Dict[str, Any]:
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        return {"restored": False, "reason": "manifest not found"}

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    restored_files: List[str] = []

    for item in manifest.get("files", []):
        target = ctx.resolve_path(item["path"])
        backup_path = Path(item["backup_path"])

        if item.get("original_exists", False) and backup_path.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
            restored_files.append(str(target))
        else:
            if target.exists():
                target.unlink()
                restored_files.append(str(target))

    return {"restored": True, "files": restored_files}


def _write_plan_artifact(
    ctx,
    item_id: str,
    attempt: int,
    files: Dict[str, str],
    summary: str,
    executor_name: str,
    plan_type: str = "executor",
) -> str:
    plan_dir = _plans_dir(ctx) / item_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / f"attempt_{attempt:02d}.json"
    payload = {
        "item_id": item_id,
        "attempt": attempt,
        "executor": executor_name,
        "plan_type": plan_type,
        "summary": summary,
        "files": sorted(files.keys()),
        "created_at": time.time(),
    }
    plan_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(plan_path)


def _guarded_write(ctx, rel_path: str, content: str) -> None:
    from mas_guardrails import guardrail_check

    ok, reason = guardrail_check("write_file", ctx, {"path": rel_path})
    if not ok:
        raise RuntimeError(reason)

    target = ctx.resolve_path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    if target.suffix == ".py" and ctx.policies.get("syntax_check_python_after_write", True):
        py_compile.compile(str(target), doraise=True)


def _replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Anchor text not found: {old[:80]}")
    return text.replace(old, new, 1)


def _apply_operations_to_file(original: str, operations: List[Dict[str, Any]]) -> str:
    updated = original
    for op in operations:
        mode = op.get("mode")
        if mode == "replace_once":
            updated = _replace_once(updated, op["old"], op["new"])
        elif mode == "append":
            suffix = op.get("text", "")
            if updated and not updated.endswith("\n"):
                updated += "\n"
            updated += suffix
        elif mode == "prepend":
            prefix = op.get("text", "")
            updated = prefix + updated
        else:
            raise ValueError(f"Unsupported operation mode: {mode}")
    return updated


def _apply_file_plan(
    ctx,
    item_id: str,
    attempt: int,
    files: Dict[str, str],
    summary: str,
    executor_name: str,
    plan_type: str = "executor",
) -> Dict[str, Any]:
    max_files = int(ctx.policies.get("max_changed_files_per_iteration", 8))
    if len(files) > max_files:
        return {
            "success": False,
            "summary": f"Refused to change {len(files)} files; limit is {max_files}",
            "changed_files": [],
        }

    plan_artifact = _write_plan_artifact(ctx, item_id, attempt, files, summary, executor_name, plan_type=plan_type)
    snapshot_manifest = _snapshot_files(ctx, item_id, files, attempt)
    changed_files: List[str] = []

    if not ctx.dry_run:
        for rel_path, content in files.items():
            _guarded_write(ctx, rel_path, content)
            changed_files.append(str(ctx.resolve_path(rel_path)))
    else:
        changed_files = [str(ctx.resolve_path(rel_path)) for rel_path in files]

    return {
        "success": True,
        "changed_files": changed_files,
        "snapshot_manifest": snapshot_manifest,
        "plan_artifact": plan_artifact,
    }


def _extract_json_from_text(text: str) -> Dict[str, Any]:
    stripped = text.strip()

    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    if stripped.startswith("{") and stripped.endswith("}"):
        return json.loads(stripped)

    first = stripped.find("{")
    last = stripped.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(stripped[first:last + 1])

    raise ValueError("No JSON object found in model output")


def _normalize_patch_plan(raw: Dict[str, Any]) -> Dict[str, Any]:
    summary = str(raw.get("summary", "Generated patch plan"))
    edits = raw.get("edits", [])
    if not isinstance(edits, list) or not edits:
        raise ValueError("Patch plan must contain a non-empty 'edits' list")

    normalized = []
    for edit in edits:
        if not isinstance(edit, dict):
            raise ValueError("Each edit must be an object")
        path = str(edit.get("path", "")).strip()
        if not path:
            raise ValueError("Each edit must include a path")
        operations = edit.get("operations", [])
        if not isinstance(operations, list) or not operations:
            raise ValueError("Each edit must include a non-empty operations list")
        normalized.append({"path": path, "operations": operations})

    return {"summary": summary, "edits": normalized}


def _read_target_context(ctx, target_files: List[str]) -> Dict[str, str]:
    contexts: Dict[str, str] = {}
    for rel_path in target_files:
        path = ctx.resolve_path(rel_path)
        if path.exists() and path.is_file():
            contexts[rel_path] = path.read_text(encoding="utf-8")
    return contexts


def _collect_editable_files(ctx, limit: int = 12) -> List[str]:
    editable_roots = list(ctx.policies.get("editable_roots", []))
    collected: List[str] = []

    for root_name in editable_roots:
        root = ctx.resolve_path(root_name)
        if not root.exists() or not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".py", ".md"}:
                continue
            rel = str(path.relative_to(ctx.resolve_path("."))).replace("\\", "/")
            collected.append(rel)
            if len(collected) >= limit:
                return collected
    return collected


def _build_llm_patch_prompt(ctx, item, target_files: List[str], file_contexts: Dict[str, str]) -> str:
    context_sections = []
    for rel_path in target_files:
        body = file_contexts.get(rel_path, "")
        if body:
            context_sections.append(f"FILE: {rel_path}\n---\n{body}\n---")
        else:
            context_sections.append(f"FILE: {rel_path}\n---\n<missing>\n---")

    context_blob = "\n\n".join(context_sections)
    failure_context = str(item.metadata.get("last_failure_summary", "")).strip()

    prompt = (
        f"Backlog item title: {item.title}\n"
        f"Description: {item.description}\n"
        "Acceptance criteria:\n- " + "\n- ".join(item.acceptance_criteria) + "\n\n"
        "You must return ONLY valid JSON. No prose. No markdown fences.\n"
        "JSON schema:\n"
        "{\n"
        '  "summary": "short summary",\n'
        '  "edits": [\n'
        "    {\n"
        '      "path": "relative/path.py",\n'
        '      "operations": [\n'
        '        {"mode": "replace_once", "old": "exact old text", "new": "exact new text"},\n'
        '        {"mode": "append", "text": "text to append"}\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Only modify the provided target files.\n"
        "- Prefer small precise edits.\n"
        "- Do not mention any file outside the provided target files.\n"
        "- Use exact anchors for replace_once.\n"
    )

    if failure_context:
        prompt += "\nRecent failure context to repair:\n" + failure_context + "\n"

    prompt += (
        "\nTarget files:\n- " + "\n- ".join(target_files) + "\n\n"
        "Current file contents:\n"
        f"{context_blob}\n"
    )
    return prompt


def _build_llm_patch_plan(ctx, item, agents: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not agents or "android_coder" not in agents:
        return {"success": False, "summary": "No android_coder agent available for generic patching"}

    target_files = list(item.metadata.get("patch_target_hint", []) or [])
    if not target_files:
        target_files = _collect_editable_files(ctx, limit=8)
    if not target_files:
        return {"success": False, "summary": "No editable target files available"}

    file_contexts = _read_target_context(ctx, target_files)
    prompt = _build_llm_patch_prompt(ctx, item, target_files, file_contexts)

    coder_result = agents["android_coder"].execute(ctx, user_prompt=prompt, response_format="json")
    response_text = str(coder_result.get("response", ""))

    try:
        raw = coder_result.get("response_json") if isinstance(coder_result.get("response_json"), dict) else _extract_json_from_text(response_text)
        plan = _normalize_patch_plan(raw)
    except Exception as exc:
        return {
            "success": False,
            "summary": f"Model output was not a valid patch plan: {exc}",
            "model_output": response_text,
        }

    files_to_write: Dict[str, str] = {}
    for edit in plan["edits"]:
        rel_path = edit["path"]
        if rel_path not in target_files:
            return {
                "success": False,
                "summary": f"Patch plan attempted to modify a non-target file: {rel_path}",
                "model_output": response_text,
            }

        original = file_contexts.get(rel_path, "")
        if original == "" and not ctx.resolve_path(rel_path).exists():
            original = ""

        try:
            updated = _apply_operations_to_file(original, edit["operations"])
        except Exception as exc:
            return {
                "success": False,
                "summary": f"Failed to apply patch operations for {rel_path}: {exc}",
                "model_output": response_text,
            }

        files_to_write[rel_path] = updated

    applied = _apply_file_plan(
        ctx,
        item.item_id,
        item.attempts,
        files_to_write,
        summary=plan["summary"],
        executor_name="llm_patch",
        plan_type="llm_patch",
    )
    applied["executor"] = "llm_patch"
    applied["summary"] = plan["summary"]
    applied["model_output"] = response_text
    return applied


def _use_case_init_py() -> str:
    return """__all__ = [
    "media_links",
]
"""


def _media_links_use_case_py() -> str:
    return """from __future__ import annotations

from typing import List, Optional

from app.domain.models import MediaLink
from app.services.storage import LocalMediaRepository


class MediaLinkUseCases:
    def __init__(self, repository: Optional[LocalMediaRepository] = None) -> None:
        self.repository = repository or LocalMediaRepository()

    def list_links(self) -> List[MediaLink]:
        return self.repository.load_all()

    def create_link(
        self,
        *,
        title: str,
        url: str,
        tags: List[str] | None = None,
        is_local: bool = False,
        description: str = "",
    ) -> MediaLink:
        if not title.strip():
            raise ValueError("title is required")
        if not url.strip():
            raise ValueError("url is required")

        link = MediaLink(
            title=title.strip(),
            url=url.strip(),
            tags=list(tags or []),
            is_local=bool(is_local),
            description=description.strip(),
        )
        return self.repository.add(link)

    def update_link(self, link: MediaLink) -> MediaLink:
        if not link.title.strip():
            raise ValueError("title is required")
        if not link.url.strip():
            raise ValueError("url is required")
        return self.repository.update(link)

    def delete_link(self, link_id: str) -> bool:
        return self.repository.delete(link_id)

    def get_link(self, link_id: str) -> Optional[MediaLink]:
        return self.repository.get(link_id)

    def search_links(self, query: str) -> List[MediaLink]:
        return self.repository.search(query)
"""


def _use_case_tests_py() -> str:
    return """from pathlib import Path
import tempfile

from app.use_cases.media_links import MediaLinkUseCases
from app.services.storage import LocalMediaRepository


def test_media_link_use_cases_crud_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        repo = LocalMediaRepository(path=str(Path(tmp) / "media_links.json"))
        use_cases = MediaLinkUseCases(repository=repo)

        created = use_cases.create_link(
            title="Example item",
            url="https://example.com/watch",
            tags=["sample", "video"],
            description="demo",
        )
        assert created.link_id

        loaded = use_cases.get_link(created.link_id)
        assert loaded is not None
        assert loaded.title == "Example item"

        loaded.title = "Updated item"
        use_cases.update_link(loaded)

        results = use_cases.search_links("updated")
        assert len(results) == 1
        assert results[0].title == "Updated item"

        deleted = use_cases.delete_link(created.link_id)
        assert deleted is True
        assert use_cases.get_link(created.link_id) is None
"""


def _autonomy_runbook_md() -> str:
    lines = [
        "# Autonomous Mode Runbook",
        "",
        "## What autonomous mode currently does",
        "- loads or creates a backlog",
        "- executes one backlog item at a time",
        "- writes iteration artifacts",
        "- writes plan artifacts before edits",
        "- runs pytest",
        "- rolls back edited files if an iteration fails",
        "- pauses when administrator approval is required",
        "",
        "## Admin approval queue",
        "Requests are written to:",
        "- `artifacts/admin/requests/`",
        "",
        "Responses should be written to:",
        "- `artifacts/admin/responses/`",
        "",
        "A response file must match the request file name.",
        "",
        "You can also record a response from the CLI:",
        "",
        "    python mas_android_adk.py --approve-request REQUEST_ID --decision approved",
        "    python mas_android_adk.py --approve-request REQUEST_ID --decision rejected --note \"reason\"",
        "",
        "## Resume behavior",
        "To resume an autonomous run after a pause:",
        "1. answer any pending request",
        "2. rerun:",
        "   `python mas_android_adk.py --autonomous`",
        "",
        "## Iteration artifacts",
        "Iteration reports are written to:",
        "- `artifacts/iterations/`",
        "",
        "Planned edit artifacts are written to:",
        "- `artifacts/plans/`",
        "",
        "Backlog state is written to:",
        "- `artifacts/backlog.json`",
        "",
        "Snapshots used for rollback are written to:",
        "- `artifacts/snapshots/`",
        "",
    ]
    return "\n".join(lines)


def _kivy_use_case_import_plan(ctx) -> Dict[str, Any]:
    path = "app_frameworks/kivy_adapter.py"
    original = ctx.resolve_path(path).read_text(encoding="utf-8")
    updated = _apply_operations_to_file(
        original,
        [
            {
                "mode": "replace_once",
                "old": "from app.services.storage import LocalMediaRepository\n",
                "new": (
                    "from app.services.storage import LocalMediaRepository\n"
                    "from app.use_cases.media_links import MediaLinkUseCases\n"
                ),
            },
            {
                "mode": "replace_once",
                "old": "        repo = LocalMediaRepository()\n",
                "new": (
                    "        repo = LocalMediaRepository()\n"
                    "        use_cases = MediaLinkUseCases(repository=repo)\n"
                ),
            },
            {
                "mode": "replace_once",
                "old": "                self.repo = repo\n",
                "new": (
                    "                self.repo = repo\n"
                    "                self.use_cases = use_cases\n"
                ),
            },
            {
                "mode": "replace_once",
                "old": "                return self.repo.search(self.search_query)\n",
                "new": "                return self.use_cases.search_links(self.search_query)\n",
            },
            {
                "mode": "replace_once",
                "old": "                    existing = self.repo.get(self.current_edit_id)\n",
                "new": "                    existing = self.use_cases.get_link(self.current_edit_id)\n",
            },
            {
                "mode": "replace_once",
                "old": "                    self.repo.update(updated)\n",
                "new": "                    self.use_cases.update_link(updated)\n",
            },
            {
                "mode": "replace_once",
                "old": "                    self.repo.add(\n                        MediaLink(\n                            title=title,\n                            url=url,\n                            tags=tags,\n                            is_local=is_local,\n                            description=description,\n                        )\n                    )\n",
                "new": (
                    "                    self.use_cases.create_link(\n"
                    "                        title=title,\n"
                    "                        url=url,\n"
                    "                        tags=tags,\n"
                    "                        is_local=is_local,\n"
                    "                        description=description,\n"
                    "                    )\n"
                ),
            },
            {
                "mode": "replace_once",
                "old": "                link = self.repo.get(link_id)\n",
                "new": "                link = self.use_cases.get_link(link_id)\n",
            },
            {
                "mode": "replace_once",
                "old": "                deleted = self.repo.delete(link_id)\n",
                "new": "                deleted = self.use_cases.delete_link(link_id)\n",
            },
        ],
    )
    return {"files": {path: updated}, "summary": "Switched Kivy adapter UI to use framework-agnostic use cases."}


def _status_command_doc(ctx) -> Dict[str, Any]:
    path = "docs/AUTONOMOUS_MODE.md"
    original = ctx.resolve_path(path).read_text(encoding="utf-8")
    addition = "\n## Status inspection\nYou can inspect saved autonomous state with:\n\n    python mas_android_adk.py --status\n"
    updated = original if "python mas_android_adk.py --status" in original else original + addition
    return {"files": {path: updated}, "summary": "Added status inspection note to autonomous runbook."}


def _android_build_readme_md() -> str:
    return """# Android Build Pipeline

This project now includes a concrete Kivy-to-Android packaging path built around
Buildozer. The MAS can generate the Android packaging files, and the repo ships
with dry-run-friendly scripts for packaging and adb smoke checks.

## Files
- `buildozer.spec` — Kivy Android packaging configuration
- `scripts/android/build_android.py` — reproducible packaging entrypoint
- `scripts/android/smoke_test_android.py` — adb-based install/launch smoke test
- `android/keystore.properties.example` — signing template for release builds

## Local debug build

    python scripts/android/build_android.py --project-root . --mode debug --dry-run

To perform a real build, install the Android toolchain and Buildozer, then rerun
without `--dry-run`.

## Local smoke test

    python scripts/android/smoke_test_android.py --project-root . --dry-run

## Expected artifacts
Debug APKs are expected under `bin/`. The build script also writes a build report
to `artifacts/android/android_build_report.json`. Smoke tests write
`artifacts/android/android_smoke_test_report.json`.
"""


def _buildozer_spec(package_name: str = "com.example.linksaver") -> str:
    domain, _, name = package_name.rpartition(".")
    domain = domain or "com.example"
    return f"""[app]
title = LinkSaver
package.name = linksaver
package.domain = {domain}
source.dir = .
source.include_exts = py,png,jpg,kv,md,json,yaml
version = 0.1.0
requirements = python3,kivy,pyyaml,python-dotenv
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 26
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET
presplash.color = #101820
icon.filename = 

[buildozer]
log_level = 2
warn_on_root = 1
"""


def _android_keystore_example() -> str:
    return """# Copy this file to android/keystore.properties and fill in real values.
KEYSTORE_PATH=/absolute/path/to/your-upload-keystore.jks
KEYSTORE_PASSWORD=change-me
KEY_ALIAS=upload
KEY_PASSWORD=change-me
"""


def _build_android_packaging_files(ctx) -> Dict[str, Any]:
    package_name = ctx.get_setting("android", "package_name", default="com.example.linksaver")
    return {
        "files": {
            "buildozer.spec": _buildozer_spec(package_name),
            "docs/ANDROID_BUILD.md": _android_build_readme_md(),
            "android/keystore.properties.example": _android_keystore_example(),
        },
        "summary": "Created Android packaging configuration, docs, and signing template.",
    }


def _executor_registry() -> Dict[str, Any]:
    return {
        "create_media_link_use_cases": lambda ctx: {
            "files": {
                "app/use_cases/__init__.py": _use_case_init_py(),
                "app/use_cases/media_links.py": _media_links_use_case_py(),
            },
            "summary": "Created framework-agnostic media link use-case layer.",
        },
        "create_media_link_use_case_tests": lambda ctx: {
            "files": {
                "tests/test_media_link_use_cases.py": _use_case_tests_py(),
            },
            "summary": "Created use-case tests.",
        },
        "create_autonomy_runbook": lambda ctx: {
            "files": {
                "docs/AUTONOMOUS_MODE.md": _autonomy_runbook_md(),
            },
            "summary": "Created autonomous mode runbook.",
        },
        "switch_kivy_to_use_cases": _kivy_use_case_import_plan,
        "document_status_command": _status_command_doc,
        "create_android_packaging_files": _build_android_packaging_files,
    }


def execute_work_item(ctx, item, agents: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    executor_name = item.metadata.get("executor")
    registry = _executor_registry()

    if executor_name == "llm_patch":
        return _build_llm_patch_plan(ctx, item, agents)

    executor = registry.get(executor_name)
    if executor is None:
        if agents:
            return _build_llm_patch_plan(ctx, item, agents)
        return {
            "success": False,
            "summary": f"No executor found for backlog item: {executor_name}",
            "changed_files": [],
        }

    try:
        plan = executor(ctx)
        files: Dict[str, str] = plan.get("files", {})
        summary = plan.get("summary", "")
        apply_result = _apply_file_plan(ctx, item.item_id, item.attempts, files, summary, executor_name, plan_type="executor")
        apply_result["summary"] = summary
        apply_result["executor"] = executor_name
        return apply_result
    except Exception as exc:
        return {
            "success": False,
            "summary": f"Executor failed: {exc}",
            "changed_files": [],
            "executor": executor_name,
        }