"""
Minimal SySL example: create a shaded sphere and generate an HTML viewer.

Run this script after installing:

    pip install sysl geolipi
"""

import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader import DEFAULT_SETTINGS, RenderMode, evaluate_to_shader
from sysl.shader_runtime import create_shader_html


def main() -> None:
    # Create simple geometry
    geometry = gls.Sphere3D((1.0,))

    # Define a basic V4 material (albedo, emissive, mrc)
    material = sls.MaterialV4(
        (1.0, 0.2, 0.1),
        (0.0, 0.0, 0.0),
        (0.5, 0.3, 0.0),
    )
    scene = sls.MatSolidV4(geometry, material)

    # Choose render settings
    settings = dict(DEFAULT_SETTINGS)
    settings["render_mode"] = RenderMode.V4

    # Generate shader and HTML
    shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)
    html_code = create_shader_html(shader_code, uniforms, textures, show_controls=True)

    output_path = "sysl_example.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_code)

    print(f"Wrote example viewer to {output_path}")


if __name__ == "__main__":
    main()

