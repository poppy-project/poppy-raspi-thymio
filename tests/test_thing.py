"""Thing feature tests."""

import base64
import json
import logging
from pathlib import Path

from pytest import approx
from pytest_bdd import given, parsers, scenario, then, when

from poppy.raspi_thymio.frame import Frame
from poppy.raspi_thymio.thing import Thing, ThingKind, ThingList


@scenario("thing.feature", "Find all Things")
def test_find_all_things():
    """Find all Things."""


@scenario("thing.feature", "Find best Things")
def test_find_best_things():
    """Find best Things."""


@scenario("thing.feature", "Format Things")
def test_format_things():
    """Format Things."""


@given(parsers.parse("image from file {image:S}"), target_fixture="frame")
def _(tmpdir, image):
    """image from file <image>."""
    image_file = Path("tests") / "data" / image

    frame = Frame(out_dir=tmpdir)
    frame.get_frame(image_file)
    return frame


@when("find all", target_fixture="things")
def _(frame):
    """find all."""
    things = ThingList.detect(frame)
    assert things
    return things


@when("format", target_fixture="formatted")
def _(things):
    """format."""
    return things.format()


@when("sort best")
def _(things):
    """sort best."""
    things.update_targets()


@then(parsers.parse("format yields {balls:S} {cubes:S} {stars:S}"))
def _(formatted, balls, cubes, stars):
    """format yields <balls> <cubes> <stars>."""
    checks = {ThingKind.Ball: balls, ThingKind.Cube: cubes, ThingKind.Star: stars}
    for kind, todo in checks.items():
        if todo == "None":
            continue
        subset = [f for f in formatted if f["class"] == int(kind)]
        expected = json.loads(base64.b64decode(todo))
        for x, y in zip(expected, subset):
            assert approx(x["az"], rel=0.5) == y["az"]
            assert approx(x["el"], rel=0.5) == y["el"]
            assert x["class"] == y["class"]
            assert approx(x["color"], rel=0.5) == y["color"]
            assert approx(x["conf"], rel=0.5) == y["conf"]
            assert x["name"] == y["name"]
            assert approx(tuple(x["xyxy"]), rel=0.5) == tuple(y["xyxy"])


@then(parsers.parse("found all {balls:S} {cubes:S} {stars:S}"))
def _(things, balls, cubes, stars):
    """found all <balls> <cubes> <stars>."""
    checks = {ThingKind.Ball: balls, ThingKind.Cube: cubes, ThingKind.Star: stars}
    for kind, todo in checks.items():
        if todo == "None":
            continue
        for example in todo.split(";"):
            az, el, conf, *_ = (int(i) for i in example.split(","))
            assert any(
                candidate.kind == kind
                and candidate.azel == approx((az, el), abs=10, rel=0.5)
                and candidate.confidence * 100 == approx(conf, abs=10, rel=0.5)
                for candidate in things or []
            )


@then(parsers.parse("found best 1 {balls:S} {cubes:S} {stars:S}"))
def _(things, balls, cubes, stars):
    """found best 1 <balls> <cubes> <stars>."""
    checks = {ThingKind.Ball: balls, ThingKind.Cube: cubes, ThingKind.Star: stars}
    for kind, example in checks.items():
        if example == "None":
            continue
        az, el, conf, *_ = (int(i) for i in example.split(","))
        assert any(
            candidate.target
            and candidate.kind == kind
            and candidate.azel == approx((az, el), abs=10, rel=0.5)
            and candidate.confidence * 100 == approx(conf, abs=10, rel=0.5)
            for candidate in things or []
        )
