#!/usr/bin/env python3
"""
Delta Skin to RetroArch Overlay Converter

Converts .deltaskin files (Delta emulator touch controller skins)
to RetroArch overlay .cfg files with PNG assets.
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

try:
    from pdf2image import convert_from_bytes
except ImportError:
    convert_from_bytes = None
    print("Warning: pdf2image not installed. PDF conversion will fail.", file=sys.stderr)
    print("Install with: pip install pdf2image", file=sys.stderr)
    print("Also requires poppler: brew install poppler", file=sys.stderr)

from input_mapping import DELTA_TO_RETROARCH, GAME_TYPE_NAMES


def parse_deltaskin(deltaskin_path):
    """Extract and parse a deltaskin file or directory."""
    deltaskin_path = Path(deltaskin_path)

    # Check if it's a directory or has info.json adjacent (expanded deltaskin)
    if deltaskin_path.is_dir():
        skin_dir = deltaskin_path
    elif deltaskin_path.suffix == '.deltaskin' and (deltaskin_path.parent / 'info.json').exists():
        # Expanded deltaskin in source repo - info.json is in same directory
        skin_dir = deltaskin_path.parent
    else:
        skin_dir = None

    if skin_dir:
        # Read from directory
        info_path = skin_dir / 'info.json'
        with open(info_path, 'r') as f:
            info = json.load(f)

        files = {}
        for item in skin_dir.iterdir():
            if item.name != 'info.json' and item.is_file():
                files[item.name] = item.read_bytes()

        return info, files

    # Read from ZIP archive
    with zipfile.ZipFile(deltaskin_path, 'r') as zf:
        info_json = zf.read('info.json')
        info = json.loads(info_json)

        files = {}
        for name in zf.namelist():
            if name != 'info.json':
                files[name] = zf.read(name)

    return info, files


def get_display_type_preference(device_data):
    """Get the preferred display type from available options."""
    # Prefer edgeToEdge, then standard, then splitView
    for dtype in ['edgeToEdge', 'standard', 'splitView']:
        if dtype in device_data:
            return dtype
    # Return first available
    return next(iter(device_data.keys())) if device_data else None


def convert_pdf_to_png(pdf_bytes, mapping_size, scale=3):
    """Convert PDF bytes to PNG image at the specified scale."""
    if convert_from_bytes is None:
        raise RuntimeError("pdf2image not installed")

    target_width = int(mapping_size['width'] * scale)
    target_height = int(mapping_size['height'] * scale)

    images = convert_from_bytes(pdf_bytes, size=(target_width, target_height))
    return images[0] if images else None


def compute_bounding_box(frames):
    """Compute the bounding box encompassing all frames (for DS dual screens)."""
    if not frames:
        return None

    min_x = min(f['x'] for f in frames)
    min_y = min(f['y'] for f in frames)
    max_x = max(f['x'] + f['width'] for f in frames)
    max_y = max(f['y'] + f['height'] for f in frames)

    return {
        'x': min_x,
        'y': min_y,
        'width': max_x - min_x,
        'height': max_y - min_y
    }


def normalize_frame(frame, mapping_size):
    """Convert pixel coordinates to normalized 0-1 coordinates (center + half-size)."""
    x = (frame['x'] + frame['width'] / 2) / mapping_size['width']
    y = (frame['y'] + frame['height'] / 2) / mapping_size['height']
    w = (frame['width'] / 2) / mapping_size['width']
    h = (frame['height'] / 2) / mapping_size['height']
    return x, y, w, h


def is_dpad(inputs):
    """Check if inputs represent a d-pad."""
    if not isinstance(inputs, dict):
        return False
    return all(k in inputs for k in ['up', 'down', 'left', 'right'])


def is_analog_stick(inputs):
    """Check if inputs represent an analog stick."""
    if not isinstance(inputs, dict):
        return False
    # Check for analog stick - values contain 'analogStick' prefix
    analog_values = ['analogStickUp', 'analogStickDown', 'analogStickLeft', 'analogStickRight']
    return any(v in analog_values for v in inputs.values() if isinstance(v, str))


def convert_item_to_descriptor(item, mapping_size, index, overlay_index=0):
    """Convert a Delta item to RetroArch overlay descriptor(s)."""
    frame = item.get('frame')
    inputs = item.get('inputs')

    if not frame or not inputs:
        return []

    x, y, w, h = normalize_frame(frame, mapping_size)
    prefix = f'overlay{overlay_index}_desc{index}'
    lines = []

    if isinstance(inputs, list) and len(inputs) > 0:
        # Single button or list of buttons
        ra_input = DELTA_TO_RETROARCH.get(inputs[0], inputs[0])
        if ra_input:
            lines.append(f'{prefix} = "{ra_input},{x:.6f},{y:.6f},radial,{w:.6f},{h:.6f}"')

    elif isinstance(inputs, dict):
        if is_analog_stick(inputs):
            # Analog stick
            lines.append(f'{prefix} = "analog_left,{x:.6f},{y:.6f},radial,{w:.6f},{h:.6f}"')
        elif is_dpad(inputs):
            # D-pad
            lines.append(f'{prefix} = "dpad_area,{x:.6f},{y:.6f},rect,{w:.6f},{h:.6f}"')

    # Handle extended edges if present
    extended = item.get('extendedEdges', {})
    if extended:
        if extended.get('top'):
            lines.append(f'{prefix}_reach_up = {1 + extended["top"] / (frame["height"] / 2):.2f}')
        if extended.get('bottom'):
            lines.append(f'{prefix}_reach_down = {1 + extended["bottom"] / (frame["height"] / 2):.2f}')
        if extended.get('left'):
            lines.append(f'{prefix}_reach_left = {1 + extended["left"] / (frame["width"] / 2):.2f}')
        if extended.get('right'):
            lines.append(f'{prefix}_reach_right = {1 + extended["right"] / (frame["width"] / 2):.2f}')

    return lines


def generate_overlay_config(skin_name, device, orientations, portrait_data, landscape_data):
    """Generate overlay config for a device with portrait/landscape rotation support."""
    lines = []
    num_overlays = len(orientations)
    lines.append(f'overlays = {num_overlays}')
    lines.append('')

    overlay_index = 0

    for orientation in orientations:
        if orientation == 'portrait' and portrait_data:
            data = portrait_data
            aspect_ratio = data['mappingSize']['height'] / data['mappingSize']['width']
            img_name = 'portrait.png'
        elif orientation == 'landscape' and landscape_data:
            data = landscape_data
            aspect_ratio = data['mappingSize']['width'] / data['mappingSize']['height']
            img_name = 'landscape.png'
        else:
            continue

        mapping_size = data['mappingSize']
        items = data.get('items', [])

        # Get screen frame(s) for viewport
        screen_frames = data.get('screens', [])
        if not screen_frames:
            # Fallback to single gameScreenFrame
            gsf = data.get('gameScreenFrame')
            if gsf:
                screen_frames = [{'outputFrame': gsf}]

        # Compute viewport from screen frames
        if screen_frames:
            frames = [s.get('outputFrame', s.get('inputFrame', {})) for s in screen_frames if s]
            frames = [f for f in frames if f]  # Filter out empty
            if frames:
                viewport = compute_bounding_box(frames)
            else:
                viewport = data.get('gameScreenFrame')
        else:
            viewport = data.get('gameScreenFrame')

        # Overlay header
        lines.append(f'overlay{overlay_index}_name = "{orientation}"')
        lines.append(f'overlay{overlay_index}_overlay = "{img_name}"')
        lines.append(f'overlay{overlay_index}_full_screen = true')
        lines.append(f'overlay{overlay_index}_normalized = true')
        lines.append(f'overlay{overlay_index}_aspect_ratio = {aspect_ratio:.6f}')

        # Viewport
        if viewport:
            vp_x = viewport['x'] / mapping_size['width']
            vp_y = viewport['y'] / mapping_size['height']
            vp_w = viewport['width'] / mapping_size['width']
            vp_h = viewport['height'] / mapping_size['height']
            lines.append(f'overlay{overlay_index}_viewport = "{vp_x:.6f},{vp_y:.6f},{vp_w:.6f},{vp_h:.6f}"')

        lines.append('')

        # Convert items to descriptors
        desc_lines = []
        for i, item in enumerate(items):
            desc_lines.extend(convert_item_to_descriptor(item, mapping_size, i, overlay_index))

        # Add invisible rotation button
        other_orientation = 'landscape' if orientation == 'portrait' else 'portrait'
        if num_overlays > 1:
            rotate_idx = len(items)
            # Place at top center
            if orientation == 'portrait':
                desc_lines.append(f'overlay{overlay_index}_desc{rotate_idx} = "overlay_next,0.5,0.02,radial,0.04,0.02"')
            else:
                desc_lines.append(f'overlay{overlay_index}_desc{rotate_idx} = "overlay_next,0.5,0.04,radial,0.02,0.04"')
            desc_lines.append(f'overlay{overlay_index}_desc{rotate_idx}_next_target = "{other_orientation}"')
            num_descs = len(items) + 1
        else:
            num_descs = len(items)

        lines.append(f'overlay{overlay_index}_descs = {num_descs}')
        lines.append('')
        lines.extend(desc_lines)
        lines.append('')

        overlay_index += 1

    return '\n'.join(lines)


def convert_deltaskin(deltaskin_path, output_dir, devices=None, scale=3):
    """Convert a deltaskin file to RetroArch overlay(s)."""
    print(f"Converting: {deltaskin_path}")

    info, files = parse_deltaskin(deltaskin_path)

    skin_name = info.get('name', 'Unknown')
    game_type = info.get('gameTypeIdentifier', '')
    game_name = GAME_TYPE_NAMES.get(game_type, game_type.split('.')[-1] if game_type else 'Unknown')
    representations = info.get('representations', {})

    # Clean skin name for filesystem
    safe_name = skin_name.replace(' ', '_').replace('/', '_')

    if devices is None:
        devices = list(representations.keys())

    for device in devices:
        if device not in representations:
            print(f"  Skipping {device}: not found in skin")
            continue

        device_data = representations[device]
        display_type = get_display_type_preference(device_data)
        if not display_type:
            print(f"  Skipping {device}: no display types found")
            continue

        type_data = device_data[display_type]

        # Get available orientations
        portrait_data = type_data.get('portrait')
        landscape_data = type_data.get('landscape')

        orientations = []
        if portrait_data:
            orientations.append('portrait')
        if landscape_data:
            orientations.append('landscape')

        if not orientations:
            print(f"  Skipping {device}: no orientations found")
            continue

        # Create output directory
        device_output_dir = Path(output_dir) / f"{safe_name}_{game_name}_{device}"
        device_output_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Device: {device} ({display_type})")
        print(f"    Orientations: {', '.join(orientations)}")

        # Convert and save images
        for orientation in orientations:
            data = portrait_data if orientation == 'portrait' else landscape_data
            if not data:
                continue

            assets = data.get('assets', {})
            asset_name = assets.get('resizable') or assets.get('small') or assets.get('medium') or assets.get('large')

            if asset_name and asset_name in files:
                mapping_size = data['mappingSize']
                asset_bytes = files[asset_name]

                if asset_name.endswith('.pdf'):
                    print(f"    Converting {orientation} PDF to PNG...")
                    try:
                        img = convert_pdf_to_png(asset_bytes, mapping_size, scale)
                        if img:
                            img_path = device_output_dir / f'{orientation}.png'
                            img.save(str(img_path), 'PNG')
                            print(f"      Saved: {img_path}")
                    except Exception as e:
                        print(f"      Error converting PDF: {e}")
                elif asset_name.endswith('.png'):
                    # Copy PNG directly
                    img_path = device_output_dir / f'{orientation}.png'
                    img_path.write_bytes(asset_bytes)
                    print(f"      Copied: {img_path}")

        # Generate config
        config = generate_overlay_config(
            skin_name, device, orientations, portrait_data, landscape_data
        )
        config_path = device_output_dir / f"{safe_name}_{game_name}_{device}.cfg"
        config_path.write_text(config)
        print(f"    Config: {config_path}")

    print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Delta skins to RetroArch overlays'
    )
    parser.add_argument(
        'deltaskin',
        nargs='+',
        help='Path to .deltaskin file(s)'
    )
    parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--devices',
        nargs='+',
        help='Devices to convert (default: all). Options: iphone, ipad, tv'
    )
    parser.add_argument(
        '--scale',
        type=int,
        default=3,
        help='Image scale factor (default: 3 for retina)'
    )

    args = parser.parse_args()

    for deltaskin_path in args.deltaskin:
        if not os.path.exists(deltaskin_path):
            print(f"Error: File not found: {deltaskin_path}", file=sys.stderr)
            continue

        try:
            convert_deltaskin(
                deltaskin_path,
                args.output,
                devices=args.devices,
                scale=args.scale
            )
        except Exception as e:
            print(f"Error converting {deltaskin_path}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
