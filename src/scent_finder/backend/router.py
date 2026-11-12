import openai
from fastapi import HTTPException, Request

from ..fragrance import agent, tools
from .core import create_router
from .models import (ChatIn, ChatOut, CollectionOut, Fragrance, ImportIn, ImportPreviewOut, ItemUpdateIn, MeOut,
                     SaveIn, SaveOut, ScentDnaOut, VersionOut)

MAX_MESSAGE_CHARS = 1000

router = create_router()


@router.get("/version", response_model=VersionOut, operation_id="version")
async def version():
    return VersionOut.from_metadata()


@router.get("/collection", response_model=CollectionOut, operation_id="getCollection")
def get_collection(request: Request, status: str | None = None):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    return tools.get_my_collection(status)


@router.get("/dna", response_model=ScentDnaOut | None, operation_id="getScentDna")
def get_dna(request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    dna = tools.get_scent_dna()
    return None if "error" in dna else dna


@router.get("/fragrances/lookup", response_model=list[Fragrance], operation_id="lookupFragrances")
def lookup(q: str, request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    return tools.lookup(q)


@router.post("/collection/preview", response_model=ImportPreviewOut, operation_id="previewImport")
def preview_import(body: ImportIn, request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    res = tools.add_to_collection(body.text, status=body.status, confirm=False)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return {**res, "status": body.status}


@router.post("/collection/save", response_model=SaveOut, operation_id="saveToCollection")
def save(body: SaveIn, request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    res = tools.save_to_collection(body.fragrance_ids, body.status, body.rating)
    if "error" in res:
        raise HTTPException(400, res["error"])
    return res


@router.patch("/collection/{fragrance_id}", operation_id="updateCollectionItem")
def update_item(fragrance_id: int, body: ItemUpdateIn, request: Request) -> dict:
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    if body.rating is not None and not 1 <= body.rating <= 5:
        raise HTTPException(400, "rating must be 1-5")
    if body.status is not None and body.status not in ("owned", "sampled", "wishlist"):
        raise HTTPException(400, "status must be owned, sampled or wishlist")
    res = tools.update_collection_item(fragrance_id, body.status, body.rating)
    if "error" in res:
        raise HTTPException(404, res["error"])
    return res


@router.delete("/collection/{fragrance_id}", operation_id="removeFromCollection")
def remove_item(fragrance_id: int, request: Request) -> dict:
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    return tools.remove_from_collection(fragrance_id)


@router.post("/chat", response_model=ChatOut, operation_id="chat")
def chat(body: ChatIn, request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    if not body.messages or len(body.messages[-1].content) > MAX_MESSAGE_CHARS:
        raise HTTPException(400, f"Keep questions under {MAX_MESSAGE_CHARS} characters.")
    allowed, remaining = tools.take_message_quota()
    if not allowed:
        raise HTTPException(429, f"You've used today's {tools.DAILY_MESSAGE_LIMIT} guide messages. Come back tomorrow.")
    try:
        return {**agent.chat([m.model_dump() for m in body.messages]), "remaining_today": remaining}
    except openai.NotFoundError:
        raise HTTPException(503, "The guide's model access is still being set up for this app. Try again in a minute.")
    except openai.APIError as e:
        raise HTTPException(502, f"The model service returned an error ({type(e).__name__}). Try again.")


@router.get("/me", response_model=MeOut, operation_id="getMe")
def get_me(request: Request):
    tools.set_user(request.headers.get("X-Forwarded-Email"))
    shelf = tools.get_my_collection()
    by_status = {st: sum(1 for i in shelf["items"] if i.get("my_status") == st) for st in ("owned", "wishlist", "sampled")}
    email = request.headers.get("X-Forwarded-Email") or ""
    name = request.headers.get("X-Forwarded-Preferred-Username") or email.split("@")[0] or None
    return {"display_name": name, "shelf_count": shelf["count"], "by_status": by_status,
            "daily_limit": tools.DAILY_MESSAGE_LIMIT}
