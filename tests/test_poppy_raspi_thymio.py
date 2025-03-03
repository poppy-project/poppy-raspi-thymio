"""
Basic invocation test for poppy_raspi_thymio.
"""

from click.testing import CliRunner

from poppy.raspi_thymio.detector import main


def test_main():
    """
    Check that poppy_raspi_thymio's main function can be called.
    """
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert "Usage:" in result.output
    assert result.exit_code == 0
