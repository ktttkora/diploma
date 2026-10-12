"""
Text rendering helpers for screenshot annotation.

OpenCV's putText cannot render Cyrillic, so annotated text is drawn with
Pillow instead, which handles Unicode and line wrapping.
"""

from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


# Fonts that ship with Windows and include Cyrillic glyphs
FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/verdana.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    # Bundled with matplotlib, for non-Windows environments
    str(Path(__file__).resolve().parents[3]
        / "venv/Lib/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"),
]

_font_cache: dict = {}


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """
    Load a Cyrillic-capable font at the requested size.

    Args:
        size: Font size in pixels

    Returns:
        Pillow font object, falling back to the built-in bitmap font
    """
    if size in _font_cache:
        return _font_cache[size]

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                font = ImageFont.truetype(candidate, size)
                _font_cache[size] = font
                return font
            except OSError:
                continue

    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """
    Wrap text to fit a pixel width.

    Args:
        text: Text to wrap
        font: Font used for measurement
        max_width: Maximum line width in pixels

    Returns:
        List of lines
    """
    if not text:
        return []

    lines: List[str] = []
    current = ""

    for word in text.split():
        candidate = f"{current} {word}".strip()
        width = font.getbbox(candidate)[2]
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_text_block(
    image: np.ndarray,
    lines: List[Tuple[str, int, Tuple[int, int, int]]],
    padding: int = 10,
    line_spacing: int = 6,
    background: Optional[Tuple[int, int, int]] = None
) -> np.ndarray:
    """
    Draw a block of text onto an image.

    Args:
        image: OpenCV image in BGR order
        lines: Tuples of (text, font size, BGR colour)
        padding: Padding inside the block, in pixels
        line_spacing: Extra spacing between lines, in pixels
        background: Optional BGR colour for a solid block behind the text

    Returns:
        New image with the text drawn
    """
    if not lines:
        return image

    # Measure the block
    measured = []
    total_height = 0
    max_width = 0

    for text, size, _colour in lines:
        font = get_font(size)
        bbox = font.getbbox(text)
        line_height = bbox[3] - bbox[1]
        line_width = bbox[2]
        measured.append((text, font, line_height))
        total_height += line_height + line_spacing
        max_width = max(max_width, line_width)

    total_height = total_height - line_spacing + padding * 2
    block_width = max_width + padding * 2

    # Build the block, then paste it onto the image
    block = Image.new("RGB", (block_width, total_height), background or (0, 0, 0))
    draw = ImageDraw.Draw(block)

    y = padding
    for (text, font, line_height), (_, _, colour) in zip(measured, lines):
        # The block is drawn in RGB, so the BGR colour must be reversed
        draw.text((padding, y), text, font=font, fill=colour[::-1])
        y += line_height + line_spacing

    # Convert BGR -> RGB for Pillow. ascontiguousarray is required because
    # reversing channels yields negative strides, which Pillow rejects.
    rgb = np.ascontiguousarray(image[:, :, ::-1])
    result = Image.fromarray(rgb)
    result.paste(block, (0, 0))

    # Back to BGR for OpenCV
    return np.ascontiguousarray(np.array(result)[:, :, ::-1])
