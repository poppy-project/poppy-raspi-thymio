"""Lane feature tests."""

import logging
from pathlib import Path

from pytest import approx
from pytest_bdd import given, parsers, scenario, then, when

from poppy.raspi_thymio.frame import Frame
from poppy.raspi_thymio.lane import Lane, LaneKind, LaneList


@scenario("lane.feature", "Lane detection")
def test_lane_detection():
    """Lane detection."""


@given(parsers.parse("image from file {image:S}"), target_fixture="frame")
def _(tmpdir, image):
    """image from file <image>."""
    image_file = Path("tests") / "data" / image

    frame = Frame(out_dir=tmpdir)
    frame.get_frame(image_file)
    return frame


@when("find all", target_fixture="lanes")
def _(frame):
    """find all."""
    lanes = LaneList.detect(frame)
    assert lanes
    return lanes


@then(parsers.parse("found all {lane:S}"))
def _(lane, lanes):
    """found all <lane>."""
    if lane == "None":
        return
    for example in lane.split(";"):
        az, *_ = (int(i) for i in example.split(","))
        assert any(
            candidate.kind == LaneKind.Center
            and candidate.azel[0] == approx(az, abs=10, rel=0.5)
            for candidate in lanes or []
        )
