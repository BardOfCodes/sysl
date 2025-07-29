"""
This is derived from shadertoy code at: https://www.shadertoy.com/view/Xds3zN
Original Author: Inigo Quilez
"""

from .shader_module import register_shader_module
from string import Template
import numpy as np

PRELIMINARIES = """
"""


CONSTANTS = {
    "_ZERO": ('int', 0),
    "_FOCAL_LENGTH": ('float', 2.5),
    "_AA": ('int', 1),
    "_SCENE_RADIUS": ('float', 100.0),
    "_SCENE_BOX_CENTER": ('vec3', (0.0, 0.5, 0.0)),
    "_SCENE_BOX_SIZE": ('vec3', (10.0, 5.0, 10.0)),
    "_RAYCAST_MAX_STEPS": ('int', 100),
    "_RAYCAST_CONSERVATIVE_STEPPING_RATE": ('float', 1.0),
    "_ADD_FLOOR_PLANE": ('bool', True),
    "_SHADOW_MAX_STEPS": ('int', 64),
    "_NORMAL_STEPS": ('int', 4),
    "_AO_STEPS": ('int', 5),
    "_COLOR_FACTOR": ('float', 2.0),
}
UNIFORMS = {
    "castShadows": {
        'type': 'bool', "init_value": "true", 
        "min": "", "max": ""},
    "sunElevation": {
        'type': 'float', "init_value": 0.5,
        "min": [0.0,], "max": [np.pi/2],
    },
    "sunAzimuth": {
        'type': 'float', "init_value": 0.0,
        "min": [-np.pi], "max": [np.pi]},
    "cameraOrigin": {
        'type': 'vec3', "init_value": [0, 0.5, 0],
        "min": [-10, -10, -10], "max": [10, 10, 10]},
    "cameraDistance": {
        'type': 'float', "init_value": 5.0,
        "min": [0.0], "max": [10.0]},
    "cameraAngleX": {
        'type': 'float', "init_value": np.pi/4,
        "min": [-np.pi], "max": [np.pi]},
    "cameraAngleY": {
        'type': 'float', "init_value": np.pi/6,
        "min": [-np.pi], "max": [np.pi]},
    "resolution": {
        'type': 'vec2', "init_value": [512, 512],
        "min": [1, 1], "max": [10000, 10000]},
}

setCamera = register_shader_module("""
@name setCamera_v1
@inputs ro, ta, cr
@outputs cam
@dependencies
mat3 setCamera( in vec3 ro, in vec3 ta, float cr )
{
	vec3 cw = normalize(ta-ro);
	vec3 cp = vec3(sin(cr), cos(cr),0.0);
	vec3 cu = normalize( cross(cw,cp) );
	vec3 cv =          ( cross(cu,cw) );
    return mat3( cu, cv, cw );
}""")

getSunDirection = register_shader_module("""
@name getSunDirection_v1
@inputs 
@outputs sunDir
@dependencies
@vardeps sunElevation, sunAzimuth
vec3 getSunDirection() {
    // Y-up convention: elevation = 0 → horizon, +π/2 → straight up
    float x =  cos(sunElevation) * sin(sunAzimuth);
    float y =  sin(sunElevation);
    float z =  cos(sunElevation) * cos(sunAzimuth);
    return normalize(vec3(x, y, z));
}""")

