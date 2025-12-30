"""
The evaluation of expressions to produce shader code that only sphere traces the generated geometry.
The resulting shader returns traced distance, primitive id, and normal for each pixel.
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
    COMBINATOR_TYPE,
    TRANSFORM_TYPE,
    POSITIONALMOD_TYPE,
    SDFMOD_TYPE,
)
import sysl.symbolic as sls
from .global_shader_context import GlobalShaderContext
from .local_shader_context import SCENE_EXPR_PROPS, LocalShaderContext, MATERIAL_EXPR_PROPS
from .param_evaluate import _inline_parse_param_from_expr
from .evaluate_singlepass import DEFAULT_BOUND_THRESHOLD, BOUNDED_SOLID_FLOAT_TEMPLATE, BOUNDED_SOLID_MIX_TEMPLATE
from .evaluate_singlepass import (eval_encoded_sdf_grid_3d as eval_encoded_sdf_grid_3d_v1)
from .evaluate_singlepass import rec_shader_eval
from .shader_templates import imfx_shaders as imfx_shaders
# V1 -> Just ray trace and get to the sdf value. 
# The 

@singledispatch
def rec_sdf_shader_eval(expression: gls.GLFunction | gls.GLExpr, global_sc) -> GlobalShaderContext:
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
    bounding_last_out = global_sc.local_sc.res_sdf_stack[-1]
    bounding_last_out_type, bounding_last_out_name = bounding_last_out
    global_sc.resolve_codebook()
    global_sc.pop_codebook()

    # Now these functions and the SM for them is inside. 
    # We now need the final custom -> which will combine these two. 
    pos_latest = global_sc.local_sc.pos_stack[-1]
    res_name = f"res_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    if bounding_last_out_type == "float":
        code_line = BOUNDED_SOLID_FLOAT_TEMPLATE.substitute(
            type=inner_type,
            res_name=res_name,
            bounding_name=bounding_name,
            inner_name=inner_name,
            pos_latest=pos_latest,
            bound_threshold=bound_threshold
        )
    else:
        code_line = BOUNDED_SOLID_MIX_TEMPLATE.substitute(
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
def eval_extrusion_prim_sdf(expression: gls.SimpleExtrusion3D, global_sc, *args, **kwargs) -> GlobalShaderContext:
    # basic version
    params = expression.args[1:]
    shader_params = _inline_parse_param_from_expr(expression, params, global_sc)
    # Add pos 2D
    orig_pos_3d = global_sc.local_sc.pos_stack.pop()
    global_sc.local_sc.pos_count += 1
    new_pos_2d = f"pos_{global_sc.local_sc.pos_count}"
    code_line = f"vec2 {new_pos_2d} = {orig_pos_3d}.xz;"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.pos_stack.append(new_pos_2d)
    # Go inside the innner expr
    inner_expr = expression.args[0] 
    global_sc = rec_sdf_shader_eval(inner_expr, global_sc, *args, **kwargs)
    res_type_2d, res_name_2d = global_sc.local_sc.res_sdf_stack.pop()
    
    primitive_param = ",".join(shader_params)
    func_name = expression.__class__.__name__
    sdf_3d_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    if len(shader_params) >= 1:
        code_line = f"float {sdf_3d_name} = {func_name}({orig_pos_3d}, {res_name_2d}, {primitive_param});"
    else:
        code_line = f"float {sdf_3d_name} = {func_name}({orig_pos_3d}, {new_pos_2d});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    
    prim_name = f"prim_{global_sc.prim_count}"
    global_sc.prim_count += 1
    code_line = f"vec2 {prim_name} = vec2({sdf_3d_name}, {global_sc.prim_count});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))

    return global_sc

@rec_sdf_shader_eval.register
def eval_rev_prim_sdf(expression: gls.SimpleRevolution3D, global_sc, *args, **kwargs) -> GlobalShaderContext:
    # basic version
    params = expression.args[1:]
    shader_params = _inline_parse_param_from_expr(expression, params, global_sc)
    primitive_param = ",".join(shader_params)
    # Add pos 2D
    orig_pos_3d = global_sc.local_sc.pos_stack.pop()
    global_sc.local_sc.pos_count += 1
    new_pos_2d = f"pos_{global_sc.local_sc.pos_count}"
    func_name = expression.__class__.__name__
    code_line = f"vec2 {new_pos_2d} = {func_name}({orig_pos_3d}, {primitive_param});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.pos_stack.append(new_pos_2d)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    # Go inside the innner expr
    inner_expr = expression.args[0] 
    global_sc = rec_shader_eval(inner_expr, global_sc, *args, **kwargs)
    prim_name = f"prim_{global_sc.prim_count}"
    global_sc.prim_count += 1
    res_type, sdf_name = global_sc.local_sc.res_sdf_stack.pop()
    code_line = f"vec2 {prim_name} = vec2({sdf_name}, {global_sc.prim_count});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))

    return global_sc


@rec_sdf_shader_eval.register
def eval_prim_sdf(expression: gls.Primitive3D, global_sc) -> GlobalShaderContext:
    
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
    global_sc.prim_count += 1
    code_line = f"vec2 {prim_name} = vec2({sdf_name}, {global_sc.prim_count});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.res_sdf_stack.append(("vec2", prim_name))

    return global_sc

@rec_sdf_shader_eval.register
def eval_prim_sdf(expression: gls.Primitive2D, global_sc) -> GlobalShaderContext:
    # No Prim Id difference for 2D outputs. 
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
    global_sc.local_sc.res_sdf_stack.append(("float", sdf_name))

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
    if isinstance(expression, gls.Modifier2D):
        new_pos_type = "vec2"
    else:
        new_pos_type = "vec3"
    if isinstance(expression, (TRANSFORM_TYPE, MACRO_TYPE, POSITIONALMOD_TYPE)):
        cur_pos = global_sc.local_sc.pos_stack.pop()
        global_sc.local_sc.pos_count += 1
        new_pos_count = global_sc.local_sc.pos_count
        new_pos = f"pos_{new_pos_count}"
        if shader_params:
            code_line = f"{new_pos_type} {new_pos} = {func_name}({cur_pos}, {shader_params});"
        else:
            code_line = f"{new_pos_type} {new_pos} = {func_name}({cur_pos});"
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