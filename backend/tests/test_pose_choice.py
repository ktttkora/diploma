"""Which dancer is outlined, and whether a reference pose is the same shape."""

from app.services.pose_service import choose_pose, pose_distance
from app.services.visualization_service import highlighted_connections


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


def test_female_without_anchor_skips_the_prominent_dancer() -> None:
    """Without a point, the woman is the partner MediaPipe did not lock onto."""
    prominent = body(0.3, 0.5)
    partner = body(0.7, 0.5)
    chosen = choose_pose([prominent, partner], text="Сутулая спина", person="female")
    assert chosen is partner


def test_male_without_anchor_keeps_the_prominent_dancer() -> None:
    """Without a point, the man stays the body MediaPipe saw first."""
    prominent = body(0.3, 0.5)
    partner = body(0.7, 0.5)
    chosen = choose_pose([prominent, partner], text="Сутулая спина", person="male")
    assert chosen is prominent


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


def test_back_and_leg_words_mark_those_bones() -> None:
    """The words in the error pick the bones drawn in the accent colour."""
    marked = highlighted_connections("Корпус завален, высокий удар ногой")
    assert (11, 23) in marked
    assert (23, 25) in marked
    assert (11, 13) not in marked