mainImage = register_shader_module("""
@name mainImage_v1
@inputs fragColor, fragCoord
@outputs fragColor
@dependencies setCamera_v1, getSunDirection_v1, render_v1
@vardeps _AA, cameraOrigin, cameraDistance, cameraAngleX, cameraAngleY, resolution, _FOCAL_LENGTH, _ZERO
void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 mo = vec2(0.0, 0.0);
    // camera	
    vec3 ta = vec3( 0.0, 1.0, -0.0 ) + cameraOrigin;
    vec3 ro = ta + cameraDistance * vec3(
        cos(cameraAngleX) * sin(cameraAngleY), // X component
        sin(cameraAngleX),                     // Y component (elevation)
        cos(cameraAngleX) * cos(cameraAngleY)  // Z component
    );
    // camera-to-world transformation
    mat3 ca = setCamera( ro, ta, 0.0 );
    vec3 tot = vec3(0.0);
    vec3 lig = getSunDirection();
    for( int m=_ZERO; m<_AA; m++ )
    for( int n=_ZERO; n<_AA; n++ )
    {
        // pixel coordinates
        vec2 o = vec2(float(m),float(n)) / float(_AA) - 0.5;

        vec2 p = (2.0*(fragCoord+o)-resolution.xy)/resolution.xy;

        vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

        vec2 px = (2.0 * (fragCoord + vec2(1.0, 0.0)) - resolution.xy) / resolution.xy;
        vec2 py = (2.0 * (fragCoord + vec2(0.0, 1.0)) - resolution.xy) / resolution.xy;

        vec3 rdx = ca * normalize(vec3(px, _FOCAL_LENGTH));
        vec3 rdy = ca * normalize(vec3(py, _FOCAL_LENGTH));

        // render	
        vec3 col = render( ro, rd, rdx, rdy , lig);
        
        // TODO: optionally introduce other post processing steps here.

        // gain
        // col = col*3.0/(2.5+col);
        
		// gamma
        col = pow( col, vec3(0.4545) );

        tot += col;
    }
    tot /= float(_AA*_AA);
    
    fragColor = vec4( tot, 1.0 );
}""")

raycast = register_shader_module("""
@name raycast_v1
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO
@vardeps _RAYCAST_MAX_STEPS, _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec2 raycast(in vec3 ro, in vec3 rd) {

    vec2 res = vec2(-1.0,-1.0);

    // 1) Sphere cull: cheap dot/mul vs. complex SDF
    float b = dot(ro, ro) - _SCENE_RADIUS*_SCENE_RADIUS;
    float c = dot(ro, rd);
    float disc = c*c - b;
    if (disc <= 0.0) return res;                // no intersection with sphere
    float s   = sqrt(disc);
    float t0  = -c - s;
    float t1  = -c + s;
    if (t1 < 0.0) return res;                   // both intersections behind camera

    float tmin = max(1.0, t0);
    float tmax = min(20.0, t1);

    // 2) Floor-plane (y=0) test
    // MAKE THIS OPTIONAL.
    if (_ADD_FLOOR_PLANE) {
        float tp = -ro.y / rd.y;
        if (tp > 0.0 && tp < tmax) {
            tmax = tp;
            res = vec2(tp, 1.0);
        }
    }

    // 3) _AABB test
    vec3 inv_rd = 1.0 / rd;  // hoist reciprocal
    vec3 tA = ( _SCENE_BOX_CENTER - _SCENE_BOX_SIZE - ro ) * inv_rd;
    vec3 tB = ( _SCENE_BOX_CENTER + _SCENE_BOX_SIZE - ro ) * inv_rd;

    vec3 tMin3 = min(tA, tB);
    vec3 tMax3 = max(tA, tB);

    float tbmin = max( max(tMin3.x, tMin3.y), tMin3.z );
    float tbmax = min( min(tMax3.x, tMax3.y), tMax3.z );

    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        float t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            vec2 h = SCENE_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001 * t) {
                res = vec2(t, h.y);
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }

    return res;
}""")

calcSoftShadow = register_shader_module("""
@name calcSoftShadow_v1
@inputs ro, rd, mint, tmax
@outputs res
@dependencies SCENE_EXPRESSION
@vardeps castShadows, _ZERO, _SHADOW_MAX_STEPS
float calcSoftShadow( in vec3 ro, in vec3 rd, in float mint, in float tmax )
{
    // bounding volume
    if (!castShadows) return 1.0;
    float tp = (0.8-ro.y)/rd.y; 
    if( tp>0.0 ) tmax = min( tmax, tp );

    float res = 1.0;
    float t = mint;
    for( int i=_ZERO; i<_SHADOW_MAX_STEPS; i++ )
    {
		float h = SCENE_EXPRESSION( ro + rd*t ).x;
        float s = clamp(8.0*h/t,0.0,1.0);
        res = min( res, s );
        t += clamp( h, 0.01, 0.2 );
        if( res<0.004 || t>tmax ) break;
    }
    res = clamp( res, 0.0, 1.0 );
    return res*res*(3.0-2.0*res);
}""")

