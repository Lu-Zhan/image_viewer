import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as fsSync from 'fs';

/**
 * Image Viewer Compare Extension
 * A VS Code extension for side-by-side comparison of images processed with different methods
 */

interface Method {
    name: string;
    description?: string;
}

interface Sample {
    name: string;
    text?: string;
    mask?: string;
    images: { [methodName: string]: string };
}

interface ImageConfig {
    base_dir: string;
    methods: Method[];
    samples: Sample[];
}

let currentPanel: vscode.WebviewPanel | undefined = undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Image Viewer Compare extension is now active');

    // Register command to open viewer
    const openViewerCommand = vscode.commands.registerCommand('imageViewerCompare.openViewer', async () => {
        const fileUri = await vscode.window.showOpenDialog({
            canSelectFiles: true,
            canSelectFolders: false,
            canSelectMany: false,
            filters: {
                'JSON Files': ['json']
            },
            title: 'Select Image Configuration File'
        });

        if (fileUri && fileUri[0]) {
            await openImageViewer(context, fileUri[0]);
        }
    });

    // Register command to open config from context menu
    const openConfigCommand = vscode.commands.registerCommand('imageViewerCompare.openConfig', async (uri: vscode.Uri) => {
        await openImageViewer(context, uri);
    });

    context.subscriptions.push(openViewerCommand, openConfigCommand);
}

async function openImageViewer(context: vscode.ExtensionContext, configUri: vscode.Uri) {
    const configPath = configUri.fsPath;
    
    // Read and parse the config file asynchronously
    let config: ImageConfig;
    try {
        const configContent = await fs.readFile(configPath, 'utf-8');
        config = JSON.parse(configContent);
        
        // Validate config
        const validationResult = validateConfig(config);
        if (!validationResult.valid) {
            vscode.window.showErrorMessage(`Invalid configuration: ${validationResult.error}`);
            return;
        }
        
        // Resolve base_dir relative to config file location
        const configDir = path.dirname(configPath);
        if (!path.isAbsolute(config.base_dir)) {
            config.base_dir = path.resolve(configDir, config.base_dir);
        }
    } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        vscode.window.showErrorMessage(`Failed to load configuration file: ${errorMessage}`);
        return;
    }

    // Create or show the webview panel
    if (currentPanel) {
        currentPanel.reveal(vscode.ViewColumn.One);
    } else {
        currentPanel = vscode.window.createWebviewPanel(
            'imageViewerCompare',
            'Image Viewer Compare',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [
                    vscode.Uri.file(config.base_dir),
                    vscode.Uri.joinPath(context.extensionUri, 'media')
                ]
            }
        );

        currentPanel.onDidDispose(() => {
            currentPanel = undefined;
        }, null, context.subscriptions);
    }

    // Update webview content
    currentPanel.webview.html = await getWebviewContent(currentPanel.webview, context, config);

    // Handle messages from the webview
    currentPanel.webview.onDidReceiveMessage(
        async message => {
            switch (message.command) {
                case 'getImageUri':
                    const imagePath = path.join(config.base_dir, message.relativePath);
                    try {
                        await fs.access(imagePath);
                        const imageUri = currentPanel!.webview.asWebviewUri(vscode.Uri.file(imagePath));
                        currentPanel!.webview.postMessage({
                            command: 'imageUri',
                            id: message.id,
                            uri: imageUri.toString()
                        });
                    } catch {
                        currentPanel!.webview.postMessage({
                            command: 'imageUri',
                            id: message.id,
                            uri: null,
                            error: `Image not found: ${message.relativePath}`
                        });
                    }
                    break;
            }
        },
        undefined,
        context.subscriptions
    );
}

