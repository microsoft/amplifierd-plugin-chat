from __future__ import annotations

from fastapi import APIRouter


def create_router(state: object) -> APIRouter:
    """Plugin entry point. Called by amplifierd plugin discovery."""
    router = APIRouter(tags=["chat"])

    @router.get("/chat/health")
    async def chat_health():
        return {"status": "ok", "plugin": "chat"}

    return router
