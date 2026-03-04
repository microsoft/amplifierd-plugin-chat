from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Response

from chat_plugin.pin_storage import PinStorage

STATIC_DIR = Path(__file__).parent / "static"


def create_pin_routes(pin_storage: PinStorage) -> APIRouter:
    router = APIRouter(prefix="/chat", tags=["chat-pins"])

    @router.get("/pins")
    async def list_pins():
        return {"pinned": sorted(pin_storage.list_pins())}

    @router.post("/pins/{session_id}")
    async def pin_session(session_id: str):
        pin_storage.add(session_id)
        return {"pinned": True, "session_id": session_id}

    @router.delete("/pins/{session_id}")
    async def unpin_session(session_id: str):
        pin_storage.remove(session_id)
        return {"pinned": False, "session_id": session_id}

    return router


def create_static_routes() -> APIRouter:
    router = APIRouter(tags=["chat-static"])

    @router.get("/chat/")
    async def serve_spa():
        html = (STATIC_DIR / "index.html").read_text()
        return Response(content=html, media_type="text/html")

    @router.get("/chat/vendor.js")
    async def serve_vendor():
        js = (STATIC_DIR / "vendor.js").read_text()
        return Response(content=js, media_type="application/javascript")

    return router
