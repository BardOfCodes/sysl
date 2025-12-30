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

mainImage = register_shader_module("""
@name mainImage_v3
@inputs color, fragCoord, resolution, ca, lig
@outputs color
@dependencies  setCamera_v1, LightPackage, ShadeRay, ToneMapping, BasicSun
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

        vec3 rgb = ShadeRay(sun, ro, rd, s);
        rgb = ToneMapping(rgb);
        tot += rgb;
    }

    tot /= float(_AA*_AA);
    
    color = vec4( tot, 1.0 );
}
""")

background = register_shader_module("""
@name background
@inputs r, sun
@outputs color
@dependencies LightPackage 
@vardeps 
vec3 background(vec3 r, DirectionalLight sun)
{
    return Sky(sun, r);
    // return mix(vec3(0.452,0.551,0.995),vec3(0.652,0.697,0.995), d.z*0.5+0.5);
}
""")

ShadeRay = register_shader_module("""
@name ShadeRay
@inputs sun, sky
@outputs color
@dependencies LightPackage, SphereTrace, background, SCENE_NORMAL, SCENE_MATERIAL
@vardeps 
// LightPackage funccalls - DirectionLight, Sky, Env, Shadow, Shade, SkyAmbient
// Background color
// Sample color from ray
// sun : Sun light
// ro : Ray origin
// rd : Ray direction
// steps : Number of trace steps
vec3 ShadeRay(DirectionalLight sun, vec3 ro, vec3 rd, out int steps) {

    // Hit and number of steps
    bool hit = false;
    int s = 0;
    
    // primary ray
    vec2 res = SphereTrace(ro, rd, 100.0, hit, s);
    float t = res.x;
    steps += s;

    // Position 
    vec3 pt = ro + t * rd;

    if (!hit)
        return background(rd, sun);

    // Compute normal
    // vec3 n = SCENE_NORMAL(pt);
    vec3 n = (res.y < 0.0) ? vec3(0.0, 1.0, 0.0) : SCENE_NORMAL(pt);

    // Shade object with light
    Material mat = SCENE_MATERIAL(pt, n, res.y);
    vec3 reflect_dir = reflect(rd, n);
    vec3 clearcoat = vec3(0);
    vec3 reflection;

    // reflection
    if (mat.clearcoat > 0.0 || mat.roughness == 0.0) {

        // secondary ray
        s = 0;
        res = SphereTrace(pt+n*0.0001, reflect_dir, 100.0, hit, s);
        t = res.x;
        steps += s;

        if (hit) {
            vec3 rpt = pt + t * reflect_dir;
            //vec3 rn = SCENE_NORMAL(rpt);
            vec3 rn = (res.y <= 0.0) ? vec3(0.0, 1.0, 0.0) : SCENE_NORMAL(rpt);
            Material rmat = SCENE_MATERIAL(rpt, rn, res.y);

            vec3 sec_reflection = Env(reflect(reflect_dir, rn), sun);
            clearcoat = Shade(sun, rmat, rpt, reflect_dir, rn, 
                            sec_reflection, sec_reflection*mat.clearcoat);
        } else
            clearcoat = Env(reflect_dir, sun);
    }
    if (mat.roughness == 0.0)
        reflection = clearcoat;
    else {
        float r = 1.0/max(mat.roughness, 0.00001);
        float v = Shadow(pt+n*0.0001, reflect_dir, 1000.0, r);
        reflection = mix(SkyAmbient(sun)*0.1, Env(reflect_dir, sun), v);
    }


    clearcoat *= mat.clearcoat;

    return Shade(sun, mat, pt, rd, n, reflection, clearcoat);
}""")

CONSTANTS.update({
    "_ST_EPSILON": ("float", 0.0001),
})

SphereTrace = register_shader_module("""
@name SphereTrace
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec2 SphereTrace(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s){

    vec2 res = vec2(-1.0,-1.0);

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
            if (abs(h.x) < 0.0001) {
                res = vec2(t, h.y);
                _h = true;
                _s = i;
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }

    return res;
}""")


SCENE_NORMAL = register_shader_module("""
@name SCENE_NORMAL
@inputs p
@outputs color
@dependencies SCENE_EXPRESSION
@vardeps 
// Calculate object normal
// p : point
vec3 SCENE_NORMAL(in vec3 p )
{
  float eps = 0.001;
  vec3 n;
  float v = SCENE_EXPRESSION(p).x;
  n.x = SCENE_EXPRESSION( vec3(p.x+eps, p.y, p.z) ).x - v;
  n.y = SCENE_EXPRESSION( vec3(p.x, p.y+eps, p.z) ).x - v;
  n.z = SCENE_EXPRESSION( vec3(p.x, p.y, p.z+eps) ).x - v;
  return normalize(n);
}""")
