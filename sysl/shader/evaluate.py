"""Convert from SySL Expression to shader code."""

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
from .local_shader_context import SCENE_EXPR_PROPS, MATERIAL_EXPR_PROPS, MATERIAL_EXPR_PROPS_V4
from .param_evaluate import _inline_parse_param_from_expr

DEFAULT_BOUND_THRESHOLD = 0.02

DEFAULT_SETTINGS = {
    "render_mode": "v4",
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "_RAYCAST_MAX_STEPS": 200,
        "_RAYCAST_CONSERVATIVE_STEPPING_RATE": 0.99,
        "_AA": 1,   
        "castShadows": True,
    },
    "extract_vars": False,
    "use_define_vars": False
}
main_image_map = {
    "v1": "mainImage_v1",
    "v2": "mainImage_v2",
    "v3": "mainImage_v3",
    "v4": "mainImage_v4",
}

# V1 -> Just a single expression.
def evaluate_to_shader(expression: gls.GLFunction | gls.GLExpr, 
                       settings: Dict[str, Any] | None = None, 
                       return_shader_context: bool=False) -> type_union[Tuple[str, Dict[str, Any]], Tuple[str, Dict[str, Any], Any]]:
    if settings is None:
        settings = DEFAULT_SETTINGS
    extract_vars = settings.get("extract_vars", False)
    set_to_ubo = settings.get("set_to_ubo", False)
    set_param_to_texture = settings.get("set_param_to_texture", False)
    render_mode = settings.get("render_mode", "v4")
    if set_param_to_texture:
        raise NotImplementedError("Setting parameters to texture is not implemented yet for single pass.")

    global_sc = GlobalShaderContext()
    # How to use V3 here? ->
    if extract_vars:
        varnamed_expr, _, var_map_base = expression._get_varnamed_expr(exclude_uniforms=True)
        global_sc.create_var_map(var_map_base, set_to_ubo=set_to_ubo)
        global_sc = rec_shader_eval(varnamed_expr, global_sc=global_sc)
    else:
        global_sc = rec_shader_eval(expression, global_sc=global_sc)
    global_sc.resolve_codebook() # This will finins ahd add the function.
    # This should give a shader context with all the required modules. 
    # and then based on settings we will load the settings. 

    if render_mode in ["v1", "v2"]:
        global_sc.add_shader_module(main_image_map[render_mode])
    elif render_mode in ["v3", "v4"]:
        global_sc.resolve_material_stack(version=render_mode)
        global_sc.add_shader_module(main_image_map[render_mode])
    else:
        raise ValueError(f"Invalid render mode: {render_mode}")
    
    shader_code = global_sc.emit_shader_code(settings)
    uniforms = global_sc.get_uniforms()
    textures = global_sc.get_textures()
    if return_shader_context:
        return shader_code, uniforms, textures, global_sc
    else:
        return shader_code, uniforms, textures


@singledispatch
def rec_shader_eval(expression: gls.GLFunction | gls.GLExpr, global_sc, *args, **kwargs):
    raise NotImplementedError(f"No shader evaluation for {type(expression)}")

solid_to_type_map = {
    sls.MatSolidV1: "vec2",
    sls.MatSolidV2: "vec4",
    sls.MatSolidV3: "vec2", # Store Reference ID.
    sls.MatSolidV4: "MATPoint", # Store Reference ID.
}

@rec_shader_eval.register
def eval_mat_solid(expression: sls.MatSolid, global_sc, *args, **kwargs) -> GlobalShaderContext:
    sdf_expr = expression.args[0]
    material_expr = expression.args[1]
    func_name = expression.__class__.__name__
    func_type = solid_to_type_map[type(expression)]
    assert isinstance(sdf_expr, gls.GLFunction) and isinstance(material_expr, gls.GLFunction), "SDF and Material must be GLFunctions"
    cur_pos = global_sc.local_sc.pos_stack[-1]
    global_sc = rec_shader_eval(sdf_expr, global_sc)
    global_sc = rec_shader_eval(material_expr, global_sc, cur_pos=cur_pos)
    assert len(global_sc.local_sc.res_sdf_stack) > 0, "No SDF in the stack"
    res_type, final_sdf = global_sc.local_sc.res_sdf_stack.pop()  # type: ignore
    valid_types = ["float", func_type]
    assert res_type in valid_types, f"Invalid result type {res_type} for {func_name}"
    final_material = global_sc.material_stack.pop()
    # Add it back to stack. 
    # This version only works in the basic version.
    res_name = f"res_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    global_sc.local_sc.add_codeline(f"{func_type} {res_name} = {func_name}({final_sdf}, {final_material});")
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    global_sc.local_sc.res_sdf_stack.append((func_type, res_name))
    return global_sc