calcNormal = register_shader_module("""
@name calcNormal_v1
@inputs ro, rd
@outputs n
@dependencies SCENE_EXPRESSION
@vardeps _ZERO, _NORMAL_STEPS
vec3 calcNormal( in vec3 pos )
{
    // inspired by tdhooper and klems - a way to prevent the compiler from inlining OBJECT_SDF_AND_MATERIAL() 4 times
    vec3 n = vec3(0.0);
    for( int i=_ZERO; i<_NORMAL_STEPS; i++ )
    {
        vec3 e = 0.5773*(2.0*vec3((((i+3)>>1)&1),((i>>1)&1),(i&1))-1.0);
        n += e*SCENE_EXPRESSION(pos+0.0005*e).x;
      //if( n.x+n.y+n.z>100.0 ) break;
    }
    return normalize(n);
}""")

calcAO = register_shader_module("""
@name calcAO_v1
@inputs ro, rd
@outputs ao
@dependencies SCENE_EXPRESSION
@vardeps _ZERO, _AO_STEPS
float calcAO( in vec3 pos, in vec3 nor )
{
	float occ = 0.0;
    float sca = 1.0;
    for( int i=_ZERO; i<_AO_STEPS; i++ )
    {
        float h = 0.01 + 0.12*float(i)/float(_AO_STEPS - 1);
        float d = SCENE_EXPRESSION( pos + h*nor ).x;
        occ += (h-d)*sca;
        sca *= 0.95;
        if( occ>0.35 ) break;
    }
    return clamp( 1.0 - 3.0*occ, 0.0, 1.0 ) * (0.5+0.5*nor.y);
}""")

checkersGradBox = register_shader_module("""
@name checkersGradBox_v1
@inputs p, dpdx, dpdy
@outputs res
@dependencies
float checkersGradBox( in vec2 p, in vec2 dpdx, in vec2 dpdy )
{
    // filter kernel
    vec2 w = abs(dpdx)+abs(dpdy) + 0.001;
    // analytical integral (box filter)
    vec2 i = 2.0*(abs(fract((p-0.5*w)*0.5)-0.5)-abs(fract((p+0.5*w)*0.5)-0.5))/w;
    // xor pattern
    return 0.5 - 0.5*i.x*i.y;                  
}""")

getMaterial = register_shader_module("""
@name getMaterial_v1
@inputs m, pos, ro, rd, rdx, rdy
@outputs mat
@dependencies checkersGradBox_v1
@vardeps _COLOR_FACTOR
struct Material {
    vec3 albedo;
    float ks;
};

// Choose material properties based on hit id
Material getMaterial(float m, vec3 pos, vec3 ro, vec3 rd, vec3 rdx, vec3 rdy) {
    Material mat;
    if (m < 1.5) {
        // Floor checker
        vec3 dpdx = ro.y * (rd / rd.y - rdx / rdx.y);
        vec3 dpdy = ro.y * (rd / rd.y - rdy / rdy.y);
        float f = checkersGradBox(3.0 * pos.xz, 3.0 * dpdx.xz, 3.0 * dpdy.xz);
        mat.albedo = vec3(0.15) + f * vec3(0.05);
        mat.ks     = 0.4;
    } else {
        // Object color
        mat.albedo = 0.4 + 0.2 * sin(m * _COLOR_FACTOR + vec3(0.0, 1.0, 2.0));
        mat.ks     = 1.0;
    }
    return mat;
}""")

