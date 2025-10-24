"""
# Idea: create multiple shader programs based on the type. 
# The first one stores where the intersection happens. And with what primitive. 
# The second one stores the material graph that it must execute given the distance. 
# Can introduce a third one to do DOF.
# Step one write the expr -> SDF shader program parser.
"""

import sys
import sympy as sp
from typing import Dict, Any, Tuple, Union as type_union
import geolipi.symbolic as gls
from string import Template
if sys.version_info >= (3, 11):
    from functools import singledispatch
else:
    from geolipi.torch_compute.patched_functools import singledispatch
import geolipi.symbolic as gls
from geolipi.symbolic.symbol_types import (
    MACRO_TYPE,
    MOD_TYPE,
    PRIM_TYPE,
    COMBINATOR_TYPE,
    TRANSFORM_TYPE,
    POSITIONALMOD_TYPE,
    SDFMOD_TYPE,
    HIGHER_PRIM_TYPE,
    COLOR_MOD,
    APPLY_COLOR_TYPE,
    SVG_COMBINATORS,
    UNOPT_ALPHA,
    EXPR_TYPE,
    SUPERSET_TYPE
)
import sysl.symbolic as sls
from .global_shader_context import GlobalShaderContext
from .local_shader_context import SCENE_EXPR_PROPS, LocalShaderContext,MATERIAL_EXPR_PROPS
from .param_evaluate import _inline_parse_param_from_expr
from .evaluate import DEFAULT_SETTINGS, DEFAULT_BOUND_THRESHOLD, BOUNDED_SOLID_TEMPLATE
from .evaluate import (eval_encoded_sdf_grid_3d as eval_encoded_sdf_grid_3d_v1, 
                       eval_prim_sdf as eval_prim_sdf_v1,
                       eval_sdf_grid_3d as eval_sdf_grid_3d_v1)
from .evaluate import rec_shader_eval
from .shader_templates import imfx_shaders as imfx_shaders
# V1 -> Just ray trace and get to the sdf value. 
# The 
posttrace_map = {
    "v1": "mainImage_post_trace_v1",
    "v2": "mainImage_post_trace_v2",
    "v3": "mainImage_post_trace_v3",
    "v4": "mainImage_post_trace_v4",
}
def evaluate_to_multipass_shader(expression: gls.GLFunction | gls.GLExpr, 
                       settings: Dict[str, Any] | None = None, 
                       return_shader_context: bool=False,
                       add_part_outline: bool=False) -> type_union[Tuple[str, Dict[str, Any]], Tuple[str, Dict[str, Any], Any]]:
    if settings is None:
        settings = DEFAULT_SETTINGS

    all_shader_bundles = []
    all_global_sc = []
    extract_vars = settings.get("extract_vars", False)
    set_to_ubo = settings.get("set_to_ubo", False)
    render_mode = settings.get("render_mode", "v3")

    # ================ FIRST PASS ================
    global_sc = GlobalShaderContext()

    if extract_vars:
        varnamed_expr, _, var_map_base = expression._get_varnamed_expr(exclude_uniforms=True)
        global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo)
        global_sc = rec_sdf_shader_eval(varnamed_expr, global_sc=global_sc)
    else:
        # How to use V3 here? ->
        global_sc = rec_sdf_shader_eval(expression, global_sc=global_sc)

    global_sc.resolve_codebook() # This will finins ahd add the function.
    # This should give a shader context with all the required modules. 
    # and then based on settings we will load the settings. 
    global_sc.add_shader_module("main_sdf_trace")

    shader_code = global_sc.emit_shader_code(settings, version="sdf_trace")
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    # Do not link textures for the first pass. 
    
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": {},
        "input_FBOs": [],
        "output_FBO": {"name": "distance_travelled", "width": 512, "height": 512, "type": "vec2"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)

    # ================ SECOND PASS ================

    if render_mode in ["v3", "v4"]:
        global_sc = GlobalShaderContext()
        global_sc.push_codebook("GEOM_EXPRESSION", SCENE_EXPR_PROPS)
        if extract_vars:
            varnamed_expr, _, var_map_base = expression._get_varnamed_expr(exclude_uniforms=True)
            global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo)
            global_sc = rec_sdf_shader_eval(varnamed_expr, global_sc=global_sc)
        else:
            global_sc = rec_sdf_shader_eval(expression, global_sc=global_sc)
        global_sc.resolve_codebook() # This will finins ahd add the function.
        global_sc.push_codebook("SCENE_EXPRESSION", SCENE_EXPR_PROPS)
        
    else:
        global_sc = GlobalShaderContext()

    if extract_vars:
        global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo)
        global_sc = rec_shader_eval(varnamed_expr, global_sc=global_sc)
    else:
        global_sc = rec_shader_eval(expression, global_sc=global_sc)
    global_sc.resolve_codebook() # This will finins ahd add the function.
    # This should give a shader context with all the required modules. 
    # and then based on settings we will load the settings. 
    if render_mode in ["v1", "v2"]:
        global_sc.add_shader_module(posttrace_map[render_mode])
    elif render_mode in ["v3", "v4"]:
        global_sc.resolve_material_stack(version=render_mode)
        global_sc.add_shader_module(posttrace_map[render_mode])
    else:
        raise ValueError(f"Invalid render mode: {render_mode}")
    
    shader_code = global_sc.emit_shader_code(settings, version="post_sdf_trace")
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    
    output_name = "intermediate_image"
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": uniforms,
        "textures": textures,
        "input_FBOs": [{"name": "distance_travelled", "width": 512, "height": 512, "type": "vec2"}],
        "output_FBO": {"name": output_name, "width": 512, "height": 512, "type": "vec4"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)
    
    # ================ THIRD PASS ================
    if add_part_outline:
        outline_amount = 1.0
        shader_code = imfx_shaders.part_outline.PART_OUTLINE_SHADER.substitute(outline_amount=outline_amount)
        input_FBOs = [{"name": "distance_travelled", "width": 512, "height": 512, "type": "vec2"},
            {"name": output_name, "width": 512, "height": 512, "type": "vec4"}]
    else:
        outline_amount = 1.0
        shader_code = imfx_shaders.basic_third_pass.BASIC_THIRD_PASS_SHADER.substitute()
        input_FBOs = [{"name": output_name, "width": 512, "height": 512, "type": "vec4"}]
    shader_bundle = {
        "shader_code": shader_code,
        "uniforms": {},
        "textures": {},
        "input_FBOs": input_FBOs,
        "output_FBO": {"name": "image", "width": 512, "height": 512, "type": "vec4"}
    }
    all_shader_bundles.append(shader_bundle)
    all_global_sc.append(global_sc)

    if return_shader_context:
        return all_shader_bundles, all_global_sc
    else:
        return all_shader_bundles
    


