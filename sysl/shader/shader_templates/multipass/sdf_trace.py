
credits = """
// This is derived from shadertoy code at: https://www.shadertoy.com/view/Xds3zN
// Original Author: Inigo Quilez
"""

from ...shader_module import register_shader_module, SMMap
from ...shader_mod_ext import CustomFunctionShaderModule
from string import Template
import numpy as np
from ..common import CONSTANTS

CONSTANTS.update({
    "_CONSERVATIVE_STEP_DIST": ("float", 1.0),
})

mainSDFTraceBaseTemplate = Template("""
vec2 octEncode(vec3 n) {
    n /= (abs(n.x) + abs(n.y) + abs(n.z));
    vec2 e = n.xy;
    if (n.z < 0.0) e = (1.0 - abs(e.yx)) * sign(e.xy);
    return e; // in [-1,1]
}

${offsets_fill}
void main_sdf_trace( out vec4 fragColor, in vec2 fragCoord )
{
    // camera	
    vec3 ta = vec3( 0.0, 1.0, -0.0 ) + cameraOrigin;
    vec3 ro = ta + cameraDistance * vec3(
        cos(cameraAngleX) * sin(cameraAngleY), // X component
        sin(cameraAngleX),                     // Y component (elevation)
        cos(cameraAngleX) * cos(cameraAngleY)  // Z component
    );
    // camera-to-world transformation
    mat3 ca = setCamera( ro, ta, 0.0 );

    ${p_code}

    vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

    // render	
    vec2 trace_result = raycast_sdf_trace(ro, rd);
    vec3  pos = ro + rd * trace_result.x;
    vec3  nor = calcNormal(pos);
    vec2 enc = octEncode(nor) * 0.5 + 0.5;
    
    fragColor = vec4(trace_result.x, trace_result.y, enc.x, enc.y); 
}""")

p_code_AA_1 = """
    vec2 p = (2.0*(fragCoord)-resolution.xy)/resolution.xy;
"""

p_code_AA_N = Template("""
    // -----------------------------
    // 0) Atlas / quadrant bookkeeping
    // -----------------------------
    vec2 baseRes = ${base_res_factor} * resolution.xy;               // size of ONE sub-image (W,H)
    vec2 qFloat   = floor(fragCoord / baseRes);       // (0..${aa_amount_minus_one}, 0..${aa_amount_minus_one})
    ivec2 q       = ivec2(qFloat);
    int sampleIdx = q.x + ${aa_amount} * q.y;                    // 0..${num_samples_minus_one}

    // Local pixel coords inside the sub-image
    vec2 localFrag = fragCoord - qFloat * baseRes;    // [0..W) x [0..H)

    // -----------------------------
    // 1) Sub-pixel jitter (in pixel units)
    //    You can tweak +/-0.25 to taste; +/-0.5 is full pixel diagonals.
    // -----------------------------
    vec2 jitterPx = OFFS[sampleIdx];

    // -----------------------------
    // 2) Ray for this "sub-image" (normalize using baseRes)
    //    NOTE: normalize NDC using baseRes, not full resolution
    // -----------------------------
    vec2 p = ((localFrag + jitterPx) * 2.0 - baseRes) / baseRes;   // [-1,1] in sub-image
""")

offset_template = Template("""
const vec2 OFFS[${num_samples}] = vec2[${num_samples}](
${offsets_array}
);
""")

class mainSDFTrace(CustomFunctionShaderModule):
    def __init__(self, name=None, template=None, *args, **kwargs):
        if template is None:
            template = mainSDFTraceBaseTemplate
        if name is None:
            name = "main_sdf_trace"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["setCamera_v1", "raycast_sdf_trace", "calcNormal_v1", ]
        self.vardeps = ["_AA", "cameraOrigin", "cameraDistance", "cameraAngleX", "cameraAngleY", "resolution", "_FOCAL_LENGTH", "_ZERO"]
        self.inputs = ["fragColor", "fragCoord"]
        self.outputs = ["fragColor"]
        self.aa = 1

    def register_hit(self, *args, **kwargs):
        aa_amount = int(kwargs.get("AA", None))
        assert aa_amount is not None, "AA is required"
        self.aa = aa_amount
        
        self.hit_count += 1

    def generate_code(self):
        assert self.hit_count == 1, "Only one AA pass is valid"
        aa_amount = self.aa
        num_samples = aa_amount * aa_amount
        
        if aa_amount == 1:
            p_code = p_code_AA_1
        else:
            p_code = p_code_AA_N.substitute(
                base_res_factor=f"{1.0 / aa_amount:.15f}",
                aa_amount=aa_amount,
                aa_amount_minus_one=aa_amount - 1,
                num_samples_minus_one=num_samples - 1
            )
        
        # Generate offsets array
        # For AA=n, we create an n×n grid of offsets
        # Offset pattern: for position (i, j) in grid, offset = ((i + 0.5) / n - 0.5, (j + 0.5) / n - 0.5)
        offsets = []
        for y in range(aa_amount):
            for x in range(aa_amount):
                offset_x = (x + 0.5) / aa_amount - 0.5
                offset_y = (y + 0.5) / aa_amount - 0.5
                sign_x = "+" if offset_x >= 0 else ""
                sign_y = "+" if offset_y >= 0 else ""
                offsets.append(f"    vec2({sign_x}{offset_x:.6f}, {sign_y}{offset_y:.6f})")
        
        offsets_array = ",\n".join(offsets)
        if aa_amount == 1:
            offsets_fill = ""
        else:
            offsets_fill = offset_template.substitute(num_samples=num_samples, offsets_array=offsets_array)
        
        final_code_str = self.template.substitute(p_code=p_code, offsets_fill=offsets_fill)
        self.code = final_code_str

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


SMMap["main_sdf_trace"] = mainSDFTrace



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
            if (abs(h.x) < 0.0001) {
                res = vec2(t, h.y);
                break;
            }
            t += h.x * _RAYCAST_CONSERVATIVE_STEPPING_RATE;
        }
    }
    res.x *= _CONSERVATIVE_STEP_DIST;
    return res;
}""")
