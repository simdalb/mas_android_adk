from __future__ import annotations

from pathlib import Path
import json
import time


def _append_log(ctx, event_name: str) -> None:
    log_dir = Path(ctx.project_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": time.time(),
        "event": event_name,
    }
    with (log_dir / "workflow_events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def before_bootstrap(ctx) -> None:
    _append_log(ctx, "before_bootstrap")


def after_bootstrap(ctx) -> None:
    _append_log(ctx, "after_bootstrap")


def before_delivery_iteration(ctx) -> None:
    _append_log(ctx, "before_delivery_iteration")


def after_delivery_iteration(ctx) -> None:
    _append_log(ctx, "after_delivery_iteration")


def before_release(ctx) -> None:
    _append_log(ctx, "before_release")


def after_release(ctx) -> None:
    _append_log(ctx, "after_release")


WORKFLOW_HOOKS = {
    "before_bootstrap": before_bootstrap,
    "after_bootstrap": after_bootstrap,
    "before_delivery_iteration": before_delivery_iteration,
    "after_delivery_iteration": after_delivery_iteration,
    "before_release": before_release,
    "after_release": after_release,
}