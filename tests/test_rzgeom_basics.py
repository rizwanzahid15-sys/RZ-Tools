import pytest

from rzgeom import (
    mm_to_ft, ft_to_mm, m_to_ft, vnorm, bend_angle_deg, is_bend,
    is_vertical, point_along, angle_between_deg,
)


def test_units():
    assert mm_to_ft(304.8) == 1.0
    assert m_to_ft(15) == pytest.approx(49.2126, abs=1e-4)
    assert ft_to_mm(1) == 304.8


def test_angle_between():
    assert angle_between_deg((1, 0, 0), (0, 2, 0)) == pytest.approx(90)
    assert angle_between_deg((1, 0, 0), (-3, 0, 0)) == pytest.approx(180)


def test_bend_angles():
    assert bend_angle_deg((1, 0, 0), (-1, 0, 0)) == pytest.approx(0)
    assert bend_angle_deg((1, 0, 0), (0, 1, 0)) == pytest.approx(90)
    assert is_bend(90) and is_bend(80)
    assert not is_bend(45) and not is_bend(0)


def test_vertical():
    assert is_vertical((0, 0, 1))
    assert not is_vertical((1, 0, 0.2))
    assert is_vertical((1, 0, 2))


def test_point_along():
    assert point_along((0, 0, 0), (10, 0, 0), 2.5) == pytest.approx((2.5, 0, 0))


def test_vnorm_zero_raises():
    pytest.raises(ValueError, vnorm, (0, 0, 0))
