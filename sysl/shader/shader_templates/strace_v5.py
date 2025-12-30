CREDITS = """
// This is derived from shadertoy code at: https://www.shadertoy.com/view/ll33Wn
// Original Author: Dalton

"""
from ..shader_module import register_shader_module, SMMap
from .common import CONSTANTS

from string import Template
import numpy as np


CONSTANTS.update({
    "SHADE_COUNT": ("float", 4.0),
    "AMBIENT": ("float", 0.1),
})

CONSTANTS.update({
    "EDGE_THICKNESS": ("float", 0.00),
    "MAX_DIST": ("float", 100.0),
})

ColorToonShading = register_shader_module("""
@name ColorToonShading
@inputs pt_normal, lightDir, lightColor
@outputs color
@dependencies 
@vardeps SHADE_COUNT, AMBIENT
vec3 ColorToonShading(vec3 pt_normal, vec3 lightDir, vec3 lightColor)
{
    float intensity = dot(pt_normal, normalize(lightDir));
    intensity = ceil(intensity * SHADE_COUNT) / SHADE_COUNT;
    intensity = max(intensity, AMBIENT);
    vec3 color = lightColor * intensity;
    return color;
}""")

ShadeRay_v5 = register_shader_module("""
@name ShadeRay_v5
@inputs sun, sky
@outputs color
@dependencies LightPackage_v4, SphereTrace_v5, background_v4, SCENE_NORMAL, MATPoint, ColorToonShading
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
    MATPoint res = SphereTrace(ro, rd, 100.0, hit, s);
    float t = res.x;
    Material mat = res.mat;
    steps += s;

    if (res.x < -1.0)
    {
        return vec3(0.0);
    }
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
        res = SphereTrace(pt+n*0.0001, reflect_dir, 100.0, hit, s);
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
        float v = Shadow(pt+n*0.0001, reflect_dir, 1000.0, r);
        reflection = mix(SkyAmbient(sun)*0.1, Env(reflect_dir, sun), v);
    }


    clearcoat *= mat.mrc.z;

    vec3 color = Shade(sun, mat, pt, rd, n, reflection, clearcoat);
    color = ColorToonShading(n, sun.direction, color); // Toon shading:
    return color;
}""")

SphereTrace_v5 = register_shader_module("""
@name SphereTrace_v5
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION, MatFloor_v4
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _RAYCAST_CONSERVATIVE_STEPPING_RATE, MAX_DIST, EDGE_THICKNESS
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

    // 3) _AABB test
    vec3 inv_rd = 1.0 / rd;  // hoist reciprocal
    vec3 tA = ( _SCENE_BOX_CENTER - _SCENE_BOX_SIZE - ro ) * inv_rd;
    vec3 tB = ( _SCENE_BOX_CENTER + _SCENE_BOX_SIZE - ro ) * inv_rd;

    vec3 tMin3 = min(tA, tB);
    vec3 tMax3 = max(tA, tB);

    float tbmin = max( max(tMin3.x, tMin3.y), tMin3.z );
    float tbmax = min( min(tMax3.x, tMax3.y), tMax3.z );

    float edgeLength = MAX_DIST;

    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        float t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            MATPoint h = SCENE_EXPRESSION(ro + rd * t);
            edgeLength = min(h.x, edgeLength);
            if (abs(h.x) < 0.0001) {
                res.x = t;
                res.mat = h.mat;
                _h = true;
                _s = i;
                break;
            }
            if (h.x > edgeLength && edgeLength <= EDGE_THICKNESS) // Edge hit
            {
                res.x = -2.0;
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }

    return res;
}""")

def mainImage_v5_factor():
    mainImage = SMMap['mainImage_v4']()
    mainImage.name = "mainImage_v5"
    mainImage.dependencies = ["setCamera_v1", "LightPackage_v4", "ShadeRay_v5", "ToneMapping", "BasicSun_v4"]
    return mainImage
SMMap['mainImage_v5'] = mainImage_v5_factor



####### MULTIPASS SHADERS #######


ShadeRayPostTrace_v5 = register_shader_module("""
@name ShadeRayPostTrace_v5
@inputs sun, sky
@outputs color
@dependencies LightPackage_v4, SphereTracePostTrace_v5, SphereTraceGeom_v4, background_v4, SCENE_NORMAL_GEOM, MATPoint, ColorToonShading
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

    if (res.x < -1.0)
        return vec3(0.0);
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
        res = SphereTraceGeom(pt+n*0.0001, reflect_dir, 100.0, hit, s);
        //res = SphereTracePostTrace(pt+n*0.01, reflect_dir, 100.0, hit, s, 0.0);
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
        float v = Shadow(pt+n*0.0001, reflect_dir, 1000.0, r);
        reflection = mix(SkyAmbient(sun)*0.1, Env(reflect_dir, sun), v);
    }


    clearcoat *= mat.mrc.z;

    vec3 color = Shade(sun, mat, pt, rd, n, reflection, clearcoat);
    color = ColorToonShading(n, sun.direction, color); // Toon shading:
    return color;

}""")

SphereTracePostTrace_v5 = register_shader_module("""
@name SphereTracePostTrace_v5
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION, MatFloor_v4
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _RAYCAST_CONSERVATIVE_STEPPING_RATE, MAX_DIST, EDGE_THICKNESS
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

    // 3) _AABB test
    vec3 inv_rd = 1.0 / rd;  // hoist reciprocal
    vec3 tA = ( _SCENE_BOX_CENTER - _SCENE_BOX_SIZE - ro ) * inv_rd;
    vec3 tB = ( _SCENE_BOX_CENTER + _SCENE_BOX_SIZE - ro ) * inv_rd;

    vec3 tMin3 = min(tA, tB);
    vec3 tMax3 = max(tA, tB);

    float tbmin = max( max(tMin3.x, tMin3.y), tMin3.z );
    float tbmax = min( min(tMax3.x, tMax3.y), tMax3.z );
    
    float edgeLength = MAX_DIST;
    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        float t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            MATPoint h = SCENE_EXPRESSION(ro + rd * t);
            edgeLength = min(h.x, edgeLength);
            if (abs(h.x) < 0.0001) {
                res.x = t;
                res.mat = h.mat;
                _h = true;
                _s = i;
                break;
            }
            if (h.x > edgeLength && edgeLength <= EDGE_THICKNESS) // Edge hit
            {
                res.x = -2.0;
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }
    return res;
}""")




def mainImage_post_trace_v5_factor():
    mainImage_post_trace = SMMap['mainImage_post_trace_v4']()
    mainImage_post_trace.name = "mainImage_post_trace_v5"
    mainImage_post_trace.dependencies = ["setCamera_v1", "LightPackage_v4", "ShadeRayPostTrace_v5", "ToneMapping", "BasicSun_v4"]
    return mainImage_post_trace
SMMap['mainImage_post_trace_v5'] = mainImage_post_trace_v5_factor

