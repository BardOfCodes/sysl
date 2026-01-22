"""
Multi-pass shader evaluation for SySL expressions.

Multi-pass rendering separates the rendering pipeline into distinct phases:
1. First pass: SDF ray tracing to compute intersection distance and primitive ID
2. Second pass: Material evaluation and shading at intersection points
3. Third pass: Screen-space post-processing (outlines, dithering, etc.)
4. Fourth pass (optional): Anti-aliasing downsampling

This approach enables more complex rendering effects and better performance
for certain scene configurations.
"""

import sympy as sp
from typing import Dict, Any, Tuple, Union as type_union
import geolipi.symbolic as gls
import sysl.symbolic as sls
from .global_shader_context import GlobalShaderContext
from .local_shader_context import SCENE_EXPR_PROPS
from .param_evaluate import _inline_parse_param_from_expr
from .shader_templates import imfx_shaders as imfx_shaders
from .shader_templates.common import RenderMode
from ..utils import recursive_sm_to_smg
from .evaluate_singlepass import rec_shader_eval
from .evaluate_shader_trace import rec_sdf_shader_eval

# Maps render mode to the corresponding post-trace shader module name
posttrace_map = {
    RenderMode.V1: "mainImage_post_trace_v1",
    RenderMode.V2: "mainImage_post_trace_v2",
    RenderMode.V3: "mainImage_post_trace_v3",
    RenderMode.V4: "mainImage_post_trace_v4",
    RenderMode.V5: "mainImage_post_trace_v5",
    RenderMode.V6: "mainImage_post_trace_v6",
}
def evaluate_multipass(expression: gls.GLFunction | gls.GLExpr, 
                       settings: Dict[str, Any] | None = None, 
                       return_shader_context: bool=False,
                       primitive_editing_mode: bool=False,
                       prim_expr: gls.GLFunction | gls.GLExpr | None = None,
                       map_first_pass_smg: bool=True,
                       post_process_shader: bool=None) -> type_union[Tuple[str, Dict[str, Any]], Tuple[str, Dict[str, Any], Any]]:

    all_shader_bundles = []
    all_global_sc = []
    render_mode = settings.get("render_mode", RenderMode.DEFAULT)
    extract_vars = settings.get("extract_vars", False)
    set_to_ubo = settings.get("set_to_ubo", False)
    set_param_to_texture = settings.get("set_param_to_texture", False)
    AA = settings.get("variables", {}).get("_AA", 1)

    if primitive_editing_mode:
        exclude_class_set = (gls.UniformVariable, sls.MaterialV4)
    else:
        exclude_class_set = (gls.UniformVariable, ) 
    # ================ FIRST PASS ================
    global_sc = GlobalShaderContext()
    if map_first_pass_smg:
        first_pass_expression = recursive_sm_to_smg(expression)
    else:
        first_pass_expression = expression
    if extract_vars:
        varnamed_expr, _, var_map_base = first_pass_expression._get_varnamed_expr(exclude_class_set=exclude_class_set)
        global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo, set_param_to_texture=set_param_to_texture)
        global_sc = rec_sdf_shader_eval(varnamed_expr, global_sc=global_sc)
    else:
        global_sc = rec_sdf_shader_eval(first_pass_expression, global_sc=global_sc)


    # Do not link textures for the first pass. 
    if primitive_editing_mode:
        # We need some uniforms. 
        gc_prim = GlobalShaderContext()
        gc_prim = rec_sdf_shader_eval(prim_expr, global_sc=gc_prim)
        global_sc.uniforms.update(gc_prim.uniforms)
        
    global_sc.resolve_codebook()
    global_sc.add_shader_module("main_sdf_trace", AA=AA)
    shader_code = global_sc.emit_shader_code(settings, version="sdf_trace")
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    
    cur_res = uniforms['resolution']['init_value']
    width = cur_res[0] * AA
    height = cur_res[1] * AA

    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": textures,
        "input_FBOs": [],
        "output_FBO": {"name": "distance_travelled", "width": width, "height": height, "type": "vec4"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)

    # ================ SECOND PASS ================

    if render_mode in [RenderMode.V3, RenderMode.V4, RenderMode.V5]:
        global_sc = GlobalShaderContext()
        global_sc.push_codebook("GEOM_EXPRESSION", SCENE_EXPR_PROPS)
        if extract_vars:
            varnamed_expr, _, var_map_base = expression._get_varnamed_expr(exclude_class_set=exclude_class_set)
            global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo, set_param_to_texture=set_param_to_texture)
            global_sc = rec_sdf_shader_eval(varnamed_expr, global_sc=global_sc)
        else:
            global_sc = rec_sdf_shader_eval(expression, global_sc=global_sc)
        global_sc.resolve_codebook()  # This will finish and add the function.
        global_sc.push_codebook("SCENE_EXPRESSION", SCENE_EXPR_PROPS)
    else:
        global_sc = GlobalShaderContext()

    if extract_vars:
        global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo, set_param_to_texture=set_param_to_texture)
        global_sc = rec_shader_eval(varnamed_expr, global_sc=global_sc)
    else:
        global_sc = rec_shader_eval(expression, global_sc=global_sc)
    if primitive_editing_mode:
        global_sc.uniforms.update(gc_prim.uniforms)
    global_sc.resolve_codebook() 
    
    if render_mode == RenderMode.V3:
        global_sc.resolve_material_stack(version=render_mode)
    global_sc.add_shader_module(posttrace_map[render_mode], AA=AA)
    
    shader_code = global_sc.emit_shader_code(settings, version="post_sdf_trace")
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    
    cur_res = uniforms['resolution']['init_value']
    width_2 = cur_res[0] * AA
    height_2 = cur_res[1] * AA
    
    output_name = "intermediate_image"
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": textures,
        "input_FBOs": [{"name": "distance_travelled", "width": width, "height": height, "type": "vec4"}],
        "output_FBO": {"name": output_name, "width": width_2, "height": height_2, "type": "vec4"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)
    
    # ================ THIRD PASS ================
    third_bundles, output_name = create_third_pass_shader_bundle(
        settings, width_2, height_2, output_name,
        post_process_shader=post_process_shader, AA=AA
    )
    all_shader_bundles.extend(third_bundles)

    # ================ FOURTH PASS (AA) ================
    aa_bundle = create_aa_pass_shader_bundle(width_2, height_2, AA, output_name)
    if aa_bundle:
        all_shader_bundles.append(aa_bundle)
    if return_shader_context:
        return all_shader_bundles, all_global_sc
    else:
        return all_shader_bundles


