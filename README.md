# Delta Skin to RetroArch Overlay Converter

Convert Delta emulator touch controller skins (`.deltaskin` files) to RetroArch overlay `.cfg` files with PNG assets.

## Web Version (Recommended)

Use the web converter directly in your browser - no installation required:

**[Open Web Converter](https://warmenhoven.github.io/skin2overlay/)** *(update URL after deploying)*

Or run locally:
```bash
# Open index.html in your browser
open index.html
```

The web version runs entirely in your browser - your files never leave your device.

---

## Command Line Version

### Requirements

- Python 3.8+
- [Poppler](https://poppler.freedesktop.org/) (for PDF to PNG conversion)

#### macOS

```bash
brew install poppler
```

#### Linux

```bash
sudo apt install poppler-utils  # Debian/Ubuntu
```

### Installation

```bash
git clone https://github.com/warmenhoven/skin2overlay.git
cd skin2overlay
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Convert a single skin
python convert.py /path/to/Standard.deltaskin -o output/

# Convert specific devices only
python convert.py skin.deltaskin -o output/ --devices iphone ipad

# Convert all skins in a directory
python convert.py ~/skins/*.deltaskin -o output/

# Adjust image scale (default: 3x for retina)
python convert.py skin.deltaskin -o output/ --scale 2
```

## Output Structure

The converter generates one overlay per device, with portrait and landscape orientations in the same config file:

```
output/
├── SkinName_GameType_iphone/
│   ├── SkinName_GameType_iphone.cfg   # RetroArch overlay config
│   ├── portrait.png                    # Portrait orientation image
│   └── landscape.png                   # Landscape orientation image
├── SkinName_GameType_ipad/
│   └── ...
└── SkinName_GameType_tv/
    └── ...
```

## Features

- **Input Mapping**: Converts Delta button inputs to RetroArch equivalents
  - Standard buttons (A, B, X, Y, L, R, Start, Select)
  - D-pad → `dpad_area`
  - Analog stick → `analog_left`
  - N64 C-buttons → right analog (r_x_minus, r_x_plus, r_y_minus, r_y_plus)
  - N64 Z button → L2

- **Viewport Positioning**: Converts `gameScreenFrame` to `overlay_viewport`
  - DS dual screens: Computes bounding box of both screens

- **Extended Touch Edges**: Converts to RetroArch `reach_*` parameters

- **Rotation Support**: Portrait/landscape as separate overlay indices with invisible rotation buttons

- **PDF to PNG**: Renders vector PDFs at 3x mappingSize (retina quality)

## Supported Platforms

- NES
- SNES
- N64
- Game Boy / Game Boy Color
- Game Boy Advance
- Nintendo DS
- Sega Genesis

## Limitations

- **Screen filters** (CIFilter) - No RetroArch equivalent
- **DS touch input** - Not directly convertible
- **TV auto-detection** - TV overlays are generated but must be manually selected

## Input Format

The converter accepts:
- `.deltaskin` ZIP archives (standard distribution format)
- Expanded deltaskin directories (as found in Delta source code)

## License

MIT