function validateConfig(config: unknown): { valid: boolean; error?: string } {
    if (typeof config !== 'object' || config === null) {
        return { valid: false, error: 'Configuration must be an object' };
    }

    const cfg = config as Record<string, unknown>;

    if (!cfg.base_dir || typeof cfg.base_dir !== 'string') {
        return { valid: false, error: 'Missing or invalid base_dir field' };
    }

    if (!Array.isArray(cfg.methods) || cfg.methods.length === 0) {
        return { valid: false, error: 'methods must be a non-empty array' };
    }

    const methodNames = new Set<string>();
    for (const method of cfg.methods) {
        if (!method.name || typeof method.name !== 'string') {
            return { valid: false, error: 'Each method must have a name property' };
        }
        methodNames.add(method.name);
    }

    if (!Array.isArray(cfg.samples) || cfg.samples.length === 0) {
        return { valid: false, error: 'samples must be a non-empty array' };
    }

    for (const sample of cfg.samples) {
        if (!sample.name || typeof sample.name !== 'string') {
            return { valid: false, error: 'Each sample must have a name property' };
        }
        if (!sample.images || typeof sample.images !== 'object') {
            return { valid: false, error: `Sample "${sample.name}" must have an images object` };
        }
        // Validate that image keys reference valid methods
        for (const methodName of Object.keys(sample.images)) {
            if (!methodNames.has(methodName)) {
                return { valid: false, error: `Sample "${sample.name}" references unknown method "${methodName}"` };
            }
        }
    }

    return { valid: true };
}

function getNonce(): string {
    let text = '';
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    for (let i = 0; i < 32; i++) {
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    }
    return text;
}

async function getWebviewContent(webview: vscode.Webview, context: vscode.ExtensionContext, config: ImageConfig): Promise<string> {
    // Get URIs for external resources
    const styleUri = webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'styles.css'));
    const scriptUri = webview.asWebviewUri(vscode.Uri.joinPath(context.extensionUri, 'media', 'main.js'));
    
    // Generate nonce for inline script (for config injection only)
    const nonce = getNonce();
    
    // Convert image paths to webview URIs
    const samplesWithUris = await Promise.all(config.samples.map(async sample => {
        const images: { [key: string]: string } = {};
        for (const [methodName, relativePath] of Object.entries(sample.images)) {
            const absolutePath = path.join(config.base_dir, relativePath);
            try {
                await fs.access(absolutePath);
                images[methodName] = webview.asWebviewUri(vscode.Uri.file(absolutePath)).toString();
            } catch {
                images[methodName] = '';
            }
        }
        return { ...sample, images };
    }));

    const configJson = JSON.stringify({
        methods: config.methods,
        samples: samplesWithUris
    });

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src ${webview.cspSource} https: data:; script-src 'nonce-${nonce}' ${webview.cspSource}; style-src ${webview.cspSource};">
    <title>Image Viewer Compare</title>
    <link rel="stylesheet" href="${styleUri}">
</head>
<body>
    <div class="header">
        <span class="title">🖼️ <span id="viewerTitle">Image Viewer</span></span>
        <div class="controls">
            <button class="language-toggle" onclick="toggleLanguage()">中/En</button>
            <button id="prevBtn" onclick="prevSample()">◀ <span data-i18n="prev">Previous</span></button>
            <span class="sample-info">
                <span id="currentLabel" data-i18n="current">Current</span>: 
                <span id="currentIndex">1</span> / <span id="totalSamples">1</span>
            </span>
            <button id="nextBtn" onclick="nextSample()"><span data-i18n="next">Next</span> ▶</button>
        </div>
    </div>
    
    <div class="options">
        <label class="option">
            <input type="checkbox" id="showMethodName" checked onchange="render()">
            <span data-i18n="showMethodName">Show Method Name</span>
        </label>
        <label class="option">
            <input type="checkbox" id="showDescription" onchange="render()">
            <span data-i18n="showDescription">Show Description</span>
        </label>
        <label class="option">
            <input type="checkbox" id="showSampleName" checked onchange="render()">
            <span data-i18n="showSampleName">Show Sample Name</span>
        </label>
        <label class="option">
            <input type="checkbox" id="showText" checked onchange="render()">
            <span data-i18n="showText">Show Sample Text</span>
        </label>
        <label class="option">
            <span data-i18n="numRows">Rows</span>:
            <select id="numRows" onchange="render()">
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3" selected>3</option>
                <option value="5">5</option>
            </select>
        </label>
    </div>
    
    <div id="imageGrid" class="image-grid"></div>
    
    <script nonce="${nonce}">
        window.imageViewerConfig = ${configJson};
    </script>
    <script src="${scriptUri}"></script>
</body>
</html>`;
}

export function deactivate() {}
