"""Test the package import."""

import src


def test_version_when_package_imported_has_version() -> None:
    """Test that version is defined."""
    assert hasattr(src, "__version__")
    assert src.__version__ == "0.0.2"
