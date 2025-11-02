credits = """
// This code is derived from https://www.shadertoy.com/view/3tKfDG
// Original Author: Jacquemet Matthieu
"""
import numpy as np
from string import Template
from ...shader_module import register_shader_module, SMMap
from ..common import CONSTANTS

CONSTANTS.update({
    "_EE": ("float", 1000.0),
})

MATPoint = register_shader_module("""
@name MATPoint
@inputs x, mat
@outputs mat
@dependencies BaseMaterials_v4
struct MATPoint {
    float x;
    Material mat;
};
""")


MaterialV4 = register_shader_module("""
@name MaterialV4
@inputs albedo, emissive, mrc
@outputs mat
@dependencies BaseMaterials_v4
@vardeps 
Material MaterialV4(vec3 albedo, vec3 emissive, vec3 mrc)
{   
    Material mat;
    mat.albedo = albedo;
    mat.emissive = emissive;
    mat.mrc = mrc;
    return mat;
}
""")

SMPLMaterialV4 = register_shader_module("""
@name SMPLMaterialV4
@inputs albedo, emissive, mrc
@outputs mat
@dependencies BaseMaterials_v4
@vardeps 
Material SMPLMaterialV4(vec3 albedo, vec2 mr)
{   
    Material mat;
    mat.albedo = albedo;
    mat.emissive = vec3(0.0);
    mat.mrc.z = 0.0;
    mat.mrc.xy = mr;
    return mat;
}
""")

background_v4 = register_shader_module("""
@name background_v4
@inputs r, sun
@outputs color
@dependencies LightPackage_v4 
@vardeps 
vec3 background(vec3 r, DirectionalLight sun)
{
    return Sky(sun, r);
    // return mix(vec3(0.452,0.551,0.995),vec3(0.652,0.697,0.995), d.z*0.5+0.5);
}
""")

mainImage = register_shader_module("""
@name mainImage_v4
@inputs color, fragCoord, resolution, ca, lig
@outputs color
@dependencies  setCamera_v1, LightPackage_v4, ShadeRay_v4, ToneMapping, BasicSun_v4
@vardeps cameraDistance, cameraOrigin, cameraAngleX, cameraAngleY, resolution
@vardeps _FOCAL_LENGTH, _ZERO, _AA
void mainImage(out vec4 color, in vec2 pxy )
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

    // Shade background
    DirectionalLight sun = BasicSun();
    int s = 0;
    for( int m=_ZERO; m<_AA; m++ )
    for( int n=_ZERO; n<_AA; n++ )
    {
        // pixel coordinates
        vec2 o = vec2(float(m),float(n)) / float(_AA) - 0.5;

        vec2 p = (2.0*(pxy+o)-resolution.xy)/resolution.xy;

        vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

        vec3 rgb = ShadeRay_v4(sun, ro, rd, s);
        rgb = ToneMapping(rgb);
        tot += rgb;
    }

    tot /= float(_AA*_AA);
    
    color = vec4( tot, 1.0 );
}
""")


ShadeRay_v4 = register_shader_module("""
@name ShadeRay_v4
@inputs sun, sky
@outputs color
@dependencies LightPackage_v4, SphereTrace_v4, background_v4, SCENE_NORMAL, SCENE_MATERIAL, MATPoint
@vardeps 
// LightPackage funccalls - DirectionLight, Sky, Env, Shadow, Shade, SkyAmbient
// Background color
// Sample color from ray
// sun : Sun light
// ro : Ray origin
// rd : Ray direction
// steps : Number of trace steps
vec3 ShadeRay_v4(DirectionalLight sun, vec3 ro, vec3 rd, out int steps) {

    // Hit and number of steps
    bool hit = false;
    int s = 0;
    
    // primary ray
    MATPoint res = SphereTrace(ro, rd, 100.0, hit, s);
    float t = res.x;
    Material mat = res.mat;
    steps += s;

    // Position 
    vec3 pt = ro + t * rd;

    if (!hit)
        return background(rd, sun);

    // Compute normal
    vec3 n = SCENE_NORMAL(pt);

    // Shade object with light
    vec3 reflect_dir = reflect(rd, n);
    vec3 clearcoat = vec3(0);
    vec3 reflection;

    // reflection
    if (mat.mrc.z > 0.0 || mat.mrc.y == 0.0) {

        // secondary ray
        s = 0;
        res = SphereTrace(pt+n*0.01, reflect_dir, 100.0, hit, s);
        t = res.x;
        steps += s;

        if (hit) {
            vec3 rpt = pt + t * reflect_dir;
            vec3 rn = SCENE_NORMAL(rpt);
            vec3 sec_reflection = Env(reflect(reflect_dir, rn), sun);
            clearcoat = Shade(sun, res.mat, rpt, reflect_dir, rn, 
                            sec_reflection, sec_reflection*mat.mrc.z);
        } else
            clearcoat = Env(reflect_dir, sun);
    }
    if (mat.mrc.y == 0.0)
        reflection = clearcoat;
    else {
        float r = 1.0/max(mat.mrc.y, 0.00001);
        float v = Shadow(pt+n*0.1, reflect_dir, 1000.0, r);
        reflection = mix(SkyAmbient(sun)*0.1, Env(reflect_dir, sun), v);
    }


    clearcoat *= mat.mrc.z;

    return Shade(sun, mat, pt, rd, n, reflection, clearcoat);
}""")

CONSTANTS.update({
    "_ST_EPSILON": ("float", 0.0001),
})

SphereTrace_v4 = register_shader_module("""
@name SphereTrace_v4
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION, MatFloor_v4
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
MATPoint SphereTrace(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s){

    MATPoint res;
    res.x = -1.0;

    // 1) Sphere cull: cheap dot/mul vs. complex SDF
    float b = dot(ro, ro) - _SCENE_RADIUS*_SCENE_RADIUS;
    float c = dot(ro, rd);
    float disc = c*c - b;
    if (disc <= 0.0) {
        _h = false;
        _s = 0;
        return res;
    }
    // no intersection with sphere
    float s   = sqrt(disc);
    float t0  = -c - s;
    float t1  = -c + s;
    if (t1 < 0.0) {
        _h = false;
        _s = 0;
        return res;
    }                   // both intersections behind camera

    float tmin = max(1.0, t0);
    float tmax = min(20.0, t1);

    // 2) Floor-plane (y=0) test
    // MAKE THIS OPTIONAL.
    if (_ADD_FLOOR_PLANE) {
        float tp = -ro.y / rd.y;
        if (tp > 0.0 && tp < tmax) {
            tmax = tp;
            res.x = tp;
            _h = true;
            _s = 0;
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
            MATPoint h = SCENE_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001) {
                res.x = t;
                res.mat = h.mat;
                _h = true;
                _s = i;
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }

    return res;
}""")

