# Share Note (Self-Hosted) 🔗

An Obsidian plugin that shares your notes to a **self-hosted server** with one click. Generates a link you can send to anyone.

## Features

- 📤 One-click sharing from Obsidian
- 🖼️ Automatically uploads embedded images (`![[image.jpg]]` and `![](path)`)
- 📋 Link copied to clipboard instantly
- 🔒 Self-hosted — your data stays on your server
- 🌙 Beautiful dark theme with image lightbox

## Installation

### Option 1: Manual
1. Download [main.js](releases/latest/download/main.js), [manifest.json](releases/latest/download/manifest.json), and [styles.css](releases/latest/download/styles.css)
2. Create folder `.obsidian/plugins/share-note-selfhosted/` in your vault
3. Place all 3 files inside
4. Enable in Obsidian: Settings → Community plugins → Share Note (Self-Hosted)

### Option 2: BRAT
1. Install [BRAT](https://github.com/TfTHacker/obsidian42-brat)
2. BRAT settings → Add Beta plugin → paste this repo URL
3. Enable the plugin

## Server Setup

The plugin requires a backend server. See [server/](server/) for the FastAPI-based server.

### Quick start

```bash
pip install fastapi uvicorn markdown2 python-multipart
python3 -m uvicorn server.main:app --host 127.0.0.1 --port 9100
```

Put it behind a reverse proxy (Caddy, nginx) with HTTPS.

## Configuration

In plugin settings, set your server URL:

```
https://share.yourdomain.com
```

## Usage

- Open any Markdown note
- Click the **share** icon in the ribbon, or run `Share Note: Share current note` from the command palette
- The link is copied to your clipboard!

## License

MIT
