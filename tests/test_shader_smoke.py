import importlib

import pytest


geolipi_sym = pytest.importorskip(
    "geolipi.symbolic",
    reason="geolipi is required for shader generation tests",
)


def _make_simple_scene():
    import sysl.symbolic as sls

    # Simple sphere geometry from GeoLiPI
    sphere = geolipi_sym.Sphere3D((1.0,))

    # Basic V4 material (albedo, emissive, mrc)
    material = sls.MaterialV4(
        (1.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.5, 0.3, 0.0),
    )

    return sls.MatSolidV4(sphere, material)


def test_evaluate_to_shader_singlepass_smoke() -> None:
    """End-to-end smoke test for shader generation."""
    from sysl.shader import DEFAULT_SETTINGS, RenderMode, evaluate_to_shader

    scene = _make_simple_scene()
    settings = dict(DEFAULT_SETTINGS)
    settings["render_mode"] = RenderMode.V4

    result = evaluate_to_shader(scene, mode="singlepass", settings=settings)

    # Depending on configuration, evaluate_to_shader may return a string
    # or a list/dict of shader information. We only assert it is non-empty.
    assert result


def test_shader_runtime_html_generation_smoke() -> None:
    """
    Verify that shader_runtime HTML generation works on a simple shader.

    This does not validate visual correctness, only that we can produce
    some HTML without raising errors.
    """
    from sysl.shader_runtime import create_shader_html

    # Minimal fake shader output compatible with create_shader_html
    frag_code = "void main() { gl_FragColor = vec4(1.0); }"
    uniforms = {}
    textures = {}

    html = create_shader_html(
        frag_code,
        uniforms,
        textures,
        title="Test Shader",
        show_controls=False,
    )

    assert isinstance(html, str)
    assert "<html" in html.lower()

