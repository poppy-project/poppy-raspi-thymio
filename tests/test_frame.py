"""Frame feature tests."""

from pathlib import Path

import numpy as np
from pytest_bdd import given, parsers, scenario, then, when

import poppy.raspi_thymio.colors as colors
from poppy.raspi_thymio.frame import Frame
from poppy.raspi_thymio.lane import Lane, LaneKind
from poppy.raspi_thymio.thing import Thing, ThingKind


@scenario("frame.feature", "Decorate things")
def test_decorate_things():
    """Decorate."""


@scenario("frame.feature", "Decorate lanes")
def test_decorate_lanes():
    """Decorate."""


@scenario("frame.feature", "Remap features")
def test_remap_features():
    """Remap features."""


@scenario("frame.feature", "Retrieve edges")
def test_retrieve_edges():
    """Retrieve edges."""


@scenario("frame.feature", "Retrieve grayscale")
def test_retrieve_grayscale():
    """Retrieve grayscale."""


@given("a camera image", target_fixture="frame")
def _(tmpdir):
    """a camera image."""
    image_file = Path("tests") / "data" / "mixed.jpeg"

    frame = Frame(out_dir=tmpdir)
    frame.get_frame(image_file)
    return frame


@given(parsers.parse("a camera image {image:S}"), target_fixture="frame")
def _(tmpdir, image):
    """a camera image."""
    image_file = Path("tests") / "data" / image

    frame = Frame(out_dir=tmpdir)
    frame.get_frame(image_file)
    return frame


@given(parsers.parse("a feature {xy:S}"), target_fixture="x_y")
def _(xy):
    """a feature <xy>."""
    return np.array(xy.split(",")).astype(int)


@given("a set of things", target_fixture="things")
def _():
    """a set of things."""
    things = [
        Thing(kind=ThingKind.Ball, xyxy=(21, 490, 72, 433), confidence=0.87),
        Thing(kind=ThingKind.Ball, xyxy=(292, 535, 358, 467), confidence=0.92, target=True),
        Thing(kind=ThingKind.Cube, xyxy=(294, 392, 342, 332), confidence=0.90),
        Thing(kind=ThingKind.Cube, xyxy=(435, 458, 501, 383), confidence=0.91, target=True),
        Thing(kind=ThingKind.Star, xyxy=(524, 573, 599, 499), confidence=0.77),
        Thing(kind=ThingKind.Star, xyxy=(152, 463, 210, 410), confidence=0.85, target=True),
    ]
    return things


@given("a set of lanes", target_fixture="lanes")
def _():
    """a set of lanes."""
    lanes = [
        Lane(
            xyxy=(250, 590, 395, 590),
            color=[(100, 100, 100), (0, 0, 0), (100, 100, 100)],
        ),
        Lane(xyxy=(424, 445, 450, 400), color=[(50, 50, 50), (0, 0, 0), (50, 50, 50)]),
    ]
    return lanes


@when("decorate things")
def _(frame, things):
    """decorate things."""
    frame.decorate(things, [])


@when("decorate lanes")
def _(frame, lanes):
    """decorate lanes."""
    frame.decorate([], lanes)


@when("get edges", target_fixture="edges")
def _(frame):
    """get edges."""
    return frame.xray


@when("get grayscale", target_fixture="grayscale")
def _(frame):
    """get grayscale."""
    return frame.gray


@when("remap edge feature", target_fixture="remap_edge")
def _(frame, x_y):
    """remap edge feature."""
    return frame.remap_xray(x_y)


@when("remap grayscale feature", target_fixture="remap_gray")
def _(frame, x_y):
    """remap grayscale feature."""
    return frame.remap_gray(x_y)


@then("decorated things are as expected")
def _(frame, things):
    """decorated things are as expected."""
    assert frame.color.size == (640, 640)
    for thing in things:
        x1, y1, x2, y2 = thing.xyxy
        y1, y2 = sorted((y1, y2))
        # Bounding box (corners)
        assert frame.color.getpixel((x1, y1))[:3] == colors.BR_YELLOW[:3]
        assert frame.color.getpixel((x2, y2))[:3] == colors.BR_YELLOW[:3]
        # Target
        if thing.target:
            assert frame.color.getpixel(thing.center)[:3] == colors.BR_GRAY[:3]


@then("decorated lanes are as expected")
def _(frame, lanes):
    """decorated lanes are as expected."""
    assert frame.color.size == (640, 640)
    for lane in lanes:
        # Lane
        assert frame.color.getpixel(lane.center)[:3] == colors.BR_CYAN[:3]


@then("edges is as expected")
def _(edges):
    """edges is as expected."""
    assert edges.shape == (320, 320)


@then("grayscale is as expected")
def _(grayscale):
    """grayscale is as expected."""
    assert grayscale.size == (640, 640)


@then(parsers.parse("remapped edge feature is {edge_xy}"))
def _(remap_edge, edge_xy):
    """remapped edge feature is correct."""
    assert remap_edge.tolist() == [int(x) for x in edge_xy.split(",")]


@then(parsers.parse("remapped grayscale feature is {gray_xy:S}"))
def _(remap_gray, gray_xy):
    """remapped grayscale feature is correct."""
    assert remap_gray.tolist() == [int(x) for x in gray_xy.split(",")]
