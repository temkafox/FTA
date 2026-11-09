import math

import pytest

from actpilot.tree_geometry import orbit_angle, orbit_point


@pytest.mark.parametrize(
    "index, count, degrees",
    [(0, 16, 0), (1, 16, 30), (2, 16, 45), (3, 16, 60), (7, 16, 150), (15, 16, 330),
     (4, 40, 40), (5, 40, 45), (6, 40, 50), (39, 40, 350), (1, 6, 60), (9, 72, 45)],
)
def test_orbit_angles_follow_skilltree_export(index, count, degrees):
    assert orbit_angle(index, count) == pytest.approx(math.radians(degrees))


def test_orbit_point_uses_game_angles():
    x, y = orbit_point(100.0, 200.0, 2, 1, [0, 82, 162], [1, 6, 16])

    assert x == pytest.approx(100 + 162 * math.sin(math.radians(30)))
    assert y == pytest.approx(200 - 162 * math.cos(math.radians(30)))
