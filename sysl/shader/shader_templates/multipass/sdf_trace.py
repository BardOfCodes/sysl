
credits = """
// This is derived from shadertoy code at: https://www.shadertoy.com/view/Xds3zN
// Original Author: Inigo Quilez
"""

from ...shader_module import register_shader_module
from string import Template
import numpy as np
from ..common import CONSTANTS

CONSTANTS.update({
    "_CONSERVATIVE_STEP_DIST": ("float", 0.99),
})

mainImage = register_shader_module("""
@name main_sdf_trace
@inputs fragColor, fragCoord
@outputs fragColor
@dependencies setCamera_v1, raycast_sdf_trace
@vardeps _AA, cameraOrigin, cameraDistance, cameraAngleX, cameraAngleY, resolution, _FOCAL_LENGTH, _ZERO
// We Ray trace and store the distance travelled in a float FBO 
// Technically when we actually do AA we need to save a bigger buffer - not average it out.
void main_sdf_trace( out vec4 fragColor, in vec2 fragCoord )
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
    vec2 p = (2.0*(fragCoord)-resolution.xy)/resolution.xy;

    vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

    // render	
    vec2 trace_result = raycast_sdf_trace(ro, rd);
    
    // TODO: optionally introduce other post processing steps here.

    
    fragColor = vec4(trace_result.x, trace_result.y, 0.0, 1.0);  // Only .r will be stored in R32F FBO
}""")

raycast_sdf_trace = register_shader_module("""
@name raycast_sdf_trace
@inputs ro, rd
@outputs res
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _CONSERVATIVE_STEP_DIST
@vardeps _RAYCAST_MAX_STEPS, _ADD_FLOOR_PLANE, _RAYCAST_CONSERVATIVE_STEPPING_RATE, _SHADOW_MAX_STEPS

// Cleaned-up render function
vec2 raycast_sdf_trace(in vec3 ro, in vec3 rd) {
    // Raycast
    vec2 res = vec2(0.0, -1.0);

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
        if (tp > 0.0) {
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
    res.x *= _CONSERVATIVE_STEP_DIST;
    return res;
}""")

