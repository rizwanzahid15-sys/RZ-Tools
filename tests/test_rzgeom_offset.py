import math

import pytest

from rzgeom import required_rise, slope_run, offset_spans, dogleg_polyline


def test_rise_up():
    assert required_rise(0, 0.05, [(0, 0.05)], 0.1, True) == pytest.approx(0.2)


def test_rise_down():
    assert required_rise(0, 0.05, [(0, 0.05)], 0.1, False) == pytest.approx(-0.2)


def test_rise_already_clear():
    assert required_rise(1.0, 0.05, [(0, 0.05)], 0.1, True) == 0.0
    assert required_rise(-1.0, 0.05, [(0, 0.05)], 0.1, False) == 0.0


def test_rise_uses_highest_other():
    others = [(0, 0.05), (0.3, 0.05)]
    assert required_rise(0, 0.05, others, 0.1, True) == pytest.approx(0.5)


def test_slope_run_30():
    assert slope_run(0.2, 30) == pytest.approx(0.2 / math.tan(math.radians(30)))
    assert slope_run(-0.2, 30) == pytest.approx(slope_run(0.2, 30))


def test_spans_merge_close_crossings():
    spans = offset_spans(20, [(8, 0.2), (9, 0.2)], 0.5, 0.3)
    assert spans == [pytest.approx((7.3, 9.7))]


def test_spans_separate_far_crossings():
    spans = offset_spans(20, [(15, 0.2), (4, 0.2)], 0.5, 0.3)
    assert spans == [pytest.approx((3.3, 4.7)), pytest.approx((14.3, 15.7))]


def test_span_near_end_raises():
    # Review Focus 3
    pytest.raises(ValueError, offset_spans, 10, [(0.5, 0.2)], 0.5, 0.3)
    pytest.raises(ValueError, offset_spans, 10, [(9.5, 0.2)], 0.5, 0.3)


def test_dogleg_points():
    pts = dogleg_polyline((0, 0, 0), (10, 0, 0), [(4, 6)], 0.2, 0.5)
    expected = [(0, 0, 0), (4, 0, 0), (4.5, 0, 0.2), (5.5, 0, 0.2), (6, 0, 0), (10, 0, 0)]
    assert pts == [pytest.approx(p) for p in expected]
