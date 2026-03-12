from pathlib import Path
import tempfile

from mas_android_adk import make_context
from mas_autonomy import pending_admin_requests, record_admin_response, request_admin_approval


def test_admin_request_and_response_cycle():
    with tempfile.TemporaryDirectory() as tmp:
        ctx = make_context(
            project_root=tmp,
            settings_override={
                "runtime": {"dry_run": True, "verbose": False},
            },
        )

        request = request_admin_approval(
            ctx,
            request_type="request_release_decision",
            payload={"reason": "Need approval for release"},
        )
        assert request["status"] == "pending"
        assert request["requires_human"] is True

        pending = pending_admin_requests(ctx)
        assert len(pending) == 1
        request_id = pending[0]["request_id"]

        response = record_admin_response(ctx, request_id=request_id, approved=True, note="approved in test")
        assert response["approved"] is True

        pending_after = pending_admin_requests(ctx)
        assert pending_after == []

        resolved = request_admin_approval(
            ctx,
            request_type="request_release_decision",
            payload={"reason": "Need approval for release"},
        )
        assert resolved["status"] == "resolved"
        assert resolved["approved"] is True