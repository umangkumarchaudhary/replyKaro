# -*- coding: utf-8 -*-

"""

    Module :mod:`web.application.routes`

    The FastAPI app: wires every API router together.

        uv run uvicorn web.application.routes:app --reload

"""

# ----------- START: Native Imports ---------- #
from contextlib import asynccontextmanager
from pathlib import Path
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
from fastapi import FastAPI
from fastapi.responses import FileResponse
# ----------- END: Third Party Imports ---------- #

# ----------- START: In-App Imports ---------- #
from core.db.session import init_db
from core.utils.config import get_settings
from web.application.api.app import business, chat, conversations, leads, usage
# ----------- END: In-App Imports ---------- #

__all__ = ["app"]

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="ReplyKaro", version="0.1.0", lifespan=lifespan)

app.include_router(business.setup_router)  # /api/businesses (before /api/{slug} routes)
for module in (business, chat, conversations, leads, usage):
    app.include_router(module.router)


@app.get("/health", tags=["system"])
def health():
    settings = get_settings()
    return {"ok": True, "chat_model": settings.chat_model, "api_key_set": bool(settings.anthropic_api_key)}


@app.get("/chat/{slug}", include_in_schema=False)
def chat_page(slug: str):
    """Test chat UI. Phase 2 turns this into an embeddable website widget."""
    return FileResponse(_STATIC / "chat.html")
