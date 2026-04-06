from __future__ import annotations

from typing import Any


async def run_post_workflow(account_id: str, content_config: dict[str, Any]) -> dict[str, Any]:
    """
    Orchestrate a full post workflow:
    1. Generate content via AI pipeline
    2. Generate/fetch media if needed
    3. Schedule the post task via Celery
    """
    # Placeholder — full implementation in Phase 3
    return {"status": "scheduled"}
