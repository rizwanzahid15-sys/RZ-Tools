import pytest

from falcon_geom import plan_pull_boxes


def S(length, vertical=False):
    return {"kind": "straight", "length": length, "vertical": vertical}


def B():
    return {"kind": "bend", "length": 0.3, "vertical": False}


def BOX():
    return {"kind": "box", "length": 0.0, "vertical": False}


def BRANCH():
    return {"kind": "branch", "length": 0.0, "vertical": False}


def approx(boxes):
    return [(i, pytest.approx(d)) for i, d in boxes]


def test_short_run_no_boxes():
    # Review Focus 4
    assert plan_pull_boxes([S(10)], 15, 2, 0.3) == []


def test_distance_every_15():
    assert plan_pull_boxes([S(40)], 15, 2, 0.3) == approx([(0, 15), (0, 30)])


def test_distance_carries_across_segments():
    assert plan_pull_boxes([S(10), S(10)], 15, 2, 0.3) == approx([(1, 5)])


def test_two_bends_box_after_second():
    run = [S(5), B(), S(3), B(), S(4)]
    assert plan_pull_boxes(run, 15, 2, 0.3) == approx([(4, 0.3)])


def test_riser_counts_as_first_bend():
    run = [S(5), B(), S(4)]
    assert plan_pull_boxes(run, 15, 2, 0.3, start_bends=1) == approx([(2, 0.3)])


def test_short_segment_after_bends_uses_mid():
    assert plan_pull_boxes([B(), B(), S(0.4)], 15, 2, 0.3) == approx([(2, 0.2)])


def test_existing_box_resets():
    assert plan_pull_boxes([S(10), BOX(), S(10)], 15, 2, 0.3) == []


def test_vertical_defers_to_next_horizontal():
    run = [S(10), S(6, True), S(5)]
    assert plan_pull_boxes(run, 15, 2, 0.3) == approx([(2, 0.3)])


def test_branch_stops_walk():
    assert plan_pull_boxes([S(10), BRANCH(), S(40)], 15, 2, 0.3) == []


def test_mark_inside_elbow_never_negative():
    # final review #1: spacing mark falls inside a bend
    run = [S(14.9), {"kind": "bend", "length": 0.5, "vertical": False}, S(10)]
    assert plan_pull_boxes(run, 15, 2, 0.3, end_margin=0.15) == approx([(2, 0.15)])


def test_no_box_exactly_at_run_end():
    # final review #1: a 30 m straight needs one box at 15, none at 30
    assert plan_pull_boxes([S(30)], 15, 2, 0.3, end_margin=0.15) == approx([(0, 15)])


def test_box_kept_off_segment_end():
    run = [S(10), S(5.05)]
    assert plan_pull_boxes(run, 15, 2, 0.3, end_margin=0.15) == approx([(1, 4.9)])