@singledispatch
def rec_sdf_shader_eval(expression: gls.GLFunction | gls.GLExpr, global_sc):
    raise NotImplementedError(f"No shader evaluation for {type(expression)}")



@rec_sdf_shader_eval.register
def eval_mat_solid(expression: type_union[sls.MatSolid, sls.MatSolidV3], global_sc) -> GlobalShaderContext:
    sdf_expr = expression.args[0]
    material_expr = expression.args[1]
    func_name = expression.__class__.__name__
    func_type = "vec2"
    assert isinstance(sdf_expr, gls.GLFunction) and isinstance(material_expr, gls.GLFunction), "SDF and Material must be GLFunctions"
    global_sc = rec_sdf_shader_eval(sdf_expr, global_sc)
    # From material only fetch index.
    # global_sc = rec_sdf_shader_eval(material_expr, global_sc)
    assert len(global_sc.local_sc.res_sdf_stack) > 0, "No SDF in the stack"
    res_type, final_sdf = global_sc.local_sc.res_sdf_stack.pop()  # type: ignore
    valid_types = ["float", func_type]
    assert res_type in valid_types, f"Invalid result type {res_type} for {func_name}"
    # final_material = global_sc.material_stack.pop()
    # Add it back to stack. 
    # This version only works in the basic version.
    res_name = f"res_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    global_sc.local_sc.add_codeline(f"{func_type} {res_name} = {final_sdf};")
    # global_sc.local_sc.add_dependency(func_name)
    # global_sc.add_shader_module(func_name)
    global_sc.local_sc.res_sdf_stack.append((func_type, res_name))
    return global_sc

