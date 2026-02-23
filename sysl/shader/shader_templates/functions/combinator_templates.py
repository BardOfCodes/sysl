"""
GLSL template definitions for combinator operations.

This module contains all the GLSL code templates and operation definitions
for various combinator operations like Union, Intersection, Difference, etc.
"""

from string import Template

# Template for 2-argument functions
BASE_TEMPLATE = Template("""
${type} ${func_name}( ${type} d1, ${type} d2 )
{  
    if (${condition}) {
        return d1;
    } else {
        return d2;
    }
}
""")

# Template for n-argument functions
NARY_TEMPLATE = Template("""
${type} ${func_name}(${args})
{
    return ${inner_code};
}
""")

# Operation definitions
OPERATIONS = {
    "Union": {
        "float": "d1<d2",
        "vec": "d1.x<d2.x",
        "MATPoint": "d1.x<d2.x"
    },
    "Intersection": {
        "float": "d1>d2", 
        "vec": "d1.x>d2.x",
        "MATPoint": "d1.x>d2.x"
    }
}

# Supported types
VECTOR_TYPES = ["vec2", "vec3", "vec4"]
MAT_TYPE = ["MATPoint"]
ALL_TYPES = ["float"] + VECTOR_TYPES + MAT_TYPE

# DIFFERENCE TEMPLATES
FLOAT_DIFF_CODE = """
float Difference( float sdf1, float sdf2 )
{
  return max(sdf1, -sdf2);
}
"""

NARY_DIFF_CODE = Template("""
${type} Difference( ${type} res1, ${type} res2 )
{
  if (res1.x > -res2.x) {
    return res1;
  }else{
    res2.x = -res2.x;
    return res2;
  }
}
""")

DIFF_ARITY_MAP = {
    ("float", 2): FLOAT_DIFF_CODE,
    ("vec2", 2): NARY_DIFF_CODE.substitute(type="vec2"),
    ("vec3", 2): NARY_DIFF_CODE.substitute(type="vec3"),
    ("vec4", 2): NARY_DIFF_CODE.substitute(type="vec4"),
    ("MATPoint", 2): NARY_DIFF_CODE.substitute(type="MATPoint"),
}

# SWITCHED DIFFERENCE TEMPLATES
FLOAT_SWITCHED_DIFF_CODE = """
float SwitchedDifference( float sdf1, float sdf2 )
{
  return max(-sdf1, sdf2);
}
"""

NARY_SWITCHED_DIFF_CODE = Template("""
${type} SwitchedDifference( ${type} res1, ${type} res2 )
{
  if (-res1.x > res2.x) {
    res1.x = -res1.x;
    return res1;
  }else{
    return res2;
  }
}
""")

SWITCHED_DIFF_ARITY_MAP = {  
    ("float", 2): FLOAT_SWITCHED_DIFF_CODE,
    ("vec2", 2): NARY_SWITCHED_DIFF_CODE.substitute(type="vec2"),
    ("vec3", 2): NARY_SWITCHED_DIFF_CODE.substitute(type="vec3"),
    ("vec4", 2): NARY_SWITCHED_DIFF_CODE.substitute(type="vec4"),
    ("MATPoint", 2): NARY_SWITCHED_DIFF_CODE.substitute(type="MATPoint"),
}

# COMPLEMENT TEMPLATES
COMPLEMENT_CODE = Template("""
${type} Complement( ${type} res )
{
  return -res;
}
""")

COMPLEMENT_ARITY_MAP = {
    ("float", 1): COMPLEMENT_CODE.substitute(type="float"),
    ("vec2", 1): COMPLEMENT_CODE.substitute(type="vec2"),
    ("vec3", 1): COMPLEMENT_CODE.substitute(type="vec3"),
    ("vec4", 1): COMPLEMENT_CODE.substitute(type="vec4"),
    ("MATPoint", 1): COMPLEMENT_CODE.substitute(type="MATPoint"),
}

