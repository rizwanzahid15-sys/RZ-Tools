import math

import pytest

from falcon_geom import group_by_direction, nearest_end, plan_intersection, crossing_sin


def test_group_reversed_same():
    # Review Focus 1: a bundle drawn in mixed directions stays one group
    g = group_by_direction([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (1, 0.03, 0)])
    assert g == [[0, 1, 3], [2]]


def test_nearest_end():
    # Review Focus 2: start from whichever end is nearest the click
    assert nearest_end((0, 0, 0), (10, 0, 0), (9, 0.5, 0)) == 1
    assert nearest_end((0, 0, 0), (10, 0, 0), (1, 0, 3)) == 0


def test_plan_intersection_hit():
    t, u = plan_intersection((0, 0, 0), (10, 0, 0), (4, -5, 3), (4, 5, 3))
    assert (t, u) == pytest.approx((0.4, 0.5))


def test_plan_intersection_parallel():
    assert plan_intersection((0, 0, 0), (10, 0, 0), (0, 1, 0), (10, 1, 0)) is None


def test_plan_intersection_outside_segment():
    assert plan_intersection((0, 0, 0), (3, 0, 0), (4, -5, 0), (4, 5, 0)) is None


def test_crossing_sin():
    assert crossing_sin((1, 0, 0), (1, 1, 0)) == pytest.approx(math.sqrt(0.5))