calcLighting = register_shader_module("""
@name calcLighting_v1
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies calcAO_v1, calcSoftShadow_v1
@vardeps _ZERO

// Compute lighting for a hit
vec3 calcLighting(vec3 pos, vec3 nor, vec3 ref, vec3 rd, Material mat, vec3 lig) {
    float occ = calcAO(pos, nor);
    vec3 lin = vec3(0.0);

    // Sun light
    // vec3 lig = normalize(vec3(-0.5, 0.4, -0.6));
    vec3 hal = normalize(lig - rd);
    float dif = clamp(dot(nor, lig), 0.0, 1.0);
    dif *= calcSoftShadow(pos, lig, 0.02, 2.5);
    float spe = pow(clamp(dot(nor, hal), 0.0, 1.0), 16.0);
    spe *= dif * (0.04 + 0.96 * pow(clamp(1.0 - dot(hal, lig), 0.0, 1.0), 5.0));
    lin += mat.albedo * 2.2 * dif * vec3(1.3, 1.0, 0.7);
    lin += 5.0 * spe * vec3(1.3, 1.0, 0.7) * mat.ks;

    // Sky light
    dif = sqrt(clamp(0.5 + 0.5 * nor.y, 0.0, 1.0));
    dif *= occ;
    spe = smoothstep(-0.2, 0.2, ref.y);
    spe *= dif * (0.04 + 0.96 * pow(clamp(1.0 + dot(nor, rd), 0.0, 1.0), 5.0));
    spe *= calcSoftShadow(pos, ref, 0.02, 2.5);
    lin += mat.albedo * 0.6 * dif * vec3(0.4, 0.6, 1.15);
    lin += 2.0 * spe * vec3(0.4, 0.6, 1.30) * mat.ks;

    // Back light
    dif = clamp(dot(nor, normalize(vec3(0.5, 0.0, 0.6))), 0.0, 1.0) * clamp(1.0 - pos.y, 0.0, 1.0);
    dif *= occ;
    lin += mat.albedo * 0.55 * dif * vec3(0.25);

    // Subsurface
    dif = pow(clamp(1.0 + dot(nor, rd), 0.0, 1.0), 2.0);
    dif *= occ;
    lin += mat.albedo * 0.25 * dif;

    return lin;
}""")

render = register_shader_module("""
@name render_v1
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_v1, calcNormal_v1, calcLighting_v1, getMaterial_v1
@vardeps _ZERO

// Cleaned-up render function
vec3 render(in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy, vec3 lig) {
    // Background
    vec3 bg = vec3(0.7, 0.7, 0.9) - max(rd.y, 0.0) * 0.3;

    // Raycast
    vec2 hit = raycast(ro, rd);
    if (hit.x < 0.0) return bg;

    float t  = hit.x;
    float m  = hit.y;
    vec3  pos = ro + rd * t;
    vec3  nor = (m < 1.5) ? vec3(0.0, 1.0, 0.0) : calcNormal(pos);
    vec3  ref = reflect(rd, nor);

    // Material determination
    Material mat = getMaterial(m, pos, ro, rd, rdx, rdy);

    // Lighting
    vec3 color = calcLighting(pos, nor, ref, rd, mat, lig);

    // Fog
    float fogFactor = 1.0 - exp(-0.0001 * t * t * t);
    return mix(color, bg, fogFactor);
}""")

dot2 = register_shader_module("""
@name dot2
@inputs v
@outputs res
@dependencies
float dot2( in vec2 v ) { return dot(v,v); }
float dot2( in vec3 v ) { return dot(v,v); }
""")

ndot = register_shader_module("""
@name ndot
@inputs a, b
@outputs res
@dependencies
float ndot( in vec2 a, in vec2 b ) { return a.x*b.x - a.y*b.y; }
""")

cro = register_shader_module("""
@name cro
@inputs v1, v2
@outputs res
@dependencies
float cro(vec2 v1, vec2 v2) {
    return v1.x * v2.y - v1.y * v2.x;
}""")

