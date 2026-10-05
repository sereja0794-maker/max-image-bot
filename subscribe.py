import os
import sys
import httpx

MAX_API = "https://platform-api2.max.ru"
token = os.environ["MAX_TOKEN"]
webhook_url = os.environ["WEBHOOK_URL"]
secret = os.environ["WEBHOOK_SECRET"]

payload = {
    "url": webhook_url,
    "update_types": ["message_created", "bot_started"],
    "secret": secret,
}

r = httpx.post(
    f"{MAX_API}/subscriptions",
    headers={"Authorization": token},
    json=payload,
    timeout=30,
)
print(r.status_code)
print(r.text)
r.raise_for_status()
