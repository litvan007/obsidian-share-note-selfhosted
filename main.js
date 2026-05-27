var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// main.ts
var main_exports = {};
__export(main_exports, {
  default: () => ShareNotePlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");
var DEFAULT_SETTINGS = {
  serverUrl: "https://share.142-252-220-144.sslip.io:8444"
};
var ShareNotePlugin = class extends import_obsidian.Plugin {
  async onload() {
    await this.loadSettings();
    this.addRibbonIcon("share", "Share Note", async () => {
      await this.shareActiveNote();
    });
    this.addCommand({
      id: "share-note",
      name: "Share current note",
      callback: async () => {
        await this.shareActiveNote();
      }
    });
    this.registerEvent(
      this.app.workspace.on("file-menu", (menu, file) => {
        if (file instanceof import_obsidian.TFile && file.extension === "md") {
          menu.addItem((item) => {
            item.setTitle("\u{1F517} Share Note").setIcon("share").onClick(async () => {
              await this.shareFile(file);
            });
          });
        }
      })
    );
    this.addSettingTab(new ShareNoteSettingTab(this.app, this));
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  async shareActiveNote() {
    const file = this.app.workspace.getActiveFile();
    if (!file) {
      new import_obsidian.Notice("No active file");
      return;
    }
    await this.shareFile(file);
  }
  async shareFile(file) {
    if (file.extension !== "md") {
      new import_obsidian.Notice("Only markdown files are supported");
      return;
    }
    new import_obsidian.Notice("Sharing note...");
    try {
      const content = await this.app.vault.read(file);
      const title = file.basename;
      const embedRegex = /!\[\[([^\]]+)\]\]/g;
      const embedMatches = [...content.matchAll(embedRegex)];
      const mdImgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
      const mdImgMatches = [...content.matchAll(mdImgRegex)];
      const filesToUpload = [];
      const uploadedNames = /* @__PURE__ */ new Set();
      for (const match of embedMatches) {
        const ref = match[1].split("|")[0].trim();
        const linkedFile = this.app.metadataCache.getFirstLinkpathDest(ref, file.path);
        if (linkedFile && !uploadedNames.has(linkedFile.name)) {
          const data = await this.app.vault.readBinary(linkedFile);
          filesToUpload.push({ name: linkedFile.name, data });
          uploadedNames.add(linkedFile.name);
        }
      }
      for (const match of mdImgMatches) {
        const imgPath = match[2];
        const imgFile = this.app.vault.getAbstractFileByPath(imgPath);
        if (imgFile instanceof import_obsidian.TFile && !uploadedNames.has(imgFile.name)) {
          const data = await this.app.vault.readBinary(imgFile);
          filesToUpload.push({ name: imgFile.name, data });
          uploadedNames.add(imgFile.name);
        }
      }
      const boundary = "----ObsidianShare" + Date.now();
      const parts = [];
      const mdHeader = `--${boundary}\r
Content-Disposition: form-data; name="markdown"\r
\r
`;
      const mdFooter = "\r\n";
      parts.push(new TextEncoder().encode(mdHeader));
      parts.push(new TextEncoder().encode(content));
      parts.push(new TextEncoder().encode(mdFooter));
      const titleHeader = `--${boundary}\r
Content-Disposition: form-data; name="title"\r
\r
`;
      parts.push(new TextEncoder().encode(titleHeader));
      parts.push(new TextEncoder().encode(title));
      parts.push(new TextEncoder().encode(mdFooter));
      for (const f of filesToUpload) {
        const fileHeader = `--${boundary}\r
Content-Disposition: form-data; name="files"; filename="${f.name}"\r
Content-Type: application/octet-stream\r
\r
`;
        parts.push(new TextEncoder().encode(fileHeader));
        parts.push(f.data);
        parts.push(new TextEncoder().encode("\r\n"));
      }
      parts.push(new TextEncoder().encode(`--${boundary}--\r
`));
      const totalLength = parts.reduce((sum, p) => sum + p.byteLength, 0);
      const body = new Uint8Array(totalLength);
      let offset = 0;
      for (const part of parts) {
        body.set(new Uint8Array(part), offset);
        offset += part.byteLength;
      }
      const response = await (0, import_obsidian.requestUrl)({
        url: `${this.settings.serverUrl}/api/share`,
        method: "POST",
        headers: {
          "Content-Type": `multipart/form-data; boundary=${boundary}`
        },
        body: body.buffer
      });
      if (response.status === 200) {
        const data = response.json;
        const url = `${this.settings.serverUrl}${data.url}`;
        await navigator.clipboard.writeText(url);
        new import_obsidian.Notice(`\u2705 Link copied: ${url}`);
      } else {
        new import_obsidian.Notice(`\u274C Error: ${response.status}`);
      }
    } catch (error) {
      console.error("Share Note error:", error);
      new import_obsidian.Notice(`\u274C Error: ${error.message}`);
    }
  }
};
var ShareNoteSettingTab = class extends import_obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Share Note Settings" });
    new import_obsidian.Setting(containerEl).setName("Server URL").setDesc("URL of your Share Note server").addText(
      (text) => text.setPlaceholder("https://share.example.com").setValue(this.plugin.settings.serverUrl).onChange(async (value) => {
        this.plugin.settings.serverUrl = value;
        await this.plugin.saveSettings();
      })
    );
  }
};
//# sourceMappingURL=main.js.map
