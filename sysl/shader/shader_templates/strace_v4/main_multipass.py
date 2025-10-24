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


mainImage_post_trace = register_shader_module("""
@name mainImage_post_trace_v4
@inputs color, fragCoord, resolution, ca, lig
@outputs color
@dependencies  setCamera_v1, LightPackage_v4, ShadeRayPostTrace_v4, ToneMapping, BasicSun_v4
@vardeps cameraDistance, cameraOrigin, cameraAngleX, cameraAngleY, resolution
@vardeps _FOCAL_LENGTH, _ZERO, _AA
void mainImage_post_trace(out vec4 color, in vec2 pxy )
{

    float dist = texelFetch(distance_travelled, ivec2(pxy), 0).r;
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

    // Shade background
    DirectionalLight sun = BasicSun();
    int s = 0;
    vec2 p = (2.0*(pxy)-resolution.xy)/resolution.xy;

    vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

    vec3 rgb = ShadeRayPostTrace(sun, ro, rd, s, dist);
    rgb = ToneMapping(rgb);

    
    color = vec4( rgb, 1.0 );
}
""")


ShadeRayPostTrace_v4 = register_shader_module("""
@name ShadeRayPostTrace_v4
@inputs sun, sky
@outputs color
@dependencies LightPackage_v4, SphereTracePostTrace_v4, SphereTraceGeom_v4, background_v4, SCENE_NORMAL_GEOM, MATPoint
@vardeps 
// LightPackage funccalls - DirectionLight, Sky, Env, Shadow, Shade, SkyAmbient
// Background color
// Sample color from ray
// sun : Sun light
// ro : Ray origin
// rd : Ray direction
// steps : Number of trace steps
vec3 ShadeRayPostTrace(DirectionalLight sun, vec3 ro, vec3 rd, out int steps, float dist) {

    // Hit and number of steps
    bool hit = false;
    int s = 0;
    
    // primary ray
    MATPoint res = SphereTracePostTrace(ro, rd, 100.0, hit, s, dist);
    float t = res.x;
    Material mat = res.mat;
    steps += s;

    // Position 
    vec3 pt = ro + t * rd;

    if (!hit)
        return background(rd, sun);

    // Compute normal
    vec3 n = SCENE_NORMAL_GEOM(pt);

    // Shade object with light
    vec3 reflect_dir = reflect(rd, n);
    vec3 clearcoat = vec3(0);
    vec3 reflection;

    // reflection
    if (mat.mrc.z > 0.0 || mat.mrc.y == 0.0) {

        // secondary ray
        s = 0;
        res = SphereTraceGeom(pt+n*0.01, reflect_dir, 100.0, hit, s);
        t = res.x;
        steps += s;

        if (hit) {
            vec3 rpt = pt + t * reflect_dir;
            vec3 rn = SCENE_NORMAL_GEOM(rpt);
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

SphereTracePostTrace_v4 = register_shader_module("""
@name SphereTracePostTrace_v4
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION, MatFloor_v4
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
MATPoint SphereTracePostTrace(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s, float dist){

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

    float tmin = max(max(1.0, t0), dist);
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
            if (abs(h.x) < 0.0001 * t) {
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


SphereTraceGeom_v4 = register_shader_module("""
@name SphereTraceGeom_v4
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies GEOM_EXPRESSION, SCENE_EXPRESSION, MatFloor_v4
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
MATPoint SphereTraceGeom(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s){

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
    float t = 0.0;
    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            vec2 h = GEOM_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001 * t) {
                _h = true;
                _s = i;
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }
    res = SCENE_EXPRESSION(ro + rd * t);
    return res;
}""")


