import os
import asyncio
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

MAX_API = "https://platform-api2.max.ru"
MAX_TOKEN = os.environ["MAX_TOKEN"]
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]

app = FastAPI(title="MAX Image Bot")

HEADERS = {"Authorization": MAX_TOKEN}

async def max_send_message(chat_id: int, text: str, attachments=None):
    payload = {"text": text}
    if attachments:
        payload["attachments"] = attachments
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{MAX_API}/messages",
            params={"chat_id": chat_id},
            headers=HEADERS,
            json=payload,
        )
        r.raise_for_status()
        return r.json()

async def commons_search(query: str, limit: int = 4):
    """Search Wikimedia Commons files and return thumbnail URLs."""
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrlimit": str(min(limit, 10)),
        "gsrsearch": query,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": "1200",
    }
    headers = {"User-Agent": "MAX-Image-Bot/1.0"}
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        r = await client.get(
            "https://commons.wikimedia.org/w/api.php",
            params=params,
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()

    result = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        mime = info.get("mime", "")
        if url and mime.startswith("image/"):
            result.append({
                "title": page.get("title", ""),
                "url": url,
                "source": f"https://commons.wikimedia.org/wiki/{page.get('title','').replace(' ', '_')}",
            })
    return result

async def max_upload_image(image_bytes: bytes, filename: str):
    # Step 1: request an upload URL/token.
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{MAX_API}/uploads",
            params={"type": "image"},
            headers=HEADERS,
        )
        r.raise_for_status()
        upload = r.json()

        # Step 2: upload the actual file to the returned URL.
        files = {"data": (filename, image_bytes, "image/jpeg")}
        r2 = await client.post(upload["url"], files=files, timeout=60)
        r2.raise_for_status()

    # MAX returns a token for use in POST /messages.
    return r2.json().get("token") or upload.get("token")

async def send_image(chat_id: int, image: dict, index: int):
    headers = {"User-Agent": "MAX-Image-Bot/1.0"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(image["url"], headers=headers)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "image/jpeg")
        if not content_type.startswith("image/"):
            raise ValueError("Search result is not an image")
        data = r.content

    token = await max_upload_image(data, f"result_{index}.jpg")
    attachment = {
        "type": "image",
        "payload": {"token": token},
    }
    await max_send_message(
        chat_id,
        f"🖼️ Результат {index}\nИсточник: {image['source']}",
        [attachment],
    )

async def handle_message(update: dict[str, Any]):
    # Current MAX event structure: message_created -> message -> body -> text.
    message = update.get("message") or {}
    body = message.get("body") or {}
    text = (body.get("text") or "").strip()

    recipient = message.get("recipient") or {}
    chat_id = recipient.get("chat_id") or recipient.get("user_id")
    if not chat_id or not text:
        return

    if text.lower() in {"/start", "старт", "начать"}:
        await max_send_message(
            chat_id,
            "👋 Привет! Напиши, какую картинку найти.\n\n"
            "Например:\n"
            "• мем про понедельник\n"
            "• православная церковь\n"
            "• кот в очках\n"
            "• горы и озеро",
        )
        return

    await max_send_message(chat_id, f"🔎 Ищу картинки по запросу:\n«{text}»")

    try:
        images = await commons_search(text, 4)
        if not images:
            await max_send_message(
                chat_id,
                "😔 Ничего подходящего не нашёл. Попробуй сформулировать запрос иначе."
            )
            return

        for i, image in enumerate(images, 1):
            try:
                await send_image(chat_id, image, i)
            except Exception:
                # One bad source should not stop the remaining results.
                continue

        await max_send_message(
            chat_id,
            "🔄 Готово. Напиши новый запрос, чтобы найти другие картинки."
        )
    except Exception as exc:
        print("ERROR:", repr(exc))
        await max_send_message(
            chat_id,
            "⚠️ Не удалось выполнить поиск. Попробуй ещё раз через несколько секунд."
        )

@app.get("/")
async def health():
    return {"ok": True, "service": "max-image-bot"}

@app.post("/webhook")
async def webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
):
    if WEBHOOK_SECRET and x_max_bot_api_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    update = await request.json()

    # Always acknowledge quickly. MAX requires HTTP 200 within 30 seconds.
    asyncio.create_task(process_update(update))
    return {"ok": True}

async def process_update(update: dict[str, Any]):
    event = update.get("update_type") or update.get("type")
    if event == "message_created":
        await handle_message(update)
    elif event == "bot_started":
        # bot_started may use a different field layout; keep onboarding simple.
        message = update.get("message") or {}
        recipient = message.get("recipient") or {}
        chat_id = recipient.get("chat_id") or recipient.get("user_id")
        if chat_id:
            await max_send_message(
                chat_id,
                "👋 Привет! Я ищу картинки по описанию. Просто напиши запрос."
            )
