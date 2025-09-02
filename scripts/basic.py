# Sample a random program from CSG2D/CSG3D

# Get the shader code. 

# -> Implies Get Code -> Apply basic RGB Material. 

# First goal -> render arbitary 3D CSG expression from Geolipi using SySL. 
# -> requirements: a) SDF map. b) Uniform, variable, operators handing, c) basic material, d) basic scene handling, e) render config handing.
# Just render the SDF -> Apply strict materials. 

# then we go for smooth material operators with a material eval in the second thing. 

# basically register geometry. 

import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader.shader_module import SMMap
import json
import numpy as np
from PIL import Image
from sysl.shader_vis.generate_shader_html import create_shader_html
from sysl.shader_vis.generate_shader_html import make_jupyter_compatible_html
from sysl.shader_vis.offline_render import render_sysl_shader_to_numpy

settings = {
    "render_mode": "v3",
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "castShadows": False,
    },
    "convert_uniforms_to_constants": True,
    "target": "ShaderToy"
}

# obj_1 = sls.MatSolidV2(solid_expr, sls.RGBMaterial((0., 1.0, 0.0)))
# obj_2 = sls.MatSolidV2(gls.Translate3D(solid_expr, (0.0, 0.5, 0.0)), sls.RGBMaterial((0., 0.0, 1.0)))
# obj_3 = sls.MatSolidV2(gls.Translate3D(solid_expr, (0.0, 0.25, 0.5)), sls.RGBMaterial((1.0, 0.0, 0.0)))

# expression = gls.SmoothUnion(obj_1, obj_2, (0.0,))
# # expression = sls.MatColorOnly(expression, obj_3)
# expression = sls.MatSmoothColorOnly(expression, obj_3, 
#     # (0.1,)
#     gls.UniformFloat((0.0,), (0.2,), (1.0,), "k")
#     )
# expression = sls.BoundedSolid(expression, gls.Cuboid3D((2.0, 2.0, 2.0)), )
solid_expr = gls.Sphere3D((0.5,))
expression = sls.MatSolidV3(solid_expr, sls.MaterialV3((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# expression = sls.MatSolidV3(solid_expr, sls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# expression = sls.MatSolidV3(solid_expr, sls.MatReference("name"))


solid_expr = gls.Sphere3D((1.5,))
expression = sls.MatSolidV3(solid_expr, 
                sls.NonEmissiveMaterialV3(
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
expression_2 = sls.MatSolidV3(solid_expr_2, 
                sls.MatReference("MatRustyPaint")
                # sls.MaterialV3(
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
obj_1 = sls.MatSolidV3(solid_expr, sls.NonEmissiveMaterialV3((0., 1.0, 0.0), (1.0,), (1.0,), (0.3,)))
obj_2 = sls.MatSolidV3(gls.Translate3D(solid_expr, (0.0, 0.5, 0.0)), sls.NonEmissiveMaterialV3((0., 0.0, 1.0), (1.0,), (1.0,), (0.3,)))
obj_3 = sls.MatSolidV3(gls.Translate3D(solid_expr, (0.0, 0.25, 0.5)), sls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (1.0,), (1.0,), (0.3,)))
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
# output = render_sysl_shader_to_numpy(shader_code, uniforms, size=(512, 512))
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


# object = sls.MatSolidV3(solid_expr, 
#         sls.MaterialV3((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# object = sls.MatSolidV3(solid_expr, 
#         sls.NonEmissiveMaterialV3((1.0, 0.0, 0.0), (0.0,), (0.0,), (0.0,)))
# object = sls.MatSolidV3(solid_expr, 
#         sls.MatReference("name"))


# scene_exprs = [sls.RegisterMaterial(object)]

# The way it should work -> we store a list of materials and mat references
# Separately construct the materials expression and codebook for it.





