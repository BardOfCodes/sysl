import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader_runtime.generate_shader_html import create_shader_html, make_jupyter_compatible_html


settings = {
    "render_mode": "v1",
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "castShadows": False,
        "_AA": 1,
        "_RAYCAST_MAX_STEPS": 200,
    },
    "set_to_ubo": False,
    "export_params": False,

}
# Create basic shapes
sphere = gls.Sphere3D((1.0,))
material = sls.MaterialV1((2.0,))
scene_with_material = sls.MatSolidV1(sphere, material)

# Render
shader_code, uniforms, textures = evaluate_to_shader(scene_with_material, settings=settings)

with open("test.glsl", "w") as f:
    f.write(shader_code)

# TO visualize in a browser:
html_code = create_shader_html(shader_code, uniforms, textures, show_controls=True)
with open("test.html", "w") as f:
    f.write(html_code)
