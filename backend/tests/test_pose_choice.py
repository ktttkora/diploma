"""Which dancer is outlined, and whether a reference pose is the same shape."""

import numpy as np

from app.services.pose_service import choose_pose, pose_distance, same_dancer


def body(x: float, y: float, foot_y: float = 0.9):
    """A simple upright body whose chest sits at (x, y)."""
    landmarks = [{"x": x, "y": y, "visibility": 1.0} for _ in range(33)]
    landmarks[11] = {"x": x - 0.05, "y": y - 0.1, "visibility": 1.0}
    landmarks[12] = {"x": x + 0.05, "y": y - 0.1, "visibility": 1.0}
    landmarks[13] = {"x": x - 0.08, "y": y, "visibility": 1.0}
    landmarks[14] = {"x": x + 0.08, "y": y, "visibility": 1.0}
    landmarks[15] = {"x": x - 0.1, "y": y + 0.08, "visibility": 1.0}
    landmarks[16] = {"x": x + 0.1, "y": y + 0.08, "visibility": 1.0}
    landmarks[23] = {"x": x - 0.04, "y": y + 0.1, "visibility": 1.0}
    landmarks[24] = {"x": x + 0.04, "y": y + 0.1, "visibility": 1.0}
    landmarks[25] = {"x": x - 0.04, "y": y + 0.25, "visibility": 1.0}
    landmarks[26] = {"x": x + 0.04, "y": y + 0.25, "visibility": 1.0}
    for index in (27, 28, 29, 30, 31, 32):
        landmarks[index] = {"x": x, "y": foot_y, "visibility": 1.0}
    return landmarks


def test_anchor_selects_the_person_under_the_point() -> None:
    """The chest point picks the partner on the right, not the first detection."""
    left = body(0.3, 0.5)
    right = body(0.72, 0.5)
    chosen = choose_pose([left, right], anchor_x=0.74, anchor_y=0.5)
    assert chosen is right


def test_two_people_without_a_cue_are_not_assigned_by_order() -> None:
    """Detection order is not a gender. An unclear pair is left undrawn."""
    assert choose_pose(
        [body(0.3, 0.5), body(0.7, 0.5)],
        text="Сутулая спина",
        person="female",
    ) is None
    assert choose_pose(
        [body(0.3, 0.5), body(0.7, 0.5)],
        text="Сутулая спина",
        person="male",
    ) is None


def test_deep_sit_picks_the_wider_stance() -> None:
    """A lunge described for the woman outlines the dancer with feet apart."""
    standing = body(0.62, 0.5)
    standing[27] = {"x": 0.60, "y": 0.9, "visibility": 1.0}
    standing[28] = {"x": 0.64, "y": 0.9, "visibility": 1.0}
    lunging = body(0.45, 0.55)
    lunging[27] = {"x": 0.30, "y": 0.9, "visibility": 1.0}
    lunging[28] = {"x": 0.62, "y": 0.9, "visibility": 1.0}
    chosen = choose_pose(
        [standing, lunging],
        text="партнерша глубоко садится в левое бедро, провал в выпад",
        person="female",
    )
    assert chosen is lunging


def test_lighter_chest_wins_over_the_wider_stance() -> None:
    """Clothes decide the partner before a lunge cue can pick the man."""
    dark = body(0.30, 0.50)
    dark[27] = {"x": 0.10, "y": 0.9, "visibility": 1.0}
    dark[28] = {"x": 0.50, "y": 0.9, "visibility": 1.0}
    light = body(0.70, 0.50)
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    image[38:62, 58:82] = 255
    text = "партнерша глубоко садится в левое бедро, провал в выпад"
    assert choose_pose([dark, light], text=text, person="female", image=image) is light
    assert choose_pose([dark, light], text=text, person="male", image=image) is dark


def test_close_chests_in_different_clothes_stay_two_people() -> None:
    """A hold can put both chest estimates near each other."""
    dark = body(0.30, 0.50)
    light = body(0.38, 0.48)
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    image[180:212, 140:176] = 255
    assert same_dancer(dark, light) is True
    assert same_dancer(dark, light, image) is False
    text = "партнерша глубоко садится в левое бедро"
    assert choose_pose([dark, light], text=text, person="female", image=image) is light
    assert choose_pose([dark, light], text=text, person="male", image=image) is dark


def test_a_single_pose_in_the_wrong_clothes_is_not_drawn() -> None:
    """One dark chest is not the woman, and one light chest is not the man."""
    dancer = body(0.5, 0.5)
    dark = np.zeros((100, 100, 3), dtype=np.uint8)
    light = np.full((100, 100, 3), 255, dtype=np.uint8)
    assert choose_pose([dancer], text="потеря оси", person="female", image=dark) is None
    assert choose_pose([dancer], text="потеря оси", person="male", image=light) is None
    assert choose_pose([dancer], text="потеря оси", person="female", image=light) is dancer
    assert choose_pose([dancer], text="потеря оси", person="male", image=dark) is dancer


def test_kick_text_selects_the_raised_foot() -> None:
    """A high-kick description outlines the dancer whose foot is up."""
    standing = body(0.35, 0.5, foot_y=0.9)
    kicking = body(0.68, 0.5, foot_y=0.32)
    kicking[26] = {"x": 0.75, "y": 0.25, "visibility": 1.0}
    chosen = choose_pose([standing, kicking], text="высокий удар ногой, спина округлена")
    assert chosen is kicking


def test_identical_poses_are_close_and_a_kick_is_not() -> None:
    """A standing catalog pose is not a match for a kick."""
    standing = body(0.5, 0.5, foot_y=0.9)
    same = body(0.2, 0.4, foot_y=0.8)
    kicking = body(0.5, 0.5, foot_y=0.2)
    kicking[26] = {"x": 0.7, "y": 0.15, "visibility": 1.0}
    assert pose_distance(standing, same) < 0.4
    assert pose_distance(standing, kicking) > 0.4
