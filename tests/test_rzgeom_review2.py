"""Tests for the second final-review findings (batches 2-3)."""
import pytest

from rzgeom import dedupe_segments, snap_joints, route_points, upper_edges


def rounded(segs):
    return sorted(tuple(tuple(round(v, 6) for v in p) for p in s) for s in segs)


def test_dedupe_segments_either_direction():
    # review #6: same CAD polyline picked twice
    segs = [((0, 0, 0), (5, 0, 0)), ((5, 0, 0), (0, 0, 0)), ((5, 0, 0), (5, 5, 0)),
            ((0, 0, 0), (5.0000001, 0, 0))]
    assert dedupe_segments(segs, 0.001) == [((0, 0, 0), (5, 0, 0)), ((5, 0, 0), (5, 5, 0))]


def test_snap_joints_closes_small_gaps():
    # review #7: 3 mm gap between touching lines must close exactly
    segs = [((0, 0, 0), (5, 0, 0)), ((5.01, 0, 0), (9, 0, 0))]
    out = snap_joints(segs, [(0, 1, 1, 0)])
    assert out[0][1] == pytest.approx((5.005, 0, 0))
    assert out[1][0] == pytest.approx((5.005, 0, 0))
    assert out[0][0] == (0, 0, 0) and out[1][1] == (9, 0, 0)


def test_route_side_connector_ends_square_to_connector():
    # review #8: last leg must run straight into a side connector
    pts = route_points((0, 0, 3), (5, 5, 1), (-1, 0, 0), approach=0.5)
    assert pts == [(0, 0, 3), (0, 0, 1), pytest.approx((4.5, 5, 1)), (5, 5, 1)]


def test_route_top_connector_unchanged_with_approach():
    pts = route_points((0, 0, 3), (5, 5, 1), (0, 0, 1), approach=0.5)
    assert pts == [(0, 0, 3), (5, 5, 3), (5, 5, 1)]


def test_upper_edges_follow_upper_conduit():
    # review #1: redraw the upper conduit's edges over the mask
    edges = upper_edges((0, 0, 0), (0, 1, 0), 0.1, 2.0)
    assert rounded(edges) == rounded([((-0.1, -1, 0), (-0.1, 1, 0)), ((0.1, -1, 0), (0.1, 1, 0))])
