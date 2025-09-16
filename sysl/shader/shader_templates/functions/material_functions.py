from string import Template
from ...shader_module import register_shader_module, SMMap
from ...shader_module_classes import FixedArityShaderModule 

MatSolidV1 = register_shader_module("""
@name MatSolidV1
@inputs sdf, mat
@outputs res
@dependencies
vec2 MatSolidV1( float sdf, float mat )
{
  return vec2(sdf, mat);
}
vec2 MatSolidV1( vec2 res, float mat )
{
  return vec2(res.x, mat);
} 
""")


MatSolidV2 = register_shader_module("""
@name MatSolidV2
@inputs sdf, mat
@outputs res
@dependencies
vec4 MatSolidV2( float sdf, vec3 mat )
{
  return vec4(sdf, mat);
}
vec4 MatSolidV2( vec4 res, vec3 mat )
{
  return vec4(res.x, mat);
}
""")

MatSolidV3 = register_shader_module("""
@name MatSolidV3
@inputs sdf, mat
@outputs res
@dependencies
vec2 MatSolidV3( float sdf, float mat )
{
  return vec2(sdf, mat);
}
vec2 MatSolidV3( vec2 res, float mat )
{
  return vec2(res.x, mat);
} 
""")
### Mat Combinators

n_ary_color_only_code = Template("""
${type} MatColorOnly( ${type} res1, ${type} res2 )
{
  if (res1.x < res2.x) {
    return res1;
  }else{
    res2.x = res1.x;
    return res2;
  }
}
""")


color_only_arity_map = {
    ("vec2", 2): n_ary_color_only_code.substitute(type="vec2"),
    ("vec3", 2): n_ary_color_only_code.substitute(type="vec3"),
    ("vec4", 2): n_ary_color_only_code.substitute(type="vec4"),
}

def mat_color_only_factory():
    name = "MatColorOnly"
    module = FixedArityShaderModule(name, color_only_arity_map)
    return module

SMMap["MatColorOnly"] = mat_color_only_factory


n_ary_smooth_color_only_code = Template("""
${type} MatSmoothColorOnly( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    ${type} res = mix( res2, res1, h ) - k*h*(1.0-h);
    res.x = res1.x;
    return res;
}
""")


smooth_color_only_arity_map = {
    ("vec2", 2): n_ary_smooth_color_only_code.substitute(type="vec2"),
    ("vec3", 2): n_ary_smooth_color_only_code.substitute(type="vec3"),
    ("vec4", 2): n_ary_smooth_color_only_code.substitute(type="vec4"),
}

def mat_smooth_color_only_factory():
    name = "MatSmoothColorOnly"
    module = FixedArityShaderModule(name, smooth_color_only_arity_map)
    return module

SMMap["MatSmoothColorOnly"] = mat_smooth_color_only_factory
