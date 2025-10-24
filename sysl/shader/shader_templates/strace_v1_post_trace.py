
from ..shader_module import register_shader_module, SMMap
from string import Template
import numpy as np


raycast_post_trace = register_shader_module("""
@name raycast_post_trace
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO
@vardeps _RAYCAST_MAX_STEPS, _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec2 raycast_post_trace(in vec3 ro, in vec3 rd, float dist) {

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

    float tmin = max(dist, t0);
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


render_post_trace = register_shader_module("""
@name render_post_trace
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_post_trace, calcNormal_v1, calcLighting_v1, getMaterial_v1
@vardeps _ZERO

// Cleaned-up render function
vec3 render_post_trace(in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy, vec3 lig, float dist) {
    // Background
    vec3 bg = vec3(0.7, 0.7, 0.9) - max(rd.y, 0.0) * 0.3;

    // Raycast
    vec2 hit = raycast_post_trace(ro, rd, dist);
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

mainImage_post_trace = register_shader_module("""
@name mainImage_post_trace_v1
@inputs fragColor, fragCoord
@outputs fragColor
@dependencies setCamera_v1, getSunDirection_v1, render_post_trace
@vardeps _AA, cameraOrigin, cameraDistance, cameraAngleX, cameraAngleY, resolution, _FOCAL_LENGTH, _ZERO
void mainImage_post_trace( out vec4 fragColor, in vec2 fragCoord )
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
    float dist = texelFetch(distance_travelled, ivec2(fragCoord), 0).r;

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
        vec3 start_pos = ro;
        vec3 col = render_post_trace( start_pos, rd, rdx, rdy , lig, dist);
        
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


raycast_post_trace_v2 = register_shader_module("""
@name raycast_post_trace_v2
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, _ADD_FLOOR_PLANE
vec4 raycast_post_trace_v2(in vec3 ro, in vec3 rd, float dist) {

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

    float tmin = max(dist, t0);
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
            if (abs(h.x) < 0.0001 * t) {
                res = vec4(t, h.yzw);
                break;
            }
            t += h.x;
        }
    }

    return res;
}""")

render_post_trace_v2 = register_shader_module("""
@name render_post_trace_v2
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_post_trace_v2, calcNormal_v1, calcLighting_v1, getMaterial_v2
@vardeps _ZERO

// Cleaned-up render function
vec3 render_post_trace(in vec3 ro, in vec3 rd, in vec3 rdx, in vec3 rdy, vec3 lig, float dist) {
    // Background
    vec3 bg = vec3(0.7, 0.7, 0.9) - max(rd.y, 0.0) * 0.3;

    // Raycast
    vec4 hit = raycast_post_trace_v2(ro, rd, dist);
    if (hit.x < 0.0) return bg;

    float t  = hit.x;
    vec3 m  = vec3(hit.yzw);
    vec3  pos = ro + rd * t;
    vec3  nor = calcNormal(pos);
    vec3  ref = reflect(rd, nor);

    // Material determination
    Material mat = getMaterial(m, pos, ro, rd, rdx, rdy);

    // Lighting
    vec3 color = calcLighting(pos, nor, ref, rd, mat, lig);

    // Fog
    float fogFactor = 1.0 - exp(-0.0001 * t * t * t);
    return mix(color, bg, fogFactor);
}""")


def mainImage_post_trace_RGB_factor():
    mainImageRGB = SMMap['mainImage_post_trace_v1']()
    mainImageRGB.name = "mainImage_post_trace_v2"
    mainImageRGB.dependencies = ["setCamera_v1", "getSunDirection_v1", "render_post_trace_v2"]
    return mainImageRGB
SMMap['mainImage_post_trace_v2'] = mainImage_post_trace_RGB_factor
