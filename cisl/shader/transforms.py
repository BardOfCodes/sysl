from .shader_module import register_shader_module, ShaderModule, SMMap
import geolipi.symbolic as gls


EulerRotate3D = register_shader_module("""
@name EulerRotate3D
@inputs pos, angles
@outputs pos
@dependencies
vec3 EulerRotate3D( vec3 p, vec3 angles )
{
    float cx = cos(angles.x), sx = sin(angles.x);
    float cy = cos(angles.y), sy = sin(angles.y);
    float cz = cos(angles.z), sz = sin(angles.z);
    mat3 rx = mat3(1.0, 0.0, 0.0, 0.0, cx, -sx, 0.0, sx, cx);
    mat3 ry = mat3(cy, 0.0, sy, 0.0, 1.0, 0.0, -sy, 0.0, cy);
    mat3 rz = mat3(cz, -sz, 0.0, sz, cz, 0.0, 0.0, 0.0, 1.0);
    return rz * ry * rx * p;
}
""")

Scale3D = register_shader_module("""
@name Scale3D
@inputs pos, scale
@outputs pos
@dependencies
vec3 Scale3D( vec3 p, vec3 scale )
{
    return p / scale;
}
""")

Translate3D = register_shader_module("""
@name Translate3D
@inputs pos, translation
@outputs pos
@dependencies
vec3 Translate3D( vec3 p, vec3 translation )
{
    return p - translation;
}
""")


ReflectCoords3D = register_shader_module("""
@name ReflectCoords3D
@inputs pos, normal
@outputs pos
@dependencies
vec3 ReflectCoords3D( vec3 p, vec3 normal )
{
    // normalize normal
    vec3 n = normalize(normal);
    // reflect p about n
    vec3 out = p - 2 * dot(p, n) * n;
    return out;
}
""")




