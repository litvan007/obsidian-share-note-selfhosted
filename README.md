# Page Sharing

Obsidian plugin for one-click note sharing via a link.

**Default:** notes are shared via the plugin author's server. You can change this to your own self-hosted server in settings.

## Install

1. Create folder `.obsidian/plugins/page-sharing/` in your vault
2. Download [main.js](https://github.com/litvan007/obsidian-share-note-selfhosted/releases/latest/download/main.js), [manifest.json](https://github.com/litvan007/obsidian-share-note-selfhosted/releases/latest/download/manifest.json), [styles.css](https://github.com/litvan007/obsidian-share-note-selfhosted/releases/latest/download/styles.css) into it
3. Restart Obsidian
4. Settings → Community plugins → enable **Page Sharing**

## Usage

Open any note → click the share icon in the ribbon (or run the command) → link is copied to your clipboard.

## Settings

- **Server URL** — defaults to the shared public server. Change to your own if you self-host.

## Self-hosting

See the `server/` folder for the FastAPI backend. Deploy with Docker or manually.

## License

MIT