# For V3, allow graph for material local coordinate frame.

@rec_shader_eval.register
def eval_mat_solid_v3(expression: sls.MatSolidV3, global_sc, *args, **kwargs) -> GlobalShaderContext:
    sdf_expr = expression.args[0]
    material_expr = expression.args[1]
    func_name = expression.__class__.__name__
    func_type = solid_to_type_map[type(expression)]
    assert isinstance(sdf_expr, gls.GLFunction) and isinstance(material_expr, gls.GLFunction), "SDF and Material must be GLFunctions"
    global_sc = rec_shader_eval(sdf_expr, global_sc)
    # Here we change it. 

    mat_name = f"mat_{global_sc.material_count}"
    mat_function_name = f"{mat_name}_func"
    mat_index = global_sc.material_count
    global_sc.push_codebook(mat_function_name, MATERIAL_EXPR_PROPS)

    global_sc = rec_shader_eval(material_expr, global_sc)

    global_sc.resolve_codebook()
    global_sc.pop_codebook()
    code_line = f"float {mat_name} = {float(mat_index)};"
    global_sc.material_count += 1
    global_sc.local_sc.add_codeline(code_line)
    global_sc.material_stack.append(mat_name)
    global_sc.material_registry.update({mat_function_name: mat_index})

    
    assert len(global_sc.local_sc.res_sdf_stack) > 0, "No SDF in the stack"
    res_type, final_sdf = global_sc.local_sc.res_sdf_stack.pop()  # type: ignore
    valid_types = ["float", func_type]
    assert res_type in valid_types, f"Invalid result type {res_type} for {func_name}"
    final_material = global_sc.material_stack.pop()
    # Add it back to stack. 
    # This version only works in the basic version.
    res_name = f"res_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    global_sc.local_sc.add_codeline(f"{func_type} {res_name} = {func_name}({final_sdf}, {final_material});")
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    global_sc.local_sc.res_sdf_stack.append((func_type, res_name))
    return global_sc


BOUNDED_SOLID_TEMPLATE = Template("""
${type} ${res_name};
float ${res_name}_sdf = ${bounding_name}(${pos_latest});
if (${res_name}_sdf < ${bound_threshold}) {
    ${res_name} = ${inner_name}(${pos_latest});
} else {
    ${res_name} = ${type}(-1.0);
    ${res_name}.x = ${res_name}_sdf;
}
""")


@rec_shader_eval.register
def eval_bounded_solid(expression: sls.BoundedSolid, global_sc, *args, **kwargs) -> GlobalShaderContext:
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
    global_sc = rec_shader_eval(bounding_expr, global_sc)
    global_sc.resolve_codebook()
    global_sc.pop_codebook()

    inner_name = f"inner_{global_sc.custom_func_count}"
    global_sc.custom_func_count += 1
    global_sc.push_codebook(inner_name, SCENE_EXPR_PROPS)
    assert isinstance(sdf_expr, gls.GLFunction), "SDF expression must be a GLFunction"
    global_sc = rec_shader_eval(sdf_expr, global_sc)
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


@rec_shader_eval.register
def eval_prim_sdf(expression: PRIM_TYPE, global_sc, *args, **kwargs) -> GlobalShaderContext:
    # basic version
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


@rec_shader_eval.register
def eval_encoded_sdf_grid_3d(expression: type_union[sls.EncodedSDFGrid3D, sls.AABBEncodedSDFGrid3D], global_sc, *args, **kwargs) -> GlobalShaderContext:
    # basic version
    params = expression.args
    shader_params = _inline_parse_param_from_expr(expression, params, global_sc)
    sdf_texture_name = shader_params[0]
    b64_data = shader_params[1]
    tex_shape = [int(x) for x in list(params[2])] # shader_params will have it a vec2
    tex_dtype = shader_params[3]
    bound_threshold = shader_params[4]
    cur_pos = global_sc.local_sc.pos_stack.pop()
    func_name = expression.__class__.__name__
    sdf_name = f"sdf_{global_sc.local_sc.res_sdf_count}"
    global_sc.local_sc.res_sdf_count += 1
    custom_func_name = f"sdf_grid_3d_{global_sc.custom_func_count}"
    global_sc.custom_func_count += 1
    # GLSL code for sphere (sphere_param[0] is the vec4 sphere parameters)
    code_line = f"float {sdf_name} = {custom_func_name}({cur_pos});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    if isinstance(expression, sls.AABBEncodedSDFGrid3D):
        bbox_origin = shader_params[5]
        bbox_scale = shader_params[6]
        global_sc.add_shader_module(func_name, 
            function_name=custom_func_name, 
            sdf_texture_name=sdf_texture_name,
            bound_threshold=bound_threshold,
            bbox_origin=bbox_origin,
            bbox_scale=bbox_scale
        )
    else:
        global_sc.add_shader_module(func_name, 
            function_name=custom_func_name, 
            sdf_texture_name=sdf_texture_name,
            bound_threshold=bound_threshold
        )
    global_sc.local_sc.res_sdf_stack.append(("float", sdf_name))
    # Register the texture info
    texture_data = {'name': sdf_texture_name, 
                    'data_b64': b64_data,
                    'shape': tex_shape, 
                    'dtype': tex_dtype,
                    }
    global_sc.add_texture(texture_data)
    return global_sc