# SMOOTH UNION TEMPLATES
SMOOTH_UNION_FLOAT_CODE = """
float SmoothUnion( float res1, float res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2 - res1)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}
"""

SMOOTH_UNION_VEC_CODE = Template("""
${type} SmoothUnion( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}
""")

SMOOTH_UNION_MATPOINT_CODE = Template("""
${type} SmoothUnion( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    // mix res, albedo, emissive, mrc
    float t = k*h*(1.0-h);
    ${type} out_res;
    out_res.x = mix( res2.x, res1.x, h ) - t;
    out_res.mat.albedo = mix( res2.mat.albedo, res1.mat.albedo, h );
    out_res.mat.emissive = mix( res2.mat.emissive, res1.mat.emissive, h );
    out_res.mat.mrc = mix( res2.mat.mrc, res1.mat.mrc, h );
    return out_res;
}
""")

SMOOTH_UNION_ARITY_MAP = {
    ("float", 2): SMOOTH_UNION_FLOAT_CODE,
    ("vec2", 2): SMOOTH_UNION_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): SMOOTH_UNION_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): SMOOTH_UNION_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): SMOOTH_UNION_MATPOINT_CODE.substitute(type="MATPoint"),
}

# GEOM ONLY SMOOTH UNION TEMPLATES
GEOM_ONLY_SMOOTH_UNION_FLOAT_CODE = """
float GeomOnlySmoothUnion( float res1, float res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2 - res1)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}
"""

GEOM_ONLY_SMOOTH_UNION_VEC_CODE = Template("""
${type} GeomOnlySmoothUnion( ${type} res1, ${type} res2, float k )
{
    ${type} out_res;
    if (res1.x < res2.x) {
        out_res = res1;
    }else{
        out_res = res2;
    }

    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    float new_x = mix( res2.x, res1.x, h ) - k*h*(1.0-h);
    out_res.x = new_x;
    return out_res;
}
""")



GEOM_ONLY_SMOOTH_UNION_ARITY_MAP = {
    ("float", 2): GEOM_ONLY_SMOOTH_UNION_FLOAT_CODE,
    ("vec2", 2): GEOM_ONLY_SMOOTH_UNION_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): GEOM_ONLY_SMOOTH_UNION_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): GEOM_ONLY_SMOOTH_UNION_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): GEOM_ONLY_SMOOTH_UNION_VEC_CODE.substitute(type="MATPoint"),
}
# SMOOTH UNION MIXED TEMPLATES
SMOOTH_UNION_MIXED_FLOAT_CODE = """
float SmoothUnionMixed( float res1, float res2, float k_1, float k_2 )
{
    float h = clamp( 0.5 + 0.5*(res2 - res1)/k_1, 0.0, 1.0 );
    return mix( res2, res1, h ) - k_1*h*(1.0-h);
}
"""

SMOOTH_UNION_MIXED_VEC_CODE = Template("""
${type} SmoothUnionMixed( ${type} res1, ${type} res2, float k_1, float k_2 )
{
    float h_1 = clamp( 0.5 + 0.5*(res2.x - res1.x)/k_1, 0.0, 1.0 );
    float h_2 = clamp( 0.5 + 0.5*(res2.x - res1.x)/k_2, 0.0, 1.0 );
    ${type} out_res = mix( res2, res1, h_2 );
    out_res.x = mix( res2.x, res1.x, h_1 ) - k_1*h_1*(1.0-h_1);

    return out_res;
}
""")


