# Image Viewer Compare - VS Code Extension

A VS Code extension for side-by-side comparison of images processed with different methods. This is the VS Code version of the Streamlit Image Viewer app.

## Features

- 📁 Load image configurations from JSON files
- 🖼️ Side-by-side comparison of images across multiple methods
- 🔄 Navigate between samples with Previous/Next buttons
- 🎨 Toggle display options (method names, descriptions, sample text)
- 📊 Adjustable number of rows to display
- 🌐 Bilingual support (English/Chinese)

## Installation

### From Source

1. Navigate to the extension directory:
   ```bash
   cd vscode_extension
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Compile TypeScript:
   ```bash
   npm run compile
   ```

4. Open VS Code and press `F5` to run the extension in development mode, or package it:
   ```bash
   npx vsce package
   ```

### Usage

1. **Open via Command Palette**:
   - Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
   - Type "Image Viewer: Open Viewer"
   - Select a JSON configuration file

2. **Open via Context Menu**:
   - Right-click on a `.json` file in the Explorer
   - Select "Image Viewer: Open Configuration File"

## JSON Configuration Format

The extension uses the same JSON format as the Streamlit app:

```json
{
  "base_dir": "./images",
  "methods": [
    {
      "name": "Method A",
      "description": "Description of Method A"
    },
    {
      "name": "Method B",
      "description": "Description of Method B"
    }
  ],
  "samples": [
    {
      "name": "Sample 1",
      "text": "Sample description text",
      "images": {
        "Method A": "relative/path/to/image_a.jpg",
        "Method B": "relative/path/to/image_b.jpg"
      }
    }
  ]
}
```

### Field Descriptions

- **base_dir**: Base directory for image paths (relative to the JSON file location)
- **methods**: Array of method objects
  - **name** (required): Display name of the method
  - **description** (optional): Description of the method
- **samples**: Array of sample objects
  - **name** (required): Display name of the sample
  - **text** (optional): Sample description or prompt text
  - **images** (required): Object mapping method names to relative image paths

## Display Options

- **Show Method Name**: Toggle visibility of method names above images
- **Show Description**: Toggle visibility of method descriptions
- **Show Sample Name**: Toggle visibility of sample names
- **Show Sample Text**: Toggle visibility of sample text/prompts
- **Rows**: Number of samples to display at once (1, 2, 3, or 5)

## Navigation

- Use **Previous** / **Next** buttons to navigate between samples
- The current position is displayed as "Current: X / Y"

## Language Toggle

Click the "中/En" button to switch between English and Chinese interface.

## Differences from Streamlit Version

| Feature | Streamlit App | VS Code Extension |
|---------|---------------|-------------------|
| Image cropping | ✅ Full support | ❌ Not available |
| Mask support | ✅ Full support | ❌ Not available |
| PDF export | ✅ Full support | ❌ Not available |
| Close View | ✅ Full support | ❌ Not available |
| Basic viewing | ✅ | ✅ |
| Navigation | ✅ | ✅ |
| Multi-language | ✅ | ✅ |

The VS Code extension focuses on the core image comparison functionality, providing a lightweight viewer integrated directly into VS Code.

## Development

### Project Structure

```
vscode_extension/
├── package.json         # Extension manifest
├── tsconfig.json        # TypeScript configuration
├── src/
│   └── extension.ts     # Main extension code
├── media/               # Static assets (if needed)
└── README.md            # This file
```

### Commands

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch for changes
npm run watch

# Package extension
npx vsce package
```

## License

This extension is part of the Image Viewer project.