@rec_shader_eval.register
def eval_sdf_grid_3d(expression: type_union[gls.SDFGrid3D, sls.RGBGrid3D], global_sc, *args, **kwargs) -> GlobalShaderContext:
    # basic version
    raise NotImplementedError("Convert Grid3D to EncodedGrid first.")

@rec_shader_eval.register
def eval_sdf_combinator(expression: COMBINATOR_TYPE, global_sc, *args, **kwargs) -> GlobalShaderContext:
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
        global_sc = rec_shader_eval(child,
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


@rec_shader_eval.register
def eval_mod(expression: MOD_TYPE, global_sc, *args, **kwargs) -> GlobalShaderContext:
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
            global_sc = rec_shader_eval(sub_expr, global_sc)
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
            return rec_shader_eval(sub_expr, global_sc)
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
        return rec_shader_eval(sub_expr, global_sc)
    elif isinstance(expression, SDFMOD_TYPE):
        # This should be treated like Comb
        global_sc = rec_shader_eval(sub_expr, global_sc)
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
    

mat_to_type_map = {
    sls.SMPLMaterial: "float",
    sls.RGBMaterial: "vec3",
    sls.MaterialV3: "float",
    sls.NonEmissiveMaterialV3: "float",
    sls.MatReference: "float",
    sls.EncodedRGBGrid3D: "float",
    sls.MaterialV4: "MATPoint",
    sls.SMPLMaterialV4: "MATPoint",
}

@rec_shader_eval.register
def eval_smpl_material(expression: sls.Material, global_sc, *args, **kwargs) -> GlobalShaderContext:
    shader_params = expression.args[:]
    processed_params = _inline_parse_param_from_expr(expression, shader_params, global_sc)
    mat_name = f"mat_{global_sc.material_count}"
    global_sc.material_count += 1
    code_line = f"{mat_to_type_map[type(expression)]} {mat_name} = {processed_params[0]};"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.material_stack.append(mat_name)
    return global_sc

mat_v3_template = Template("""
    Material mat_0;
    mat_0.albedo = ${albedo};
    mat_0.roughness = ${roughness};
    mat_0.emissive = ${emissive};
    mat_0.clearcoat = ${clearcoat};
    mat_0.metallic = ${metallic};""")

mat_v3_non_emissive_template = Template("""
    Material mat_0;
    mat_0.albedo = ${albedo};
    mat_0.roughness = ${roughness};
    mat_0.clearcoat = ${clearcoat};
    mat_0.metallic = ${metallic};""")

rgb_grid_3d_template = Template("""
    Material mat_0;
    mat_0.albedo = vec3(0.0);
    mat_0.metallic = ${metallic};
    mat_0.roughness = ${roughness};
    float box_sdf = Box3D(${pos_latest}, vec3(1.0));
    if (box_sdf < ${bound_threshold}) {
        // pos_0 is in -1 to 1. Convert to 0 1
        vec3 p_local = (${pos_latest} + 1.0) / 2.0;
        p_local = p_local.zyx;
        vec3 rgb = texture(${rgb_texture_name}, p_local).rgb;
        mat_0.albedo = rgb;
    }
""")


mat_v4_template = Template("""
    Material mat_0;
    mat_0.albedo = ${albedo};
    mat_0.emissive = ${emissive};
    mat_0.mrc = ${mrc};
""")



mat_v3_reference_template = Template("""
    Material mat_0 = ${mat_name}(${pos_latest}, n_0);
""")

@rec_shader_eval.register
def eval_mat_v3(expression: sls.MaterialV3, global_sc, *args, **kwargs) -> GlobalShaderContext:

    shader_params = expression.args[:]
    processed_params = _inline_parse_param_from_expr(expression, shader_params, global_sc)
    cur_pos = global_sc.local_sc.pos_stack.pop()

    if isinstance(expression, sls.NonEmissiveMaterialV3):
        code_lines = mat_v3_non_emissive_template.substitute(
            albedo=processed_params[0],
            metallic=processed_params[1],
            roughness=processed_params[2],
            clearcoat=processed_params[3],
            pos_latest=cur_pos
        )
    elif isinstance(expression, sls.EncodedRGBGrid3D):
        
        rgb_texture_name = processed_params[0]
        b64_data = processed_params[1]
        tex_shape = [int(x) for x in list(shader_params[2])] # shader_params will have it a vec2
        tex_dtype = processed_params[3]
        metallic = processed_params[4]
        roughness = processed_params[5]
        bound_threshold = processed_params[6]
        code_lines = rgb_grid_3d_template.substitute(
            rgb_texture_name=rgb_texture_name,
            b64_data=b64_data,
            tex_shape=tex_shape,
            tex_dtype=tex_dtype,
            metallic=metallic,
            roughness=roughness,
            bound_threshold=bound_threshold,
            pos_latest=cur_pos
        )
        texture_data = {'name': rgb_texture_name, 
                        'data_b64': b64_data,
                        'shape': tex_shape, 
                        'dtype': tex_dtype,
                        }
        global_sc.add_texture(texture_data)
    elif isinstance(expression, sls.MatReference):
        mat_name = processed_params[0]
        code_lines = mat_v3_reference_template.substitute(
            mat_name=mat_name,
            pos_latest=cur_pos
        )
        global_sc.local_sc.dependencies.append(mat_name)
    elif isinstance(expression, sls.MaterialV3):
        code_lines = mat_v3_template.substitute(
            albedo=processed_params[0],
            emissive=processed_params[1],
            roughness=processed_params[2],
            clearcoat=processed_params[3],
            metallic=processed_params[4],
            pos_latest=cur_pos
        )
        global_sc.local_sc.dependencies.append("Box3D")
    else:
        raise NotImplementedError(f"Material {expression.__class__.__name__} not implemented")

    for code_line in code_lines.split("\n"):
        global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.dependencies.append("BaseMaterials")
    global_sc.local_sc.dependencies.append("Box3D")
    global_sc.local_sc.res_sdf_stack.append(("Material", "mat_0"))
    return global_sc

rgb_grid_3d_for_v4_template = Template("""
    Material mat_0;
    vec3 p_local = (pos_0 + 1.0) / 2.0;
    p_local = p_local.zyx;
    vec3 rgb = texture(${rgb_texture_name}, p_local).rgb;
    mat_0.albedo = rgb;
    mat_0.mrc = vec3(${mrc});
""")
rgb_grid_2d_polar_template = Template("""
    Material mat_0;

    // local position in [-1,1]^3
    vec3 p_local = pos_0;

    // convert to spherical coordinates
    float r     = length(p_local);
    vec3  dir   = normalize(p_local);
    float theta = atan(dir.z, dir.x);           // azimuth [-π, π]
    float phi   = acos(clamp(dir.y, -1.0, 1.0)); // elevation [0, π]

    // normalize to [0,1]
    vec2 uv = vec2(theta / (2.0 * PI) + 0.5, phi / PI);

    // sample 2D texture using (θ, φ)
    vec3 rgb = texture(${rgb_texture_name}, uv).rgb;

    // assign material properties
    mat_0.albedo = rgb;
    mat_0.mrc = vec3(${mrc});
""")

esrgb_3d_shifted_template = Template("""
    Material mat_0;

    // local position in [-1,1]^3
    vec3 p_local = pos_0;

    // convert to spherical coordinates
    float r     = length(p_local);
    vec3  dir   = normalize(p_local);
    float theta = atan(dir.z, dir.x);           // azimuth [-π, π]
    float phi   = acos(clamp(dir.y, -1.0, 1.0)); // elevation [0, π]

    // normalize to [0,1]
    vec2 uv = vec2(theta / (2.0 * PI) + 0.5, phi / PI);

    uv = uv * ${scale} + ${shift};

    // sample 2D texture using (θ, φ)
    vec3 rgb = texture(${rgb_texture_name}, uv).rgb;

    // assign material properties
    mat_0.albedo = rgb;
    mat_0.mrc = vec3(${mrc});
""")


@rec_shader_eval.register
def eval_mat_v4(expression: sls.MaterialV4, global_sc, cur_pos=None, *args, **kwargs) -> GlobalShaderContext:
    # Expand to support LOCAL RGB textures. 
    
    shader_params = expression.args[:]
    processed_params = _inline_parse_param_from_expr(expression, shader_params, global_sc)
    mat_name = f"mat_{global_sc.material_count}"
    if isinstance(expression, (sls.EncodedRGBGrid3DV4, sls.EncodedSphericalRGBGrid3DV4)):
        # Create function
        rgb_texture_name = processed_params[0]
        b64_data = processed_params[1]
        tex_shape = [int(x) for x in list(shader_params[2])] # shader_params will have it a vec2
        tex_dtype = processed_params[3]
        mrc = processed_params[4]
        bound_threshold = processed_params[5]
        mat_function_name = f"{mat_name}_func"

        global_sc.push_codebook(mat_function_name, MATERIAL_EXPR_PROPS_V4)

        if isinstance(expression, (sls.ESRGB3DShifted, sls.ESRGB3DShiftedDummy)):
            shift = processed_params[6]
            scale = processed_params[7]
            code_lines = esrgb_3d_shifted_template.substitute(
                rgb_texture_name=rgb_texture_name,
                mrc=mrc,
                bound_threshold=bound_threshold,
                shift=shift,
                scale=scale,
            )
        elif isinstance(expression, sls.EncodedSphericalRGBGrid3DV4):
            code_lines = rgb_grid_2d_polar_template.substitute(
                rgb_texture_name=rgb_texture_name,
                mrc=mrc,
                bound_threshold=bound_threshold,
            )
        else:
            code_lines = rgb_grid_3d_for_v4_template.substitute(
                rgb_texture_name=rgb_texture_name,
                mrc=mrc,
                bound_threshold=bound_threshold,
            )
        for code_line in code_lines.split("\n"):
            global_sc.local_sc.add_codeline(code_line)
        global_sc.local_sc.dependencies.append("BaseMaterials_v4")
        global_sc.local_sc.dependencies.append("Box3D")
        global_sc.local_sc.res_sdf_stack.append(("Material", "mat_0"))

        global_sc.resolve_codebook()
        global_sc.pop_codebook()
        if not isinstance(expression, sls.ESRGB3DShiftedDummy):
            texture_data = {'name': rgb_texture_name, 
                            'data_b64': b64_data,
                            'shape': tex_shape, 
                            'dtype': tex_dtype,
                            }
            global_sc.add_texture(texture_data)
        func_name = mat_function_name
        shader_params = f"{cur_pos}"
    else:
        shader_params = ", ".join(processed_params)
        func_name = expression.__class__.__name__
    global_sc.material_count += 1
    code_line = f"Material {mat_name} = {func_name}({shader_params});"
    global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.add_dependency(func_name)
    global_sc.add_shader_module(func_name)
    global_sc.material_stack.append(mat_name)
    return global_sc

@rec_shader_eval.register
def eval_mat_register(expression: sls.RegisterMaterial, global_sc, *args, **kwargs) -> GlobalShaderContext:

    shader_params = expression.args[:]
    processed_params = _inline_parse_param_from_expr(expression, shader_params, global_sc)
    mat_name = processed_params[0]
    # NEEd to create the function 
    # Create the function in a separate context.
    mat_function_name = f"{mat_name}"
    
    if mat_function_name in global_sc.material_registry:
        mat_index = global_sc.material_registry[mat_function_name]
    else:
        mat_index = global_sc.material_count
        global_sc.material_count += 1
        global_sc.material_registry.update({mat_function_name: mat_index})


    # Need to create the function 
    # Create the function in a separate context.
    global_sc.push_codebook(mat_function_name, MATERIAL_EXPR_PROPS)
    shader_params = expression.args[:]
    if len(processed_params) == 5:
        code_lines = mat_v3_non_emissive_template.substitute(
            albedo=processed_params[0],
            roughness=processed_params[1],
            clearcoat=processed_params[2],
            metallic=processed_params[3]
        )
    elif len(processed_params) == 6:
        code_lines = mat_v3_template.substitute(
            albedo=processed_params[0],
            roughness=processed_params[1],
            clearcoat=processed_params[2],
            metallic=processed_params[3],
            emissive=processed_params[4]
        )
    for code_line in code_lines.split("\n"):
        global_sc.local_sc.add_codeline(code_line)
    global_sc.local_sc.dependencies.append("BaseMaterials")
    global_sc.local_sc.res_sdf_stack.append(("Material", "mat_0"))
    global_sc.resolve_codebook()
    global_sc.pop_codebook()

    return global_sc

