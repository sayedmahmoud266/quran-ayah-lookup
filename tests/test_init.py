"""
Basic tests for package initialization
"""
import pytest
from quran_ayah_lookup import __version__, __author__, __email__


def test_package_metadata():
    """Test that package metadata is correctly set."""
    assert __version__ == "0.0.1"
    assert __author__ == "Sayed Mahmoud"
    assert __email__ == "foss-support@sayedmahmoud266.website"


def test_package_import():
    """Test that the package can be imported successfully."""
    import quran_ayah_lookup
    assert quran_ayah_lookup is not None


def test_package_has_all_attribute():
    """Test that __all__ attribute exists."""
    import quran_ayah_lookup
    assert hasattr(quran_ayah_lookup, '__all__')
    assert isinstance(quran_ayah_lookup.__all__, list)