SMOOTH_UNION_MIXED_MATPOINT_CODE = Template("""
${type} SmoothUnionMixed( ${type} res1, ${type} res2, float k_1, float k_2 )
{
    float h_1 = clamp( 0.5 + 0.5*(res2.x - res1.x)/k_1, 0.0, 1.0 );
    float h_2 = clamp( 0.5 + 0.5*(res2.x - res1.x)/k_2, 0.0, 1.0 );
    // mix res, albedo, emissive, mrc
    float t_1 = k_1*h_1*(1.0-h_1);
    // float t_2 = k_2*h_2*(1.0-h_2); // not used
    ${type} out_res;
    out_res.x = mix( res2.x, res1.x, h_1 ) - t_1;
    out_res.mat.albedo = mix( res2.mat.albedo, res1.mat.albedo, h_2 );
    out_res.mat.emissive = mix( res2.mat.emissive, res1.mat.emissive, h_2 );
    out_res.mat.mrc = mix( res2.mat.mrc, res1.mat.mrc, h_2 );
    return out_res;
}
""")

SMOOTH_UNION_MIXED_ARITY_MAP = {
    ("float", 2): SMOOTH_UNION_MIXED_FLOAT_CODE,
    ("vec2", 2): SMOOTH_UNION_MIXED_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): SMOOTH_UNION_MIXED_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): SMOOTH_UNION_MIXED_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): SMOOTH_UNION_MIXED_MATPOINT_CODE.substitute(type="MATPoint"),
}


# SMOOTH INTERSECTION TEMPLATES
SMOOTH_INTERSECTION_FLOAT_CODE = """
float SmoothIntersection( float res1, float res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2-res1)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) + k*h*(1.0-h);
}
"""

SMOOTH_INTERSECTION_VEC_CODE = Template("""
${type} SmoothIntersection( ${type} res1, ${type} res2, float k )
{   
    float h = clamp( 0.5 - 0.5*(res2.x-res1.x)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) + k*h*(1.0-h);
}
""")


SMOOTH_INTERSECTION_MATPOINT_CODE = Template("""
${type} SmoothIntersection( ${type} res1, ${type} res2, float k )
{   
    float h = clamp( 0.5 - 0.5*(res2.x-res1.x)/k, 0.0, 1.0 );
    float t = k*h*(1.0-h);
    ${type} out_res;
    out_res.x = mix( res2.x, res1.x, h ) + t;
    out_res.mat.albedo = mix( res2.mat.albedo, res1.mat.albedo, h );
    out_res.mat.emissive = mix( res2.mat.emissive, res1.mat.emissive, h );
    out_res.mat.mrc = mix( res2.mat.mrc, res1.mat.mrc, h );
    return out_res;
}
""")

SMOOTH_INTERSECTION_ARITY_MAP = {
    ("float", 2): SMOOTH_INTERSECTION_FLOAT_CODE,
    ("vec2", 2): SMOOTH_INTERSECTION_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): SMOOTH_INTERSECTION_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): SMOOTH_INTERSECTION_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): SMOOTH_INTERSECTION_MATPOINT_CODE.substitute(type="MATPoint"),
}

# SMOOTH DIFFERENCE TEMPLATES
SMOOTH_DIFFERENCE_FLOAT_CODE = """
float SmoothDifference( float res1, float res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2+res1)/k, 0.0, 1.0 );
    return mix( res1, -res2, h ) + k*h*(1.0-h);
}
"""

SMOOTH_DIFFERENCE_VEC_CODE = Template("""
${type} SmoothDifference( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2.x+res1.x)/k, 0.0, 1.0 );
    res2.y = -res2.y;
    return mix( res1, -res2, h ) + k*h*(1.0-h);
}
""")

SMOOTH_DIFFERENCE_MATPOINT_CODE = Template("""
${type} SmoothDifference( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2.x+res1.x)/k, 0.0, 1.0 );
    float t = k*h*(1.0-h);
    ${type} out_res;
    out_res.x = mix( res1, -res2, h ) + t;
    out_res.mat.albedo = mix( res1.mat.albedo, res2.mat.albedo, h );
    out_res.mat.emissive = mix( res1.mat.emissive, res2.mat.emissive, h );
    out_res.mat.mrc = mix( res1.mat.mrc, res2.mat.mrc, h );
    return out_res;
}
""")

