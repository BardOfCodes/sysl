# Sample a random program from CSG2D/CSG3D

# Get the shader code. 

# -> Implies Get Code -> Apply basic RGB Material. 

# First goal -> render arbitary 3D CSG expression from Geolipi using CISL. 
# -> requirements: a) SDF map. b) Uniform, variable, operators handing, c) basic material, d) basic scene handling, e) render config handing.
# Just render the SDF -> Apply strict materials. 

# then we go for smooth material operators with a material eval in the second thing. 

# basically register geometry. 

import geolipi.symbolic as gls
import cisl.symbolic as csls
from cisl.shader.evaluate import evaluate_to_shader
from cisl.shader.shader_module import SMMap
import json
import numpy as np
from PIL import Image
from cisl.shader_vis.generate_shader_html import create_shader_html
from cisl.shader_vis.generate_shader_html import make_jupyter_compatible_html
from cisl.shader_vis.offline_render import render_cisl_shader_to_numpy

settings = {
    "render_mode": "v3",
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "castShadows": False,
    },
    "convert_uniforms_to_constants": True,
    "target": "ShaderToy"
}

# obj_1 = csls.MatSolidV2(solid_expr, csls.RGBMaterial((0., 1.0, 0.0)))
# obj_2 = csls.MatSolidV2(gls.Translate3D(solid_expr, (0.0, 0.5, 0.0)), csls.RGBMaterial((0., 0.0, 1.0)))
# obj_3 = csls.MatSolidV2(gls.Translate3D(solid_expr, (0.0, 0.25, 0.5)), csls.RGBMaterial((1.0, 0.0, 0.0)))

# expression = gls.SmoothUnion(obj_1, obj_2, (0.0,))
# # expression = csls.MatColorOnly(expression, obj_3)
# expression = csls.MatSmoothColorOnly(expression, obj_3, 
#     # (0.1,)
#     gls.UniformFloat((0.0,), (0.2,), (1.0,), "k")
#     )
# expression = csls.BoundedSolid(expression, gls.Cuboid3D((2.0, 2.0, 2.0)), )
solid_expr = gls.Sphere3D((0.5,))
expression = csls.MatSolidV3(solid_expr, csls.MaterialV3((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# expression = csls.MatSolidV3(solid_expr, csls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# expression = csls.MatSolidV3(solid_expr, csls.MatReference("name"))


solid_expr = gls.Sphere3D((1.5,))
expression = csls.MatSolidV3(solid_expr, 
                csls.NonEmissiveMaterialV3(
                    (1.0, 0.0, 0.0), 
                    # gls.UniformVec3((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0, 1.0), "albedo"),
                    # (0.0, 0.0, 0.0), 
                    # gls.UniformVec3((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "emissive"),
                    (1.0,), 
                    # gls.UniformFloat((0.0,), (0.7,), (1.0,), "roughness"),
                    (1.0,), 
                    # gls.UniformFloat((0.0,), (0.7,), (1.0,), "clearcoat"),
                    (0.3,)
                    # gls.UniformFloat((0.0,), (0.7,), (1.0,), "metallic"),
                    ))


solid_expr_2 = gls.Translate3D(gls.Cuboid3D((1.72, 0.2, 1.7)), (0.0, -1.0, 0.0))
expression_2 = csls.MatSolidV3(solid_expr_2, 
                csls.MatReference("MatRustyPaint")
                # csls.MaterialV3(
                #     (0.0, 0.0, 1.0), 
                #     # gls.UniformVec3((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0, 1.0), "albedo"),
                #     (0.0, 0.0, 0.0), 
                #     # gls.UniformVec3((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), "emissive"),
                #     (1.0,), 
                #     # gls.UniformFloat((0.0,), (0.7,), (1.0,), "roughness"),
                #     (1.0,), 
                #     # gls.UniformFloat((0.0,), (0.7,), (1.0,), "clearcoat"),
                #     (0.3,)
                #     # gls.UniformFloat((0.0,), (0.7,), (1.0,), "metallic"),
                #     )
                    )
expression = gls.Union(expression, expression_2)

solid_expr = gls.Sphere3D((0.5,))
obj_1 = csls.MatSolidV3(solid_expr, csls.NonEmissiveMaterialV3((0., 1.0, 0.0), (1.0,), (1.0,), (0.3,)))
obj_2 = csls.MatSolidV3(gls.Translate3D(solid_expr, (0.0, 0.5, 0.0)), csls.NonEmissiveMaterialV3((0., 0.0, 1.0), (1.0,), (1.0,), (0.3,)))
obj_3 = csls.MatSolidV3(gls.Translate3D(solid_expr, (0.0, 0.25, 0.5)), csls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (1.0,), (1.0,), (0.3,)))
expression = gls.SmoothUnion(obj_1, obj_2, (0.0,))

result = evaluate_to_shader(expression, settings, return_shader_context=True)
if len(result) == 3:
    shader_code, uniforms, shader_context = result
else:
    shader_code, uniforms = result
    shader_context = None

# print("=== DEBUG INFO ===")
# print("Uniforms:")
# if isinstance(uniforms, dict):
#     for name, info in uniforms.items():
#         print(f"  {name}: {info}")
# else:
#     print(f"  Uniforms type: {type(uniforms)}, value: {uniforms}")
# print("=== END DEBUG ===")

# Save the shader code to a file for examination
with open("generated_shader.frag", "w") as f:
    f.write(shader_code)
# print("Saved generated shader code to 'generated_shader.frag'")

# print("Rendering 3D CSG expression...")
# output = render_cisl_shader_to_numpy(shader_code, uniforms, size=(512, 512))
# print(f"Rendering completed successfully! Output shape: {output.shape}")

# Save the output as an image to verify it's working
# output_image = Image.fromarray(output)
# output_image.save("rendered_output.png")
# print("Saved rendered output to 'rendered_output.png'")

# You can also generate HTML if needed:
# html_code = create_shader_html(shader_code, uniforms, show_controls=True)
# with open("generated_shader.html", "w") as f:
#     f.write(html_code)
# print("Generated shader HTML with save render functionality!")


# object = csls.MatSolidV3(solid_expr, 
#         csls.MaterialV3((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# object = csls.MatSolidV3(solid_expr, 
#         csls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# object = csls.MatSolidV3(solid_expr, 
#         csls.MatReference("name"))


# scene_exprs = [csls.RegisterMaterial(object)]

# The way it should work -> we store a list of materials and mat references
# Separately construct the materials expression and codebook for it.





