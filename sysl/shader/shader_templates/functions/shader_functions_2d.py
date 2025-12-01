from ...shader_module import register_shader_module, SMMap
from string import Template
from ...shader_module_classes import NAryShaderModule, FixedArityShaderModule

Rotate2D = register_shader_module("""
@name Rotate2D
@inputs p, angle
@outputs res
@dependencies
vec2 Rotate2D( in vec2 p, in float angle )
{
    float s = sin(-angle);
    float c = cos(-angle);
    mat2 m = mat2(c, -s, s, c);
    return m * p;
}
""")

Circle2D = register_shader_module("""
@name Circle2D
@inputs p, s
@outputs res
@dependencies
float Circle2D( vec2 p, float s )
{
    return length(p)-s;
}
""")


Rectangle2D = register_shader_module("""
@name Rectangle2D
@inputs p, b
@outputs res
@dependencies
float Rectangle2D( in vec2 p, in vec2 b )
{   
    vec2 size = b / 2.0;
    vec2 d = abs(p)-size;
    return length(max(d,0.0)) + min(max(d.x,d.y),0.0);
}
""")


Trapezoid2D = register_shader_module("""
@name Trapezoid2D
@inputs p, r1, r2, he
@outputs res
@dependencies
float Trapezoid2D( in vec2 p, in float r1, float r2, float he )
{
    vec2 k1 = vec2(r2,he);
    vec2 k2 = vec2(r2-r1,2.0*he);
    p.x = abs(p.x);
    vec2 ca = vec2(p.x-min(p.x,(p.y<0.0)?r1:r2), abs(p.y)-he);
    vec2 cb = p - k1 + k2*clamp( dot(k1-p,k2)/dot2(k2), 0.0, 1.0 );
    float s = (cb.x<0.0 && ca.y<0.0) ? -1.0 : 1.0;
    return s*sqrt( min(dot2(ca),dot2(cb)) );
}
""")

Translate2D = register_shader_module("""
@name Translate2D
@inputs p, offset
@outputs res
@dependencies
vec2 Translate2D( in vec2 p, in vec2 offset )
{
    return p - offset;
}""")

EulerRotate2D = register_shader_module("""
@name EulerRotate2D
@inputs p, angle
@outputs res
@dependencies
vec2 EulerRotate2D( in vec2 p, in float angle )
{
    float s = sin(-angle);
    float c = cos(-angle);
    mat2 m = mat2(c, -s, s, c);
    return m * p;
}""")


# DILATE TEMPLATES
DILATE_FLOAT_CODE = """
float Dilate2D( float res, float k )
{
    return res - k;
}
"""

DILATE_VEC_CODE = Template("""
${type} Dilate2D( ${type} res, float k )
{
    res.x = res.x - k;
    return res;
}
""")

DILATE_ARITY_MAP = {
    ("float", 1): DILATE_FLOAT_CODE,
    ("vec2", 1): DILATE_VEC_CODE.substitute(type="vec2"),
    ("vec3", 1): DILATE_VEC_CODE.substitute(type="vec3"),
    ("vec4", 1): DILATE_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 1): DILATE_VEC_CODE.substitute(type="MATPoint"),
}


def dilate_factory():
    """Create a Dilate2D shader module."""
    name = "Dilate2D"
    module = FixedArityShaderModule(name, DILATE_ARITY_MAP)
    return module

SMMap["Dilate2D"] = dilate_factory