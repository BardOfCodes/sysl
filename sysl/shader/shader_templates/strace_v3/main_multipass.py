# Get two functions -> Sphere Trace, 
import numpy as np
from string import Template
from ...shader_module import register_shader_module, SMMap
from ...shader_mod_ext import CustomFunctionShaderModule
from ..common import CONSTANTS


mainImageBaseTemplate = Template("""
${offsets_fill}
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

    ${p_code}

    vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );

    vec3 rgb = ShadeRayPostTrace(sun, ro, rd, s, dist);
    rgb = ToneMapping(rgb);

    
    color = vec4( rgb, 1.0 );
}
""")

p_code_AA_1 = """
    vec2 p = (2.0*(pxy)-resolution.xy)/resolution.xy;
"""
p_code_AA_N = Template("""
    vec2 baseRes = ${base_res_factor} * resolution.xy;          // (W, H)
    vec2 qFloat  = floor(pxy / baseRes);  
    int sampleIdx = int(qFloat.x) + ${aa_amount} * int(qFloat.y);
    vec2 pxy_local = pxy - qFloat * baseRes;     // local pixel inside quadrant
    vec2 jitterPx = OFFS[sampleIdx];
    vec2 p = ((pxy_local + jitterPx) * 2.0 - baseRes) / baseRes;
""")

offset_template = Template("""
const vec2 OFFS[${num_samples}] = vec2[${num_samples}](
${offsets_array}
);
""")

class mainImagePostTrace(CustomFunctionShaderModule):
    def __init__(self, name=None, template=None, *args, **kwargs):
        if template is None:
            template = mainImageBaseTemplate
        if name is None:
            name = "mainImage_post_trace_v3"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["setCamera_v1", "LightPackage", "ShadeRayPostTrace", "ToneMapping", "BasicSun"]
        self.vardeps = ["cameraDistance", "cameraOrigin", "cameraAngleX", "cameraAngleY", "resolution", "_FOCAL_LENGTH", "_ZERO", "_AA"]
        self.inputs = ["color", "fragCoord", "resolution", "ca", "lig"]
        self.outputs = ["color"]
        self.aa = 1

    def register_hit(self, *args, **kwargs):
        aa_amount = int(kwargs.get("AA", None))
        assert aa_amount is not None, "AA is required"
        self.aa = aa_amount
        
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        assert self.hit_count == 1, "Only one AA pass is valid"
        aa_amount = self.aa
        num_samples = aa_amount * aa_amount
        if aa_amount == 1:
            p_code = p_code_AA_1
        else:
            p_code = p_code_AA_N.substitute(base_res_factor=f"{1.0 / aa_amount:.15f}", aa_amount=aa_amount)
        
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

SMMap["mainImage_post_trace_v3"] = mainImagePostTrace



ShadeRayPostTrace = register_shader_module("""
@name ShadeRayPostTrace
@inputs ro, rd, dist
@outputs color
@dependencies LightPackage, SphereTracePostTrace, SphereTraceGeom, background, SCENE_NORMAL_GEOM, SCENE_MATERIAL
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
    vec2 res = SphereTracePostTrace(ro, rd, 100.0, hit, s, dist);
    float t = res.x;
    steps += s;

    // Position 
    vec3 pt = ro + t * rd;

    if (!hit)
        return background(rd, sun);

    // Compute normal
    vec3 n = SCENE_NORMAL_GEOM(pt);

    // Shade object with light
    Material mat = SCENE_MATERIAL(pt, n, res.y);
    vec3 reflect_dir = reflect(rd, n);
    vec3 clearcoat = vec3(0);
    vec3 reflection;

    // reflection
    if (mat.clearcoat > 0.0 || mat.roughness == 0.0) {

        // secondary ray
        s = 0;
        res = SphereTraceGeom(pt+n*0.0001, reflect_dir, 100.0, hit, s);
        t = res.x;
        steps += s;

        if (hit) {
            vec3 rpt = pt + t * reflect_dir;
            vec3 rn = SCENE_NORMAL_GEOM(rpt);
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


SphereTracePostTrace = register_shader_module("""
@name SphereTracePostTrace
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec2 SphereTracePostTrace(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s, float dist){

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

    float tmin = max(dist, t0);
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

SphereTraceGeom = register_shader_module("""
@name SphereTraceGeom
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies GEOM_EXPRESSION, SCENE_EXPRESSION
@vardeps _SCENE_RADIUS, _SCENE_BOX_CENTER, _SCENE_BOX_SIZE, _ZERO, _RAYCAST_MAX_STEPS, 
@vardeps  _RAYCAST_CONSERVATIVE_STEPPING_RATE
vec2 SphereTraceGeom(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s){

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
    float t = 0.0;
    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);

        // 4) Ray‐march only in [tmin, tmax]
        t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            vec2 h = GEOM_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001) {
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


SCENE_NORMAL_GEOM = register_shader_module("""
@name SCENE_NORMAL_GEOM
@inputs p
@outputs color
@dependencies GEOM_EXPRESSION
@vardeps 
// Calculate object normal
// p : point
vec3 SCENE_NORMAL_GEOM(in vec3 p )
{
  float eps = 0.001;
  vec3 n;
  float v = GEOM_EXPRESSION(p).x;
  n.x = GEOM_EXPRESSION( vec3(p.x+eps, p.y, p.z) ).x - v;
  n.y = GEOM_EXPRESSION( vec3(p.x, p.y+eps, p.z) ).x - v;
  n.z = GEOM_EXPRESSION( vec3(p.x, p.y, p.z+eps) ).x - v;
  return normalize(n);
}""")
