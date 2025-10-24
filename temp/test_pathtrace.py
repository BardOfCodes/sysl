import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader.shader_module import SMMap
from IPython.display import display, HTML
from sysl.shader_vis.generate_shader_html import create_shader_html, make_jupyter_compatible_html

settings = {
    "render_mode": "v3",
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "castShadows": False,
        "_AA": 1,
        "_RAYCAST_MAX_STEPS": 200,
    },
    "set_to_ubo": False,
    "export_params": False,
    # "convert_uniforms_to_constants": True,
    # "target": "ShaderToy"

}
import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader_vis.generate_shader_html import create_shader_html, make_jupyter_compatible_html
from IPython.display import display, HTML

# Create basic shapes
sphere = gls.Sphere3D((1.0,))
box = gls.Cuboid3D((2, 0.01, 2,))

# Combine with operations
scene = gls.Translate3D(
    gls.Union(gls.Scale3D(sphere, (0.5, 0.5, 0.5)), box),
    (0.5, 0.5, 0)
)

# Assign materials
material = sls.NonEmissiveMaterialV3(
    (1.0, 0.0, 0.0), 
    (1.0,), (1.0,), (0.3,)
)

# material = sls.SMPLMaterial((2.5,))
# material = sls.RGBMaterial((1.0, 0.0, 0.0))

scene_with_material = sls.MatSolidV3(scene, material)

# Render
shader_code, uniforms, textures = evaluate_to_shader(scene_with_material, settings=settings)

with open("test.glsl", "w") as f:
    f.write(shader_code)

if not settings.get("target", "GLSL") == "ShaderToy":
    # TO visualize in a browser:
    html_code = create_shader_html(shader_code, uniforms, textures, show_controls=True)
    with open("test.html", "w") as f:
        f.write(html_code)

    # To visualize inline in jupyter notebook:
    # jupy_wrapper_html = make_jupyter_compatible_html(html_code)
    # display(HTML(jupy_wrapper_html))
    # Now do the multipass version
from sysl.shader.evaluate_multipass import evaluate_to_multipass_shader
from sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html

shader_bundles = evaluate_to_multipass_shader(scene_with_material, settings=settings)

with open("test_1.glsl", "w") as f:
    f.write(shader_bundles[0]['shader_code'])
with open("test_2.glsl", "w") as f:
    f.write(shader_bundles[1]['shader_code'])

if not settings.get("target", "GLSL") == "ShaderToy":
    # TO visualize in a browser:
    html_code = create_multibuffer_shader_html(shader_bundles, show_controls=True)
    with open("/sensei-fs-3/users/aganeshan/projects/mpspy/temp/test.html", "w") as f:
        f.write(html_code)

    # To visualize inline in jupyter notebook:
    jupy_wrapper_html = make_jupyter_compatible_html(html_code)
    display(HTML(jupy_wrapper_html))