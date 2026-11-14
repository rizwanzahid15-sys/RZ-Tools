import pytest

from falcon_geom import (pair_bundles, bundle_spacing, bundles, home_run_label,
                    arrow_points, mask_rect)


def rounded(points):
    return sorted(tuple(round(v, 6) for v in p) for p in points)


def test_pair_bundles_inner_with_inner_any_order():
    # Review Focus 2: A lists the outer conduit first, B the inner first
    A = [((0, 2, 0), (10, 2, 0)), ((0, 1, 0), (10, 1, 0))]
    B = [((11, -10, 0), (11, 0, 0)), ((12, -10, 0), (12, 0, 0))]
    assert sorted(pair_bundles(A, B)) == [(0, 1), (1, 0)]


def test_pair_bundles_count_mismatch():
    pytest.raises(ValueError, pair_bundles, [((0, 0, 0), (1, 0, 0))], [])


def test_pair_bundles_parallel():
    A = [((0, 0, 0), (5, 0, 0))]
    B = [((0, 1, 0), (5, 1, 0))]
    pytest.raises(ValueError, pair_bundles, A, B)


def test_bundle_spacing():
    lines = [((0, 0, 0), (5, 0, 0)), ((0, 0.6, 0), (5, 0.6, 0)), ((0, 0.3, 0), (5, 0.3, 0))]
    assert bundle_spacing(lines) == pytest.approx(0.3)
    assert bundle_spacing(lines[:1]) == 0.0


def test_bundles_split_by_gap():
    # Review Focus 4
    lines = [((0, 0, 0), (5, 0, 0)), ((0, 0.2, 0), (5, 0.2, 0)),
             ((0, 8, 0), (5, 8, 0)), ((0, 8.2, 0), (5, 8.2, 0))]
    assert bundles(lines, 1.0) == [[0, 1], [2, 3]]


def test_bundles_no_overlap_split():
    lines = [((0, 0, 0), (5, 0, 0)), ((10, 0.2, 0), (15, 0.2, 0))]
    assert bundles(lines, 1.0) == [[0], [1]]


def test_bundles_different_directions_split():
    lines = [((0, 0, 0), (5, 0, 0)), ((0, 0, 0), (0, 5, 0))]
    assert bundles(lines, 1.0) == [[0], [1]]


def test_home_run_label_missing_parts():
    # Review Focus 5
    assert home_run_label("LP-1", "3,5") == "LP-1-3,5"
    assert home_run_label("LP-1", None) == "LP-1"
    assert home_run_label("LP-1", "") == "LP-1"
    assert home_run_label(None, "3") is None
    assert home_run_label("", "3") is None


def test_arrow_points():
    end, left, right = arrow_points((0, 0, 0), (10, 0, 0), 2, 0.5)
    assert end == pytest.approx((2, 0, 0))
    assert left[0] < 2 and right[0] < 2
    assert left[1] == pytest.approx(-right[1])
    assert abs(left[1]) == pytest.approx(0.25)


def test_mask_rect():
    pts = mask_rect((5, 5, 1), (1, 0, 0), 2, 0.4)
    assert rounded(pts) == rounded([(4, 4.8, 1), (6, 4.8, 1), (6, 5.2, 1), (4, 5.2, 1)])