def create_third_pass_shader_bundle(settings: Dict[str, Any], 
                                     width: int, 
                                     height: int, 
                                     input_image_name: str,
                                     post_process_shader: list | None = None,
                                     AA: int = 1,
                                     include_distance_texture: bool = True) -> Tuple[Dict[str, Any], str]:
    """
    Create the third pass shader bundle for post-processing.
    
    Args:
        settings: Settings dictionary containing variables like outline_nhbd
        width: Width of the input/output FBOs
        height: Height of the input/output FBOs
        input_image_name: Name of the input image FBO (e.g., "intermediate_image")
        post_process_shader: List of post-process shader names, or None for basic pass
        AA: Anti-aliasing factor (1 = no AA)
        include_distance_texture: Whether to include distance_travelled as input FBO
        
    Returns:
        Tuple of (shader_bundle, output_name)
    """
    if post_process_shader is None:
        post_process_shader = []
    post_fx_args = dict(
        nhbd=settings.get("variables", {}).get("outline_nhbd", 1),
        dither_intensity_factor=settings.get("variables", {}).get("DITHER_INTENSITY_FACTOR", 0.5),
    )
    
    if AA > 1:
        output_name = "image_AA"
    else:
        output_name = "image"
    all_shader_bundles = []
        # Create input output seq:
    input_names = [input_image_name] + [f"interm_{i}" for i in range(len(post_process_shader) - 1)]
    output_names = [f"interm_{i}" for i in range(len(post_process_shader) - 1)] + [output_name]
    if post_process_shader:
        for ind, shader_name in enumerate(post_process_shader):
            cur_args = {x:y for x, y in post_fx_args.items()}
            cur_args["input_name"] = input_names[ind]
            if shader_name not in imfx_shaders.lookup_map:
                raise ValueError(f"Invalid post process shader: {shader_name}")
            shader_code = imfx_shaders.lookup_map[shader_name].substitute(**cur_args)
            if include_distance_texture:
                input_FBOs = [
                    {"name": "distance_travelled", "width": width, "height": height, "type": "vec4"},
                    {"name": input_names[ind], "width": width, "height": height, "type": "vec4"}
                ]
            else:
                input_FBOs = [{"name": input_names[ind], "width": width, "height": height, "type": "vec4"}]

            shader_bundle = {
                "shader_code": shader_code,
                "uniforms": {},
                "textures": {},
                "input_FBOs": input_FBOs,
                "output_FBO": {"name": output_names[ind], "width": width, "height": height, "type": "vec4"}
            }
            all_shader_bundles.append(shader_bundle)
    else:
        cur_args = {x:y for x, y in post_fx_args.items()}
        cur_args["input_name"] = input_image_name
        shader_code = imfx_shaders.basic_third_pass.BASIC_THIRD_PASS_SHADER.substitute(**cur_args)
        input_FBOs = [{"name": input_image_name, "width": width, "height": height, "type": "vec4"}]
        shader_bundle = {
            "shader_code": shader_code,
            "uniforms": {},
            "textures": {},
            "input_FBOs": input_FBOs,
            "output_FBO": {"name": output_name, "width": width, "height": height, "type": "vec4"}
        }
        all_shader_bundles.append(shader_bundle)
    
    return all_shader_bundles, output_name


def create_aa_pass_shader_bundle(width: int, 
                                  height: int, 
                                  AA: int,
                                  input_image_name: str = "image_AA") -> Dict[str, Any] | None:
    """
    Create the AA (anti-aliasing) pass shader bundle for downsampling.
    
    Args:
        width: Width of the input FBO (AA-scaled)
        height: Height of the input FBO (AA-scaled)
        AA: Anti-aliasing factor
        input_image_name: Name of the input image FBO (default "image_AA")
        
    Returns:
        shader_bundle if AA > 1, otherwise None
    """
    if AA <= 1:
        return None
    
    resolution = width // AA
    shader_code = imfx_shaders.fxaa.fxaa_shader(AA).substitute(resolution=resolution)
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": {},
        "textures": {},
        "input_FBOs": [{"name": input_image_name, "width": width, "height": height, "type": "vec4"}],
        "output_FBO": {"name": "image", "width": width // AA, "height": height // AA, "type": "vec4"}
    }
    
    return shader_bundle

