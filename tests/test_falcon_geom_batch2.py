import pytest

from falcon_geom import (project_distance, snap_end, joint_pairs, joint_kind,
                    line_intersection_xy, route_points)


def test_project_distance():
    assert project_distance((0, 0, 0), (10, 0, 0), (4, 3, 0)) == pytest.approx(4)
    assert project_distance((0, 0, 0), (10, 0, 0), (-2, 0, 0)) == 0
    assert project_distance((0, 0, 0), (10, 0, 0), (12, 0, 0)) == pytest.approx(10)


def test_snap_end():
    assert snap_end(10, 0.2, 0.3) == 0
    assert snap_end(10, 9.8, 0.3) == 1
    assert snap_end(10, 5, 0.3) is None


def test_joint_pairs():
    segs = [((0, 0, 0), (5, 0, 0)), ((5, 0, 0), (5, 5, 0)), ((9, 9, 0), (10, 9, 0))]
    assert joint_pairs(segs, 0.01) == [(0, 1, 1, 0)]


def test_joint_pairs_end_used_once():
    segs = [((0, 0, 0), (5, 0, 0)), ((5, 0, 0), (5, 5, 0)), ((5, 0, 0), (9, 0, 0))]
    pairs = joint_pairs(segs, 0.01)
    assert len(pairs) == 1


def test_joint_kind_collinear_is_union():
    # Review Focus 1
    assert joint_kind((1, 0, 0), (-1, 0, 0)) == "union"
    assert joint_kind((1, 0, 0), (1, 0.001, 0)) == "union"
    assert joint_kind((1, 0, 0), (0, 1, 0)) == "elbow"


def test_line_intersection_xy():
    assert line_intersection_xy((0, 0, 1), (2, 0, 1), (5, -3, 0), (5, -1, 0)) == pytest.approx((5, 0, 1))
    assert line_intersection_xy((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)) is None


def test_route_same_height():
    assert route_points((0, 0, 1), (5, 5, 1), (1, 0, 0)) == [(0, 0, 1), (5, 5, 1)]


def test_route_down_into_top_connector():
    assert route_points((0, 0, 3), (5, 5, 1), (0, 0, 1)) == [(0, 0, 3), (5, 5, 3), (5, 5, 1)]


def test_route_side_connector_vertical_first():
    # Review Focus 3
    assert route_points((0, 0, 3), (5, 5, 1), (-1, 0, 0)) == [(0, 0, 3), (0, 0, 1), (5, 5, 1)]
