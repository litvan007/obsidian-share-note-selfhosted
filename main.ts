import { App, Plugin, PluginSettingTab, Setting, Notice, TFile, requestUrl, MarkdownRenderer, Component } from 'obsidian';

interface PageSharingSettings {
	serverUrl: string;
}

const DEFAULT_SETTINGS: PageSharingSettings = {
	serverUrl: 'https://share.142-252-220-144.sslip.io:8444'
}

export default class PageSharingPlugin extends Plugin {
	settings: PageSharingSettings;

	async onload() {
		await this.loadSettings();

		// Ribbon icon
		this.addRibbonIcon('share', 'Page Sharing', async () => {
			await this.shareActiveNote();
		});

		// Command
		this.addCommand({
			id: 'share-note',
			name: 'Share current page',
			callback: async () => {
				await this.shareActiveNote();
			},
		});

		// File context menu
		this.registerEvent(
			this.app.workspace.on('file-menu', (menu, file) => {
				if (file instanceof TFile && file.extension === 'md') {
					menu.addItem((item) => {
						item
							.setTitle('🔗 Share Page')
							.setIcon('share')
							.onClick(async () => {
								await this.shareFile(file);
							});
					});
				}
			})
		);

		// Settings tab
		this.addSettingTab(new PageSharingSettingTab(this.app, this));
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
			new Notice('No active file');
			return;
		}
		await this.shareFile(file);
	}

	async shareFile(file: TFile) {
		if (file.extension !== 'md') {
			new Notice('Only markdown files are supported');
			return;
		}

		new Notice('Sharing note...');

		try {
			// Read markdown content
			const content = await this.app.vault.read(file);
			const title = file.basename;

			// Find all ![[image.jpg]] and ![[image.jpg|alt]] embeds
			const embedRegex = /!\[\[([^\]]+)\]\]/g;
			const embedMatches = [...content.matchAll(embedRegex)];

			// Also find standard markdown images ![alt](path) 
			const mdImgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
			const mdImgMatches = [...content.matchAll(mdImgRegex)];

			// Collect unique file references
			const filesToUpload: { name: string; data: ArrayBuffer }[] = [];
			const uploadedNames = new Set<string>();

			// Process ![[embeds]]
			for (const match of embedMatches) {
				const ref = match[1].split('|')[0].trim(); // Remove |alt part
				const linkedFile = this.app.metadataCache.getFirstLinkpathDest(ref, file.path);
				if (linkedFile && !uploadedNames.has(linkedFile.name)) {
					const data = await this.app.vault.readBinary(linkedFile);
					filesToUpload.push({ name: linkedFile.name, data });
					uploadedNames.add(linkedFile.name);
				}
			}

			// Process ![](path) images
			for (const match of mdImgMatches) {
				const imgPath = match[2];
				const imgFile = this.app.vault.getAbstractFileByPath(imgPath);
				if (imgFile instanceof TFile && !uploadedNames.has(imgFile.name)) {
					const data = await this.app.vault.readBinary(imgFile);
					filesToUpload.push({ name: imgFile.name, data });
					uploadedNames.add(imgFile.name);
				}
			}

			// Build multipart form data
			const boundary = '----ObsidianShare' + Date.now();
			const parts: ArrayBuffer[] = [];

			// Add markdown field
			const mdHeader = `--${boundary}\r\nContent-Disposition: form-data; name="markdown"\r\n\r\n`;
			const mdFooter = '\r\n';
			parts.push(new TextEncoder().encode(mdHeader));
			parts.push(new TextEncoder().encode(content));
			parts.push(new TextEncoder().encode(mdFooter));

			// Add title field
			const titleHeader = `--${boundary}\r\nContent-Disposition: form-data; name="title"\r\n\r\n`;
			parts.push(new TextEncoder().encode(titleHeader));
			parts.push(new TextEncoder().encode(title));
			parts.push(new TextEncoder().encode(mdFooter));

			// Add files
			for (const f of filesToUpload) {
				const fileHeader = `--${boundary}\r\nContent-Disposition: form-data; name="files"; filename="${f.name}"\r\nContent-Type: application/octet-stream\r\n\r\n`;
				parts.push(new TextEncoder().encode(fileHeader));
				parts.push(f.data);
				parts.push(new TextEncoder().encode('\r\n'));
			}

			// Close boundary
			parts.push(new TextEncoder().encode(`--${boundary}--\r\n`));

			// Combine all parts
			const totalLength = parts.reduce((sum, p) => sum + p.byteLength, 0);
			const body = new Uint8Array(totalLength);
			let offset = 0;
			for (const part of parts) {
				body.set(new Uint8Array(part), offset);
				offset += part.byteLength;
			}

			// Send request
			const response = await requestUrl({
				url: `${this.settings.serverUrl}/api/share`,
				method: 'POST',
				headers: {
					'Content-Type': `multipart/form-data; boundary=${boundary}`,
				},
				body: body.buffer as ArrayBuffer,
			});

			if (response.status === 200) {
				const data = response.json;
				const url = `${this.settings.serverUrl}${data.url}`;
				
				// Copy to clipboard
				await navigator.clipboard.writeText(url);
				new Notice(`✅ Link copied: ${url}`);
			} else {
				new Notice(`❌ Error: ${response.status}`);
			}
		} catch (error) {
			console.error('Page Sharing error:', error);
			new Notice(`❌ Error: ${error.message}`);
		}
	}
}

class PageSharingSettingTab extends PluginSettingTab {
	plugin: PageSharingPlugin;

	constructor(app: App, plugin: PageSharingPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl('h2', { text: 'Page Sharing Settings' });

		containerEl.createEl('p', {
			text: 'By default, notes are shared via the plugin author\'s server. You can change this to your own self-hosted server if preferred.',
			cls: 'setting-item-description'
		});

		new Setting(containerEl)
			.setName('Server URL')
			.setDesc('The server where your notes will be uploaded. Default: the shared public server. Change this to your own server URL if you have one.')
			.addText((text) =>
				text
					.setPlaceholder('https://share.example.com')
					.setValue(this.plugin.settings.serverUrl)
					.onChange(async (value) => {
						this.plugin.settings.serverUrl = value;
						await this.plugin.saveSettings();
					})
			);
	}
}
