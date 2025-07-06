import sympy as sp
from typing import Tuple, Any
import geolipi.symbolic as gls
from .global_shader_context import GlobalShaderContext

uniform_type_map = {
    gls.UniformFloat: "float",
    gls.UniformVec2: "vec2",
    gls.UniformVec3: "vec3",
    gls.UniformVec4: "vec4",
}

# A mapper from operation type to shader line template
map_op_map = {
    "add": "{expr1} + {expr2}",
    "sub": "{expr1} - {expr2}",
    "mul": "{expr1} * {expr2}",
    "div": "{expr1} / {expr2}",
    "pow": "pow({expr1}, {expr2})",
    "neg": "-{expr}",
    "sin": "sin({expr})",
    "cos": "cos({expr})",
    "tan": "tan({expr})",
    "asin": "asin({expr})",
    "acos": "acos({expr})",
    "atan": "atan({expr})",
    "atan2": "atan({expr1}, {expr2})",
    "log": "log({expr})",
    "exp": "exp({expr})",
    "sqrt": "sqrt({expr})",
    "abs": "abs({expr})",
    "min": "min({expr1}, {expr2})",
    "max": "max({expr1}, {expr2})",
    "floor": "floor({expr})",
    "ceil": "ceil({expr})",
    "round": "round({expr})",
    "frac": "fract({expr})",
    "sign": "sign({expr})",
    "step": "step({expr1}, {expr2})",
    "mod": "mod({expr1}, {expr2})",
    "normalize": "normalize({expr})",
    "norm": "length({expr})",
}

def recursive_parse_param(expression, params, global_sc: GlobalShaderContext):
    shader_params = []
    for ind, param in enumerate(params):
        if isinstance(param, (tuple, sp.Tuple)):
            processed_param = param_primitive_process(param)
            shader_params.append(processed_param)
        elif isinstance(param, str):
            # Are we sure?
            shader_params.append(param)
        elif isinstance(param, sp.Symbol):
            if param in expression.lookup_table:
                cur_param = expression.lookup_table[param]
                processed_param = param_primitive_process(cur_param)
                shader_params.append(processed_param)
            else:
                shader_params.append(param.name)
        elif isinstance(param, (sp.Integer, sp.Float)):
            if isinstance(param, sp.Integer):
                param = float(param)
            processed_param = f"{param}"
            shader_params.append(processed_param)
        elif isinstance(param, (gls.VecList)):
            vector_list, n_vecs = param.args
            under_params = vector_list
            under_expression = param
            cur_params, global_sc = recursive_parse_param(under_expression, under_params, global_sc)
            varname = f"var_{len(global_sc.local_sc.tracked_variables)}"
            global_sc.local_sc.tracked_variables.append(varname)
            vec_type = f"vec{len(vector_list[0])}"
            vec_line = f"const {vec_type}[] {varname} = {vec_type}[]({', '.join(cur_params)});"
            global_sc.local_sc.add_codeline(vec_line)
            shader_params.append(varname)
            shader_params.append(str(n_vecs))
        elif isinstance(param, (gls.UniformFloat, gls.UniformVec2, gls.UniformVec3, gls.UniformVec4)):
            min_val, default_val, max_val, uniform_name = param.args
            assert isinstance(uniform_name, sp.Symbol), f"Uniform name {uniform_name} is not a symbol"
            uniform_name = uniform_name.name
            arg_type = uniform_type_map[type(param)]
            uniform_entry = {'type': arg_type, "init_value": [float(x) for x in default_val], 
                                "min": [float(x) for x in min_val], "max": [float(x) for x in max_val]}
            if isinstance(param, gls.UniformFloat):
                uniform_entry["init_value"] = uniform_entry["init_value"][0]
            global_sc.uniforms.update({uniform_name: uniform_entry})
            shader_params.append(uniform_name)
        elif isinstance(param, (gls.Float, gls.Vec2, gls.Vec3, gls.Vec4)):
            # Now its input can be a math node, or a variable. 
            under_expression = param
            under_params = param.args
            cur_params, global_sc = recursive_parse_param(under_expression, under_params, global_sc)
            if isinstance(param, gls.Float):
                shader_params.append(cur_params[0])
            elif isinstance(param, gls.Vec2):
                new_param = f"vec2({cur_params[0]}, {cur_params[1]})"
                shader_params.append(new_param)
            elif isinstance(param, gls.Vec3):
                new_param = f"vec3({cur_params[0]}, {cur_params[1]}, {cur_params[2]})"
                shader_params.append(new_param)
            elif isinstance(param, gls.Vec4):
                new_param = f"vec4({cur_params[0]}, {cur_params[1]}, {cur_params[2]}, {cur_params[3]})"
                shader_params.append(new_param)
            else:
                raise NotImplementedError
        elif isinstance(param, gls.VarSplitter):
            under_expression = param
            under_params = param.args
            cur_params, global_sc = recursive_parse_param(under_expression, under_params, global_sc)
            selected_ind = int(float(cur_params[1]))
            new_param = cur_params[0]
            if selected_ind == 0:
                shader_params.append(f"{new_param}.x")
            elif selected_ind == 1:
                shader_params.append(f"{new_param}.y")
            elif selected_ind == 2:
                shader_params.append(f"{new_param}.z")
            elif selected_ind == 3:
                shader_params.append(f"{new_param}.w")
            else:
                raise NotImplementedError
        elif isinstance(param, (gls.UnaryOperator, gls.VectorOperator)):
            under_expression = param
            under_params = param.args
            cur_params, global_sc = recursive_parse_param(under_expression, under_params, global_sc)
            new_param = cur_params[0]
            op = cur_params[1]
            op_template = map_op_map[op]
            shader_line = op_template.format(expr=new_param)
            shader_params.append(shader_line)
        elif isinstance(param, gls.BinaryOperator):
            under_expression = param
            under_params = param.args
            cur_params, global_sc = recursive_parse_param(under_expression, under_params, global_sc)
            new_param1 = cur_params[0]
            new_param2 = cur_params[1]
            op = cur_params[2]
            op_template = map_op_map[op]
            shader_line = op_template.format(expr1=new_param1, expr2=new_param2)
            shader_params.append(shader_line)
        else:
            raise NotImplementedError
            
    return shader_params, global_sc


def _inline_parse_param_from_expr(expression: gls.GLFunction, params: Tuple[Any, ...], global_sc: GlobalShaderContext):
    shader_params, global_sc = recursive_parse_param(expression, params, global_sc)
    return shader_params

def param_primitive_process(param):

    if isinstance(param, str):
        shader_line = f"{param}"
    else:
        if len(param) == 0:
            if isinstance(param, sp.Integer):
                param = float(param)
            shader_line = f"{param}"
        if len(param) == 1:
            if isinstance(param[0], sp.Integer):
                param = [float(param[0])]
            shader_line = f"{param[0]}"
        elif len(param) == 2:
            shader_line = f"vec2({float(param[0])}, {float(param[1])})"
        elif len(param) == 3:
            shader_line = f"vec3({float(param[0])}, {float(param[1])}, {float(param[2])})"
        elif len(param) == 4:
            shader_line = f"vec4({float(param[0])}, {float(param[1])}, {float(param[2])}, {float(param[3])})"
        else:
            raise NotImplementedError
    return shader_line