@rec_sdf_shader_eval.register
def eval_bounded_solid(expression: sls.BoundedSolid, global_sc) -> GlobalShaderContext:
    func_name = expression.__class__.__name__
    sdf_expr = expression.args[0]
    bounding_expr = expression.args[1]
    if len(expression.args) > 2:
        bound_threshold = [expression.args[2]]
        bound_threshold = _inline_parse_param_from_expr(expression, tuple(bound_threshold), global_sc)
        bound_threshold = bound_threshold[0]
    else:
        bound_threshold = DEFAULT_BOUND_THRESHOLD
    # process and make function for bounding expr. 
    bounding_name = f"bounding_{global_sc.custom_func_count}"
    global_sc.custom_func_count += 1
    global_sc.push_codebook(bounding_name, SCENE_EXPR_PROPS)
    assert isinstance(bounding_expr, gls.GLFunction), "Bounding expression must be a GLFunction"
    global_sc = rec_sdf_shader_eval(bounding_expr, global_sc)
    global_sc.resolve_codebook()
    global_sc.pop_codebook()

    inner_name = f"inner_{global_sc.custom_func_count}"
    global_sc.custom_func_count += 1
    global_sc.push_codebook(inner_name, SCENE_EXPR_PROPS)
    assert isinstance(sdf_expr, gls.GLFunction), "SDF expression must be a GLFunction"
    global_sc = rec_sdf_shader_eval(sdf_expr, global_sc)
    inner_type, inner_sdf = global_sc.local_sc.res_sdf_stack[-1]  # type: ignore
    global_sc.resolve_codebook()
    global_sc.pop_codebook()

    # Now these functions and the SM for them is inside. 
    # We now need the final custom -> which will combine these two. 
    pos_latest = global_sc.local_sc.pos_stack[-1]
    res_name = f"res_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    code_line = BOUNDED_SOLID_TEMPLATE.substitute(
        type=inner_type,
        res_name=res_name,
        bounding_name=bounding_name,
        inner_name=inner_name,
        pos_latest=pos_latest,
        bound_threshold=bound_threshold
    )
    for line in code_line.split("\n"):
        global_sc.local_sc.add_codeline(line)
    global_sc.local_sc.add_dependency(bounding_name)
    global_sc.local_sc.add_dependency(inner_name)
    global_sc.local_sc.res_sdf_stack.append((inner_type, res_name))
    # append the bounding box to the stack. 
    return global_sc


@rec_sdf_shader_eval.register
def eval_prim_sdf(expression: PRIM_TYPE, global_sc) -> GlobalShaderContext:
    
    params = expression.args
    shader_params = _inline_parse_param_from_expr(expression, params, global_sc)
    # global_sc = PRIMITIVE_MAP[type(expression)](global_sc, *shader_params)
    box_param = ",".join(shader_params)
    cur_pos = global_sc.local_sc.pos_stack.pop()
    func_name = expression.__class__.__name__
    sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    if len(shader_params) >= 1:
        code_line = f"float {sdf_name} = {func_name}({cur_pos}, {box_param});"
    else:
        code_line = f"float {sdf_name} = {func_name}({cur_pos});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    prim_name = f"prim_{global_sc.prim_count}"
    code_line = f"vec2 {prim_name} = vec2({sdf_name}, {global_sc.prim_count});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.prim_count += 1
    global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))

    return global_sc
 
@rec_sdf_shader_eval.register
def eval_encoded_sdf_grid_3d(expression: type_union[sls.EncodedSDFGrid3D, sls.AABBEncodedSDFGrid3D], global_sc) -> GlobalShaderContext:
    # basic version
    return eval_encoded_sdf_grid_3d_v1(expression, global_sc)

@rec_sdf_shader_eval.register
def eval_sdf_grid_3d(expression: type_union[gls.SDFGrid3D, sls.RGBGrid3D], global_sc) -> GlobalShaderContext:
    # basic version
    raise NotImplementedError("Convert SDFGrid3D to EncodedSDFGrid3D first.")

@rec_sdf_shader_eval.register
def eval_sdf_combinator(expression: COMBINATOR_TYPE, global_sc) -> GlobalShaderContext:
    # it could be a argument tree, instead of this. 
    func_name = expression.__class__.__name__
    if isinstance(expression, (gls.SmoothUnion, gls.SmoothIntersection, gls.SmoothDifference, sls.MatSmoothColorOnly)):
        tree_branches = [arg for arg in expression.args[:-1]]
        param_list = [expression.args[-1]]
    else:
        tree_branches, param_list = [], []
        tree_branches = [arg for arg in expression.args]
    # the pos has to be copied
    cur_pos = global_sc.local_sc.pos_stack.pop()
    for child in tree_branches:
        global_sc.local_sc.pos_stack.append(cur_pos)
        assert isinstance(child, (gls.GLFunction, gls.GLExpr)), "Child must be a GLFunction or GLExpr"
        global_sc = rec_sdf_shader_eval(child,
            global_sc=global_sc,)
    n_children = len(tree_branches)
    # global_sc = COMBINATOR_MAP[type(expression)](global_sc, len(tree_branches), *param_list)

    children = [global_sc.local_sc.res_sdf_stack.pop() for _ in range(n_children)]
    # reverse the children
    children = children[::-1]
    child_names = [child[1] for child in children]
    child_types = [child[0] for child in children]
    # make sure they are all the same type.
    assert all(child_type == child_types[0] for child_type in child_types), "All children must be the same type"
    child_type = child_types[0]
    res_sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    res_sdf_names = ", ".join(child_names)
    if param_list: 
        shader_params = _inline_parse_param_from_expr(expression, tuple(param_list), global_sc)
        param_str = ", ".join(shader_params)
        res_sdf_names += f", {param_str}"

    code_line = f"{child_type} {res_sdf_name} = {func_name}({res_sdf_names});"
    global_sc.local_sc.add_codeline(code_line)
    input_format = (child_type, n_children)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name, input_format=input_format)
    global_sc.local_sc.res_sdf_stack.append((child_type, res_sdf_name))
    return global_sc


