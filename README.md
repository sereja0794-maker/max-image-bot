# MAX — «Картинка по запросу»

Первая версия бота:
1. получает сообщение из MAX через Webhook;
2. ищет изображения в Wikimedia Commons;
3. скачивает миниатюры;
4. загружает изображения в MAX;
5. отправляет найденные изображения пользователю.

## Важно

Токен MAX нельзя публиковать или коммитить в Git. Храните его в переменной окружения `MAX_TOKEN`.

Актуальный API MAX использует домен `https://platform-api2.max.ru` и заголовок `Authorization`.

## Запуск локально

Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export MAX_TOKEN="..."
export WEBHOOK_SECRET="some-random-secret"

uvicorn main:app --host 0.0.0.0 --port 8000
```

Локальный сервер нельзя напрямую указать MAX как Webhook, потому что production Webhook должен быть доступен по HTTPS на порту 443.

## Production

Нужен сервер/хостинг с:
- публичным HTTPS-доменом;
- TLS-сертификатом от доверенного центра сертификации;
- возможностью запустить FastAPI/uvicorn.

Например:

```text
https://example.com/webhook
```

После запуска:

```bash
export MAX_TOKEN="..."
export WEBHOOK_URL="https://example.com/webhook"
export WEBHOOK_SECRET="some-random-secret"

python subscribe.py
```

## Что тестировать

В MAX напишите боту:

```text
кот
```

или:

```text
православная церковь
```

или:

```text
мем про понедельник
```

### Следующий этап

Wikimedia Commons — это только первый источник. Для мемов и более широкого поиска позже лучше подключить отдельный поисковый провайдер изображений, а затем добавить ИИ-генерацию, кнопки «Ещё» и фильтрацию контента.
