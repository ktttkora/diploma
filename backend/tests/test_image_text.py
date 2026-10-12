"""
Unit tests for Cyrillic text rendering.

OpenCV cannot draw Cyrillic, so these cover the Pillow-based helpers that
annotate screenshots.
"""

import numpy as np
import pytest

from app.utils.image_text import draw_text_block, get_font, wrap_text


def test_get_font_returns_usable_font():
    """Font loading returns an object that can measure text."""
    font = get_font(20)
    bbox = font.getbbox("Тест")
    assert bbox[2] > 0


def test_get_font_is_cached():
    """The same size returns the same cached font object."""
    assert get_font(18) is get_font(18)


def test_get_font_measures_cyrillic():
    """A Cyrillic string has a non-zero width."""
    font = get_font(16)
    assert font.getbbox("Слушайте бит")[2] > 0


def test_wrap_text_empty_string():
    """Empty input produces no lines."""
    assert wrap_text("", get_font(16), 400) == []


def test_wrap_text_single_line():
    """Short text stays on one line."""
    lines = wrap_text("короткий текст", get_font(16), 1000)
    assert lines == ["короткий текст"]


def test_wrap_text_splits_long_text():
    """Long text is broken into several lines."""
    text = "Слушайте бит музыки и старайтесь попадать шагом точно в удар"
    lines = wrap_text(text, get_font(16), 150)

    assert len(lines) > 1
    # No words are lost in the wrap
    assert " ".join(lines) == text


def test_wrap_text_keeps_long_word():
    """A word wider than the limit is still emitted."""
    lines = wrap_text("оченьдлинноесловобезпробелов", get_font(16), 20)
    assert lines == ["оченьдлинноесловобезпробелов"]


def test_draw_text_block_no_lines():
    """An empty line list returns the image unchanged."""
    image = np.zeros((100, 200, 3), dtype=np.uint8)
    result = draw_text_block(image, [])

    assert np.array_equal(result, image)


def test_draw_text_block_preserves_shape():
    """Drawing text keeps the image dimensions."""
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    result = draw_text_block(image, [("Шаг не в бит", 20, (255, 255, 255))])

    assert result.shape == image.shape


def test_draw_text_block_changes_pixels():
    """Drawing text actually modifies the image."""
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    result = draw_text_block(image, [("Шаг не в бит", 20, (255, 255, 255))])

    assert not np.array_equal(result, image)


def test_draw_text_block_returns_contiguous_array():
    """The result is a contiguous array, safe to hand to OpenCV."""
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    result = draw_text_block(image, [("Тест", 20, (255, 255, 255))])

    assert result.flags["C_CONTIGUOUS"]


def test_draw_text_block_does_not_mutate_input():
    """The caller's image is left untouched."""
    image = np.zeros((200, 400, 3), dtype=np.uint8)
    original = image.copy()

    draw_text_block(image, [("Тест", 20, (255, 255, 255))])

    assert np.array_equal(image, original)
