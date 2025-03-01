"""DetectableList feature tests."""

import colorsys

from pytest_bdd import given, parsers, scenario, then, when

from poppy.raspi_thymio.detectable import Detectable, DetectableKind, DetectableList


# 0,10,30,2 is kind=0, xyxy=(10,20,20,10), color=(30,30,30), ttl=2
def make(spec: str):
    k, x, c, q, t, *_ = [int(i) for i in spec.split(",")]
    return Detectable(
        xyxy=(x, x + 10, x + 10, x),
        kind=DetectableKind(k),
        color=[int(i*255) for i in colorsys.hls_to_rgb(h=c / 360.0, l=0.5, s=1.0)],
        confidence=q / 10.0,
        ttl=t,
    )


@scenario("detectable-list.feature", "Merge thing lists")
def test_merge_thing_lists():
    """Merge thing lists."""


@given(
    parsers.parse("a list with one thing {initial_spec:S}"), target_fixture="current"
)
def _(initial_spec):
    """a list with one thing <initial_spec>."""
    return DetectableList(make(spec) for spec in initial_spec.split(";"))


@given(parsers.parse("a new list with one thing {new_spec:S}"), target_fixture="todo")
def _(new_spec):
    """a new list with one thing <new_spec>."""
    return DetectableList(make(spec) for spec in new_spec.split(";"))


@when("merge lists")
def _(current, todo):
    """merge lists."""
    current.merge(todo)


@then(parsers.parse("result is {expect_spec:S}"))
def _(expect_spec, current):
    """result is <expect_spec>."""
    expected = DetectableList(make(spec) for spec in expect_spec.split(";"))
    assert sorted(current) == sorted(expected)