@rec_sdf_shader_eval.register
def eval_mod(expression: MOD_TYPE, global_sc) -> GlobalShaderContext:
    sub_expr = expression.args[0]
    params = expression.args[1:]
    shader_params = _inline_parse_param_from_expr(expression, params, global_sc)
    shader_params = ", ".join(shader_params)
    # This is a hack unclear how to deal with other types)
    func_name = expression.__class__.__name__
    assert isinstance(sub_expr, (gls.GLFunction, gls.GLExpr)), "Sub expression must be a GLFunction or GLExpr"
    if isinstance(expression, TRANSFORM_TYPE):
        cur_pos = global_sc.local_sc.pos_stack.pop()
        global_sc.local_sc.pos_count += 1
        new_pos_count = global_sc.local_sc.pos_count
        new_pos = f"pos_{new_pos_count}"
        code_line = f"vec3 {new_pos} = {func_name}({cur_pos}, {shader_params});"
        global_sc.local_sc.add_codeline(code_line)
        global_sc.local_sc.add_dependency(func_name)
        global_sc.add_shader_module(func_name)
        global_sc.local_sc.pos_stack.append(new_pos)
        if isinstance(expression, (gls.Scale3D, gls.Scale2D)):
        # For the case of scaling, adjust the outputs
            cur_res_pos = len(global_sc.local_sc.res_sdf_stack) - 1
            global_sc = rec_sdf_shader_eval(sub_expr, global_sc)
            new_res_pos = len(global_sc.local_sc.res_sdf_stack) - 1
            for res_pos in range(cur_res_pos, new_res_pos):
                res_type, res_name = global_sc.local_sc.res_sdf_stack[res_pos]
                if res_type == "float":
                    code_line = f"{res_name} = {res_name} * {shader_params}.x;"
                else:
                    code_line = f"{res_name}.x = {res_name}.x * {shader_params}.x;"
                global_sc.local_sc.add_codeline(code_line)
            return global_sc
        else:
            return rec_sdf_shader_eval(sub_expr, global_sc)
    elif isinstance(expression, POSITIONALMOD_TYPE):
        cur_pos = global_sc.local_sc.pos_stack.pop()
        global_sc.local_sc.pos_count += 1
        new_pos_count = global_sc.local_sc.pos_count
        new_pos = f"pos_{new_pos_count}"
        code_line = f"vec3 {new_pos} = {func_name}({cur_pos}, {shader_params});"
        global_sc.local_sc.add_codeline(code_line)
        global_sc.local_sc.add_dependency(func_name)
        global_sc.add_shader_module(func_name)
        global_sc.local_sc.pos_stack.append(new_pos)
        return rec_sdf_shader_eval(sub_expr, global_sc)
    elif isinstance(expression, SDFMOD_TYPE):
        # This should be treated like Comb
        global_sc = rec_sdf_shader_eval(sub_expr, global_sc)
        (res_type, cur_res) = global_sc.local_sc.res_sdf_stack.pop()  # type: ignore
        new_pos = f"res_{global_sc.local_sc.res_sdf_count}"
        global_sc.local_sc.res_sdf_count += 1
        code_line = f"{res_type} {new_pos} = {func_name}({cur_res}, {shader_params});"
        global_sc.local_sc.add_codeline(code_line)
        input_format = (res_type, 1)
        global_sc.local_sc.add_dependency(func_name)
        global_sc.add_shader_module(func_name, input_format=input_format)
        global_sc.local_sc.res_sdf_stack.append((res_type, new_pos))
        return global_sc
    else:
        raise NotImplementedError(f"Modifier {expression} not implemented")