# Share Note Server

FastAPI server for receiving and serving shared Obsidian notes.

## Setup

```bash
pip install fastapi uvicorn markdown2 python-multipart
python3 -m uvicorn main:app --host 127.0.0.1 --port 9100
```

## Endpoints

- `GET /` — list all shared notes
- `POST /api/share` — upload a note (markdown + files)
- `GET /note/{id}` — view a shared note
- `GET /plugin` — plugin download page
- `DELETE /api/note/{id}` — delete a note

## Reverse Proxy

Recommended: Caddy with automatic HTTPS.

```Caddyfile
share.example.com {
    reverse_proxy 127.0.0.1:9100
}
```
