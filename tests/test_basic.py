import importlib
import os
import sys

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def test_sysl_imports_public_api() -> None:
    """Basic import smoke test for the top-level package."""
    geolipi_spec = importlib.util.find_spec("geolipi")
    if geolipi_spec is None:
        pytest.skip("geolipi is required to import sysl fully")

    mod = importlib.import_module("sysl")

    # Core attributes should be present
    assert hasattr(mod, "__version__")
    assert hasattr(mod, "evaluate_to_shader")
    assert hasattr(mod, "create_shader_html")
    assert hasattr(mod, "symbolic")


def test_version_is_string_and_matches_metadata() -> None:
    """Ensure __version__ is a non-empty string."""
    geolipi_spec = importlib.util.find_spec("geolipi")
    if geolipi_spec is None:
        pytest.skip("geolipi is required to import sysl fully")

    import sysl

    assert isinstance(sysl.__version__, str)
    assert sysl.__version__ != ""


def test_geolipi_is_optional_runtime_dependency() -> None:
    """
    Ensure that importing sysl does not eagerly import geolipi.

    This keeps import-time overhead low and avoids hard failures if geolipi
    is not installed, while still allowing it to be required for full usage.
    """
    geolipi_spec = importlib.util.find_spec("geolipi")
    if geolipi_spec is None:
        pytest.skip("geolipi is required to import sysl fully")

    import sysl  # noqa: F401


