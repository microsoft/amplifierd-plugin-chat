from __future__ import annotations

from fastapi import APIRouter


def create_router(state: object) -> APIRouter:
    """Plugin entry point. Called by amplifierd plugin discovery."""
    from chat_plugin.config import ChatPluginSettings
    from chat_plugin.pin_storage import PinStorage
    from chat_plugin.routes import create_pin_routes, create_static_routes

    settings = ChatPluginSettings()
    settings.home_dir.mkdir(parents=True, exist_ok=True)
    pin_storage = PinStorage(settings.home_dir / "pinned-sessions.json")

    router = APIRouter()

    @router.get("/chat/health", tags=["chat"])
    async def chat_health():
        return {"status": "ok", "plugin": "chat"}

    router.include_router(create_pin_routes(pin_storage))
    router.include_router(create_static_routes())
    return router