SMOOTH_DIFFERENCE_ARITY_MAP = {
    ("float", 2): SMOOTH_DIFFERENCE_FLOAT_CODE,
    ("vec2", 2): SMOOTH_DIFFERENCE_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): SMOOTH_DIFFERENCE_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): SMOOTH_DIFFERENCE_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): SMOOTH_DIFFERENCE_VEC_CODE.substitute(type="MATPoint"),
}

XOR_FLOAT_CODE = """
float XOR( float res1, float res2 )
{
    return max(min(res1, res2), -max(res1, res2));
}
"""

XOR_VEC_CODE = Template("""
${type} XOR( ${type} res1, ${type} res2 )
{
    return max(min(res1.x, res2.x), -max(res1.x, res2.x));
}
""")

XOR_ARITY_MAP = {
    ("float", 2): XOR_FLOAT_CODE,
    ("vec2", 2): XOR_VEC_CODE.substitute(type="vec2"),
    ("vec3", 2): XOR_VEC_CODE.substitute(type="vec3"),
    ("vec4", 2): XOR_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 2): XOR_VEC_CODE.substitute(type="MATPoint"),
}

# DILATE TEMPLATES
DILATE_FLOAT_CODE = """
float Dilate3D( float res, float k )
{
    return res - k;
}
"""

DILATE_VEC_CODE = Template("""
${type} Dilate3D( ${type} res, float k )
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

# ERODE TEMPLATES
ERODE_FLOAT_CODE = """
float Erode3D( float res, float k )
{
    return res + k;
}
"""

ERODE_VEC_CODE = Template("""
${type} Erode3D( ${type} res, float k )
{
    res.x = res.x + k;
    return res;
}
""")

ERODE_ARITY_MAP = {
    ("float", 1): ERODE_FLOAT_CODE,
    ("vec2", 1): ERODE_VEC_CODE.substitute(type="vec2"),
    ("vec3", 1): ERODE_VEC_CODE.substitute(type="vec3"),
    ("vec4", 1): ERODE_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 1): ERODE_VEC_CODE.substitute(type="MATPoint"),
}

# ONION TEMPLATES
ONION_FLOAT_CODE = """
float Onion3D( float res, float k )
{
    return abs(res) - k;
}
"""

ONION_VEC_CODE = Template("""
${type} Onion3D( ${type} res, float k )
{
    res.x = abs(res.x) - k;
    return res;
}
""")

ONION_ARITY_MAP = {
    ("float", 1): ONION_FLOAT_CODE,
    ("vec2", 1): ONION_VEC_CODE.substitute(type="vec2"),
    ("vec3", 1): ONION_VEC_CODE.substitute(type="vec3"),
    ("vec4", 1): ONION_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 1): ONION_VEC_CODE.substitute(type="MATPoint"),
}

# NEG ONLY ONION TEMPLATES
NEG_ONLY_ONION_FLOAT_CODE = """
float NegOnlyOnion3D( float res, float k )
{
    if (res <= 0.0){
        res = abs(res) - k;
    }
    return res;
}
"""

NEG_ONLY_ONION_VEC_CODE = Template("""
${type} NegOnlyOnion3D( ${type} res, float k )
{
    if (res.x <= 0.0){
        res.x = abs(res.x) - k;
    }
    return res;
}
""")

NEG_ONLY_ONION_ARITY_MAP = {
    ("float", 1): NEG_ONLY_ONION_FLOAT_CODE,
    ("vec2", 1): NEG_ONLY_ONION_VEC_CODE.substitute(type="vec2"),
    ("vec3", 1): NEG_ONLY_ONION_VEC_CODE.substitute(type="vec3"),
    ("vec4", 1): NEG_ONLY_ONION_VEC_CODE.substitute(type="vec4"),
    ("MATPoint", 1): NEG_ONLY_ONION_VEC_CODE.substitute(type="MATPoint"),
}

