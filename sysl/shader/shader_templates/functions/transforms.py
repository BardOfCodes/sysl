from ...shader_module import register_shader_module, ShaderModule, SMMap
import geolipi.symbolic as gls

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
    mat3 R = rz * ry * rx;
    return p * R ;
}
""")


AxisAngleRotate3D = register_shader_module("""
@name AxisAngleRotate3D
@inputs pos, axis_angle
@outputs pos
@dependencies
vec3 AxisAngleRotate3D( vec3 p, vec3 axis_angle )
{
    float theta = length(axis_angle);
    vec3 axis = normalize(axis_angle);

    mat3 K = mat3(0.0, -axis.z, axis.y, axis.z, 0.0, -axis.x, -axis.y, axis.x, 0.0);
    float s = sin(theta);
    float c = cos(theta);
    mat3 R = mat3(1.0) + s * K + (1.0 - c) * (K * K);
    return p * R;  // row vector multiplied from left
}""")



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


Affine3D = register_shader_module("""
@name Affine3D
@inputs pos, matrix
@outputs pos
@dependencies
vec3 Affine3D( vec3 p, mat4 matrix )
{
    vec4 out_p = vec4(p, 1.0) * matrix;
    return out_p.xyz;
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
    vec3 out_vec = p - 2.0 * dot(p, n) * n;
    return out_vec;
}
""")

ReflectX3D = register_shader_module("""
@name ReflectX3D
@inputs pos
@outputs pos
@dependencies
vec3 ReflectX3D( vec3 p )
{
    return vec3(abs(p.x), p.y, p.z);
}
""")

ReflectY3D = register_shader_module("""
@name ReflectY3D
@inputs pos
@outputs pos
@dependencies
vec3 ReflectY3D( vec3 p )
{
    return vec3(p.x, abs(p.y), p.z);
}
""")

ReflectZ3D = register_shader_module("""
@name ReflectZ3D
@inputs pos
@outputs pos
@dependencies
vec3 ReflectZ3D( vec3 p )
{
    return vec3(p.x, p.y, abs(p.z));
}
""")


TranslationSymmetry3D = register_shader_module("""
@name TranslationSymmetry3D
@inputs pos, axis, count
@outputs pos
@dependencies
vec3 TranslationSymmetry3D( vec3 p, vec3 direction, float offset, float count )
{ 
    int i_count = int(count);
    vec3 n = normalize(direction);
    float d = dot(p, n);
    int mod_count = int(d / offset);
    mod_count = min(mod_count, i_count - 1);
    float mul = mod_count < 0 ? 0.0 : float(mod_count);
    vec3 new_vec = p - mul * offset * n;
    return new_vec;
}""")

TranslationSymmetryX3D = register_shader_module("""
@name TranslationSymmetryX3D
@inputs pos, count
@outputs pos
@dependencies
vec3 TranslationSymmetryX3D( vec3 p, float offset, float count )
{
    int i_count = int(count);
    int mod_count = int(p.x / offset);
    mod_count = min(mod_count, i_count - 1);
    float mul = mod_count < 0 ? 0.0 : float(mod_count);
    vec3 new_vec = vec3(p.x - mul * offset, p.y, p.z);
    return new_vec;
}""")

TranslationSymmetryY3D = register_shader_module("""
@name TranslationSymmetryY3D
@inputs pos, offset, count
@outputs pos
@dependencies
vec3 TranslationSymmetryY3D( vec3 p, float offset, float count )
{
    int i_count = int(count);
    int mod_count = int(p.y / offset);
    mod_count = min(mod_count, i_count - 1);
    float mul = mod_count < 0 ? 0.0 : float(mod_count);
    vec3 new_vec = vec3(p.x, p.y - mul * offset, p.z);
    return new_vec;
}""")   

TranslationSymmetryZ3D = register_shader_module("""
@name TranslationSymmetryZ3D
@inputs pos, offset, count
@outputs pos
@dependencies
vec3 TranslationSymmetryZ3D( vec3 p, float offset, float count )
{
    int i_count = int(count);
    int mod_count = int(p.z / offset);
    mod_count = min(mod_count, i_count - 1);
    float mul = mod_count < 0 ? 0.0 : float(mod_count);
    vec3 new_vec = vec3(p.x, p.y, p.z - mul * offset);
    return new_vec;
}""")   

wrapPeriod = register_shader_module("""
@name wrapPeriod
@inputs x, period
@outputs x
@dependencies
float wrapPeriod(float a, float period)
{
    return a - period * floor(a / period);
}""")

RotationSymmetryX3D = register_shader_module("""
@name RotationSymmetryX3D
@inputs pos, offset, count
@outputs pos
@dependencies wrapPeriod
vec3 RotationSymmetryX3D( vec3 p, float offset, float count )
{
    float n = max(count, 1.0);
    float period = 6.28318530718 / n; // 2*pi / count

    // polar in YZ plane
    float r   = length(p.yz);
    float ang = atan(p.z, p.y); // angle around X

    // fold angle into a single sector, with phase offset
    ang -= offset;
    ang  = wrapPeriod(ang, period);
    ang += offset;

    // back to Euclidean
    vec2 yz = r * vec2(cos(ang), sin(ang));
    return vec3(p.x, yz.x, yz.y);
}""")

RotationSymmetryY3D = register_shader_module("""
@name RotationSymmetryY3D
@inputs pos, offset, count
@outputs pos
@dependencies wrapPeriod
vec3 RotationSymmetryY3D( vec3 p, float offset, float count )
{
    float n = max(count, 1.0);
    float period = 6.28318530718 / n;

    float r   = length(p.xz);
    float ang = atan(p.z, p.x); // angle around Y

    ang -= offset;
    ang  = wrapPeriod(ang, period);
    ang += offset;

    vec2 xz = r * vec2(cos(ang), sin(ang));
    return vec3(xz.x, p.y, xz.y);
}""")

RotationSymmetryZ3D = register_shader_module("""
@name RotationSymmetryZ3D
@inputs pos, offset, count
@outputs pos
@dependencies wrapPeriod
vec3 RotationSymmetryZ3D( vec3 p, float offset, float count )
{
    float n = max(count, 1.0);
    float period = 6.28318530718 / n;

    float r   = length(p.xy);
    float ang = atan(p.y, p.x); // angle around Z

    ang -= offset;
    ang  = wrapPeriod(ang, period);
    ang += offset;

    vec2 xy = r * vec2(cos(ang), sin(ang));
    return vec3(xy.x, xy.y, p.z);
}""")


# Distort. TBD

Twist3D = register_shader_module("""
@name Twist3D
@inputs pos, k
@outputs q
@dependencies
vec3 Twist3D( in vec3 p , in float k )
{
    float c = cos(k*p.y);
    float s = sin(k*p.y);
    mat2  m = mat2(c,-s,s,c);
    vec2 qq = m * p.xz;
    vec3  q = vec3(qq.x,p.y, qq.y);
    return q;
}""")

Bend3D = register_shader_module("""
@name Bend3D
@inputs pos, k
@outputs pos
@dependencies
vec3 Bend3D( in vec3 p , in float k )
{
    float c = cos(k*p.x);
    float s = sin(k*p.x);
    mat2  m = mat2(c,-s,s,c);
    vec3  q = vec3(m*p.xy,p.z);
    return q;
}""")
