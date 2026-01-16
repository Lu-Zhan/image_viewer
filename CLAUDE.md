# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Streamlit-based image comparison visualization tool for side-by-side comparison of images processed with different methods. Users upload a JSON configuration file defining image sets and methods, then browse samples with navigation controls.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## Architecture

Single-file Streamlit application (`app.py`) with these key components:

- **JSON Configuration Loader** (`load_json_config`): Validates uploaded JSON with required fields: `base_dir`, `methods`, `samples`
- **Image Processing Pipeline** (`load_and_process_image`): Loads images, auto-crops non-square images to 1:1 ratio (center crop if aspect ratio differs by >5%), resizes to target width
- **Session State**: Tracks `selected_sample_idx`, `show_text`, `show_descriptions` for UI persistence across reruns

## JSON Configuration Format

```json
{
  "base_dir": "path/to/images",
  "methods": [{"name": "MethodName", "description": "optional"}],
  "samples": [{"name": "SampleName", "text": "optional", "images": {"MethodName": "relative/path.png"}}]
}
```

## Key Behaviors

- Images with aspect ratio >5% from 1:1 are automatically center-cropped to square
- Sidebar controls: image width slider (256-1024px), multi-row display, sample navigation
- Aspect ratio inconsistencies across methods trigger a collapsible warning
