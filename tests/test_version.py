"""Test version and basic imports."""

from budjira import __version__


def test_version() -> None:
    """Test that version is defined and has expected format."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3  # major.minor.patch


def test_imports() -> None:
    """Test that main modules can be imported."""
    from budjira.cli import main  # noqa: F401
    from budjira.utils import errors  # noqa: F401

    assert True  # If we get here, imports worked
