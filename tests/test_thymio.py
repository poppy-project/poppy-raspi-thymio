"""
Basic presence test for Thymio.
"""

from poppy.raspi_thymio.thymio import Thymio


def test_thymio():
    """
    Check that Thymio can be instantiated.
    """
    thymio = Thymio(start=False)
    program = thymio.aseba_program()

    assert "var camera.detect" in program
    assert "var camera.thing" in program

    if thymio.client:
        thymio.node.stop()
        thymio.node.unlock()
        thymio.client.disconnect()
