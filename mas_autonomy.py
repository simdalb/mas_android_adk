from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List
import json
import time


def _admin_requests_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/admin/requests")


def _admin_responses_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/admin/responses")


def _snapshots_dir(ctx) -> Path:
    return ctx.resolve_path("./artifacts/snapshots")


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
        "Backlog state is written to:",
        "- `artifacts/backlog.json`",
        "",
        "Snapshots used for rollback are written to:",
        "- `artifacts/snapshots/`",
        "",
    ]
    return "\n".join(lines)


def _executor_registry() -> Dict[str, Any]:
    return {
        "create_media_link_use_cases": lambda: {
            "files": {
                "app/use_cases/__init__.py": _use_case_init_py(),
                "app/use_cases/media_links.py": _media_links_use_case_py(),
            },
            "summary": "Created framework-agnostic media link use-case layer.",
        },
        "create_media_link_use_case_tests": lambda: {
            "files": {
                "tests/test_media_link_use_cases.py": _use_case_tests_py(),
            },
            "summary": "Created use-case tests.",
        },
        "create_autonomy_runbook": lambda: {
            "files": {
                "docs/AUTONOMOUS_MODE.md": _autonomy_runbook_md(),
            },
            "summary": "Created autonomous mode runbook.",
        },
    }


def execute_work_item(ctx, item) -> Dict[str, Any]:
    executor_name = item.metadata.get("executor")
    registry = _executor_registry()
    executor = registry.get(executor_name)

    if executor is None:
        return {
            "success": False,
            "summary": f"No executor found for backlog item: {executor_name}",
            "changed_files": [],
        }

    plan = executor()
    files: Dict[str, str] = plan.get("files", {})
    summary = plan.get("summary", "")

    snapshot_manifest = _snapshot_files(ctx, item.item_id, files, item.attempts)

    changed_files: List[str] = []
    if not ctx.dry_run:
        for rel_path, content in files.items():
            target = ctx.resolve_path(rel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            changed_files.append(str(target))
    else:
        changed_files = [str(ctx.resolve_path(rel_path)) for rel_path in files]

    return {
        "success": True,
        "summary": summary,
        "changed_files": changed_files,
        "snapshot_manifest": snapshot_manifest,
        "executor": executor_name,
    }