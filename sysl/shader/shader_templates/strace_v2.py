
credits = """
// This is derived from shadertoy code at: https://www.shadertoy.com/view/Xds3zN
// Original Author: Inigo Quilez
"""
from ..shader_module import register_shader_module, SMMap
from string import Template
import numpy as np


def mainImageRGB_factor():
    mainImageRGB = SMMap['mainImage_v1']()
    mainImageRGB.name = "mainImage_v2"
    mainImageRGB.dependencies = ["setCamera_v1", "getSunDirection_v1", "render_v2"]
    return mainImageRGB
SMMap['mainImage_v2'] = mainImageRGB_factor


raycast = register_shader_module("""
@name raycast_v2
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO
@vardeps _RAYCAST_MAX_STEPS, _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec4 raycast(in vec3 ro, in vec3 rd) {

    vec4 res = vec4(-1.0);

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
            res.x = tp;
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
            vec4 h = SCENE_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001) {
                res = vec4(t, h.yzw);
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }

    return res;
}""")

getMaterial = register_shader_module("""
@name getMaterial_v2
@inputs m, pos, ro, rd, rdx, rdy
@outputs mat
@dependencies checkersGradBox_v1
struct Material {
    vec3 albedo;
    float ks;
};

// Choose material properties based on hit id
Material getMaterial(vec3 m, vec3 pos, vec3 ro, vec3 rd, vec3 rdx, vec3 rdy) {
    Material mat;
    if (m.x < -0.5) {
        // Floor checker
        vec3 dpdx = ro.y * (rd / rd.y - rdx / rdx.y);
        vec3 dpdy = ro.y * (rd / rd.y - rdy / rdy.y);
        float f = checkersGradBox(3.0 * pos.xz, 3.0 * dpdx.xz, 3.0 * dpdy.xz);
        mat.albedo = vec3(0.15) + f * vec3(0.05);
        mat.ks     = 0.4;
    } else {
        // Object color
        m = clamp(m, 0.0, 1.0);
        mat.albedo = m;
        mat.ks     = 1.0;
    }
    return mat;
}""")


render = register_shader_module("""
@name render_v2
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_v2, calcNormal_v1, calcLighting_v1, getMaterial_v2
@vardeps _ZERO

// Cleaned-up render function
vec3 render(in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy, vec3 lig) {
    // Background
    vec3 bg = vec3(0.7, 0.7, 0.9) - max(rd.y, 0.0) * 0.3;

    // Raycast
    vec4 hit = raycast(ro, rd);
    if (hit.x < 0.0) return bg;

    float t  = hit.x;
    vec3 m  = vec3(hit.yzw);
    vec3  pos = ro + rd * t;
    //vec3  nor = calcNormal(pos);
    vec3  nor = (m.x < 0.0) ? vec3(0.0, 1.0, 0.0) : calcNormal(pos);
    vec3  ref = reflect(rd, nor);

    // Material determination
    Material mat = getMaterial(m, pos, ro, rd, rdx, rdy);

    // Lighting
    vec3 color = calcLighting(pos, nor, ref, rd, mat, lig);

    // Fog
    float fogFactor = 1.0 - exp(-0.0001 * t * t * t);
    return mix(color, bg, fogFactor);
}""")
