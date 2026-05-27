"""
Share Note Server — self-hosted Obsidian note sharing.
Receives markdown + attachments from Obsidian plugin, renders as HTML.
"""

import os
import uuid
import json
import re
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Config ──────────────────────────────────────────────
BASE_DIR = Path("/srv/share-server")
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Compat: try markdown2 first (more features), fall back to markdown
try:
    import markdown2
    def render_md(text: str) -> str:
        return markdown2.markdown(text, extras=["fenced-code-blocks", "tables", "task-lists", "header-ids", "toc"])
except ImportError:
    import markdown
    def render_md(text: str) -> str:
        return markdown.markdown(text, extensions=["fenced_code", "tables", "toc"])

app = FastAPI(title="Share Note")

# ── Helpers ─────────────────────────────────────────────

def note_dir(note_id: str) -> Path:
    d = UPLOADS_DIR / note_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def generate_id() -> str:
    return uuid.uuid4().hex[:8]


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root {{
    --bg: #1e1e2e;
    --surface: #282840;
    --text: #cdd6f4;
    --text-muted: #a6adc8;
    --accent: #89b4fa;
    --border: #45475a;
    --code-bg: #313244;
    --green: #a6e3a1;
    --yellow: #f9e2af;
    --red: #f38ba8;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, 'Segoe UI', 'Inter', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    padding: 0;
  }}
  .container {{
    max-width: 820px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}
  .meta {{
    color: var(--text-muted);
    font-size: 13px;
    margin-bottom: 24px;
    display: flex;
    gap: 16px;
    align-items: center;
  }}
  .meta span {{ opacity: 0.7; }}
  h1 {{ font-size: 2em; margin: 0 0 8px; color: var(--accent); font-weight: 700; }}
  h2 {{ font-size: 1.5em; margin: 32px 0 12px; color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  h3 {{ font-size: 1.2em; margin: 24px 0 8px; color: var(--accent); }}
  h4 {{ font-size: 1.05em; margin: 20px 0 8px; color: var(--text-muted); }}
  p {{ margin: 8px 0; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  img {{
    max-width: 100%;
    border-radius: 8px;
    margin: 12px 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  }}
  .image-gallery {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
    margin: 12px 0;
  }}
  .image-gallery img {{
    width: 100%;
    cursor: pointer;
    transition: transform 0.2s;
  }}
  .image-gallery img:hover {{
    transform: scale(1.02);
  }}
  code {{
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
  }}
  pre {{
    background: var(--code-bg);
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 12px 0;
    line-height: 1.5;
  }}
  pre code {{ background: none; padding: 0; }}
  blockquote {{
    border-left: 3px solid var(--accent);
    padding: 8px 16px;
    margin: 12px 0;
    background: var(--surface);
    border-radius: 0 8px 8px 0;
    color: var(--text-muted);
  }}
  ul, ol {{ margin: 8px 0; padding-left: 24px; }}
  li {{ margin: 4px 0; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
  }}
  th, td {{
    padding: 8px 12px;
    border: 1px solid var(--border);
    text-align: left;
  }}
  th {{ background: var(--surface); font-weight: 600; }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
  strong {{ color: #fff; }}
  .task-list-item {{ list-style: none; margin-left: -20px; }}
  .task-list-item input {{ margin-right: 8px; }}

  /* Lightbox */
  .lightbox {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    z-index: 1000;
    cursor: pointer;
    justify-content: center;
    align-items: center;
  }}
  .lightbox.active {{ display: flex; }}
  .lightbox img {{
    max-width: 95vw;
    max-height: 95vh;
    border-radius: 4px;
    box-shadow: none;
  }}

  /* Footer */
  .footer {{
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 12px;
    text-align: center;
    opacity: 0.5;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="meta">
    <span>📅 {date}</span>
  </div>
  {content}
  <div class="footer">Shared via Share Note</div>
</div>

<div class="lightbox" id="lightbox" onclick="this.classList.remove('active')">
  <img id="lightbox-img" src="">
</div>

<script>
document.querySelectorAll('.image-gallery img, .container > img').forEach(img => {{
  img.addEventListener('click', () => {{
    document.getElementById('lightbox-img').src = img.src;
    document.getElementById('lightbox').classList.add('active');
  }});
}});
</script>
</body>
</html>"""


# ── API ─────────────────────────────────────────────────

@app.post("/api/share")
async def share_note(
    markdown: str = Form(...),
    title: str = Form("Untitled"),
    files: list[UploadFile] = File(default=[]),
):
    """Receive a note + attachments, render and store as HTML."""
    note_id = generate_id()
    ndir = note_dir(note_id)

    # Save files
    saved_files = {}
    for f in files:
        if not f.filename:
            continue
        safe_name = Path(f.filename).name
        dest = ndir / safe_name
        content = await f.read()
        with open(dest, "wb") as out:
            out.write(content)
        saved_files[safe_name] = True

    # Rewrite ![[image.jpg]] → <img src="/note/{id}/files/image.jpg">
    # Also handle ![[image.jpg|alt]] syntax
    def replace_embed(m):
        fname = m.group(1).split("|")[0].strip()
        alt = m.group(1).split("|")[1].strip() if "|" in m.group(1) else ""
        return f'<img src="/note/{note_id}/files/{fname}" alt="{alt}">'

    html_content = re.sub(r'!\[\[([^\]]+)\]\]', replace_embed, markdown)

    # Also handle standard markdown images: ![alt](path)
    def replace_md_img(m):
        alt = m.group(1)
        path = m.group(2)
        fname = Path(path).name
        if fname in saved_files:
            return f'<img src="/note/{note_id}/files/{fname}" alt="{alt}">'
        return m.group(0)

    html_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', replace_md_img, html_content)

    # Render markdown → HTML
    rendered = render_md(html_content)

    # Detect consecutive images and wrap in gallery
    rendered = re.sub(
        r'(<img[^>]*>\s*){2,}',
        lambda m: '<div class="image-gallery">' + m.group(0) + '</div>',
        rendered
    )

    # Full page
    date = datetime.now().strftime("%d.%m.%Y %H:%M")
    page = HTML_TEMPLATE.format(title=title, date=date, content=rendered)

    # Save HTML
    with open(ndir / "index.html", "w") as f:
        f.write(page)

    # Save metadata
    meta = {"title": title, "date": date, "id": note_id}
    with open(ndir / "meta.json", "w") as f:
        json.dump(meta, f, ensure_ascii=False)

    return {"id": note_id, "url": f"/note/{note_id}"}


@app.get("/note/{note_id}", response_class=HTMLResponse)
async def view_note(note_id: str):
    ndir = note_dir(note_id)
    html_path = ndir / "index.html"
    if not html_path.exists():
        raise HTTPException(404, "Note not found")
    return HTMLResponse(content=html_path.read_text())


@app.get("/note/{note_id}/files/{filename}")
async def get_file(note_id: str, filename: str):
    fpath = note_dir(note_id) / filename
    if not fpath.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(fpath)


@app.get("/api/notes")
async def list_notes():
    """List all shared notes."""
    notes = []
    for d in sorted(UPLOADS_DIR.iterdir(), reverse=True):
        meta_path = d / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            notes.append(meta)
    return {"notes": notes}


@app.get("/", response_class=HTMLResponse)
async def index():
    """Index page listing all shared notes."""
    notes_data = []
    for d in sorted(UPLOADS_DIR.iterdir(), reverse=True):
        meta_path = d / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            notes_data.append(meta)

    notes_html = ""
    for n in notes_data:
        notes_html += f'''
        <a href="/note/{n['id']}" style="display:block; padding:16px; background:var(--surface); border-radius:8px; margin-bottom:8px; text-decoration:none; color:var(--text); transition: background 0.2s;">
          <div style="font-size:1.1em; font-weight:600; color:var(--accent);">{n['title']}</div>
          <div style="font-size:0.85em; color:var(--text-muted); margin-top:4px;">📅 {n['date']}</div>
        </a>'''

    page = HTML_TEMPLATE.format(
        title="Shared Notes",
        date="",
        content=f'<h1>📝 Shared Notes</h1>{notes_html}' if notes_data else '<h1>📝 Shared Notes</h1><p style="color:var(--text-muted)">No notes yet. Share from Obsidian!</p>'
    )
    return HTMLResponse(content=page)


@app.delete("/api/note/{note_id}")
async def delete_note(note_id: str):
    ndir = note_dir(note_id)
    if not ndir.exists():
        raise HTTPException(404, "Note not found")
    import shutil
    shutil.rmtree(ndir)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9100)


@app.get("/plugin", response_class=HTMLResponse)
async def plugin_page():
    """Plugin download page."""
    plugin_html = """
    <div style="max-width:640px; margin:0 auto;">
        <h1>🔌 Share Note Plugin</h1>
        <p style="color:var(--text-muted); margin-bottom:24px;">
            Obsidian plugin for one-click note sharing to your self-hosted server.
        </p>
        <div style="background:var(--surface); border-radius:12px; padding:24px; margin-bottom:24px;">
            <h3 style="margin-top:0;">📦 Installation</h3>
            <ol style="line-height:2;">
                <li>Download <code style="background:var(--code-bg); padding:2px 6px; border-radius:4px;">main.js</code>, <code style="background:var(--code-bg); padding:2px 6px; border-radius:4px;">manifest.json</code>, <code style="background:var(--code-bg); padding:2px 6px; border-radius:4px;">styles.css</code></li>
                <li>Create folder <code style="background:var(--code-bg); padding:2px 6px; border-radius:4px;">.obsidian/plugins/share-note-selfhosted/</code></li>
                <li>Put all 3 files inside</li>
                <li>Obsidian Settings → Community plugins → Reload → Enable <strong>Share Note (Self-Hosted)</strong></li>
                <li>Set server URL to:<br>
                    <code style="background:var(--code-bg); padding:8px 12px; border-radius:6px; display:inline-block; margin-top:8px;">https://share.142-252-220-144.sslip.io:8444</code>
                </li>
            </ol>
        </div>
        <div style="background:var(--surface); border-radius:12px; padding:24px; margin-bottom:24px;">
            <h3 style="margin-top:0;">⬇️ Download</h3>
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <a href="/plugin/main.js" style="padding:10px 20px; background:var(--accent); color:#1e1e2e; border-radius:8px; text-decoration:none; font-weight:600;">main.js</a>
                <a href="/plugin/manifest.json" style="padding:10px 20px; background:var(--accent); color:#1e1e2e; border-radius:8px; text-decoration:none; font-weight:600;">manifest.json</a>
                <a href="/plugin/styles.css" style="padding:10px 20px; background:var(--accent); color:#1e1e2e; border-radius:8px; text-decoration:none; font-weight:600;">styles.css</a>
            </div>
        </div>
        <div style="background:var(--surface); border-radius:12px; padding:24px;">
            <h3 style="margin-top:0;">🚀 Usage</h3>
            <p>Open any note, click the ribbon icon or run <em>Share Note: Share current note</em> — link copied to clipboard!</p>
            <p style="color:var(--text-muted); font-size:0.9em; margin-top:12px;">All shared notes: <a href="/" style="color:var(--accent);">home page</a></p>
        </div>
    </div>
    """
    page = HTML_TEMPLATE.format(title="Share Note Plugin", date="", content=plugin_html)
    return HTMLResponse(content=page)


@app.get("/plugin/{filename}")
async def plugin_file(filename: str):
    """Serve plugin files for download."""
    plugin_dir = Path("/home/clawd/obsidian-vault/.obsidian/plugins/share-note-selfhosted")
    fpath = plugin_dir / filename
    if not fpath.exists() or filename not in ("main.js", "manifest.json", "styles.css"):
        raise HTTPException(404, "File not found")
    return FileResponse(fpath, filename=filename)
