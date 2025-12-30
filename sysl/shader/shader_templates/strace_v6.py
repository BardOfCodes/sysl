
credits = """
// This is derived from shadertoy code at: https://www.shadertoy.com/view/33BXW3
// Original Author: 8InfinityTaco8
"""

from ..shader_module import register_shader_module, SMMap
from .multipass.sdf_trace import mainSDFTrace
from string import Template
import numpy as np
from .common import CONSTANTS
CONSTANTS.update({
    "DITHER_INTENSITY_FACTOR": ("float", 0.5), # from 0.5 to 1.5
    "OUTLINE_THICKNESS": ("float", 2.0),
})

DitherUtils = register_shader_module("""
@name DitherUtils_v6
@inputs 
@outputs dither
@dependencies raycast_v2
@vardeps _ZERO, OUTLINE_THICKNESS, resolution

// 4x4 Bayer matrix thresholds
float bayerThreshold(int x, int y) {
    int idx = x + y * 4;
    // Precomputed 4x4 Bayer thresholds normalized 0..1
    float m[16] = float[16](
        0.,  8.,  2., 10.,
        12., 4., 14.,  6.,
        3., 11.,  1.,  9.,
        15., 7., 13.,  5.
    );
    return m[idx] / 16.;
}

// Outline calculation - exactly as in original shader
float CalculateConstantOutline(vec3 ro, vec3 rd, float sceneDist) {
    // float sceneDist = raycast(ro, rd);
    float outline = 0.0;
    vec2 pixelSize = 1.0 / resolution.xy;
    vec3 offsets[4] = vec3[]( 
        vec3(pixelSize.x * OUTLINE_THICKNESS, 0, 0),
        vec3(-pixelSize.x * OUTLINE_THICKNESS, 0, 0),
        vec3(0, pixelSize.y * OUTLINE_THICKNESS, 0),
        vec3(0, -pixelSize.y * OUTLINE_THICKNESS, 0)
    );
    for (int i = 0; i < 4; i++) {
        vec3 offsetUV = vec3(rd.xy + offsets[i].xy, rd.z);
        vec3 offsetRd = normalize(offsetUV);
        float offsetDist = raycast(ro, offsetRd).x;
        outline += min(abs(sceneDist - offsetDist), 0.5);
    }
    return smoothstep(0.0, 1.0, outline);
}

""")

mainImage = register_shader_module("""
@name mainImage_v6
@inputs fragColor, fragCoord
@outputs fragColor
@dependencies setCamera_v1, getSunDirection_v1, render_v6, DitherUtils_v6
@vardeps _AA, cameraOrigin, cameraDistance, cameraAngleX, cameraAngleY, resolution, _FOCAL_LENGTH, _ZERO
@vardeps DITHER_INTENSITY_FACTOR
void mainImage( out vec4 fragColor, in vec2 fragCoord )
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


        // Dithering with light intensity - similar to original
        ivec2 pix = ivec2(mod(fragCoord.xy, 4.));
        
        // Adjust threshold based on slider (affects dithering intensity)
        float thresh = bayerThreshold(pix.x, pix.y) * DITHER_INTENSITY_FACTOR;
        
        // Compute luminance
        float luminance = dot(col, vec3(0.299, 0.587, 0.114));
        
        // Apply dithering - darker areas will have more black pixels
        float dither = luminance < thresh ? 0.0 : 1.0;
        col = vec3(dither) * col;

        tot += col;
    }
    tot /= float(_AA*_AA);
    
    fragColor = vec4( tot, 1.0 );
}""")


render = register_shader_module("""
@name render_v6
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_v2, calcNormal_v1, calcLighting_v6, getMaterial_v2, DitherUtils_v6
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
    // vec3 color = mat.albedo;
    float outline = CalculateConstantOutline(ro, rd, hit.x);
    // Apply outline directly as in original
    // gain
    // color = color*3.0/(2.5+color);
    
    // gamma
    color = pow( color, vec3(0.4545) );
    color = mix(color, vec3(0.0), outline);
    return color;
}""")


calcLighting_v6 = register_shader_module("""
@name calcLighting_v6
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
    lin += mat.albedo * 0.6 * dif * vec3(0.4, 0.6, 1.15);

    // spe = smoothstep(-0.2, 0.2, ref.y);
    // spe *= dif * (0.04 + 0.96 * pow(clamp(1.0 + dot(nor, rd), 0.0, 1.0), 5.0));
    // spe *= calcSoftShadow(pos, ref, 0.02, 2.5);
    // lin += 2.0 * spe * vec3(0.4, 0.6, 1.30) * mat.ks;

    return lin;
}""")

#### Multi-Shader Version

mainImage_post_trace_template = Template("""
${offsets_fill}
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
    // pixel coordinates

    // vec2 p = (2.0*(fragCoord)-resolution.xy)/resolution.xy;
    ${p_code}

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

    // Dithering with light intensity - similar to original
    ivec2 pix = ivec2(mod(fragCoord.xy, 4.));
    
    // Adjust threshold based on slider (affects dithering intensity)
    float thresh = bayerThreshold(pix.x, pix.y) * DITHER_INTENSITY_FACTOR;
    
    // Compute luminance
    float luminance = dot(col, vec3(0.299, 0.587, 0.114));
    
    // Apply dithering - darker areas will have more black pixels
    float dither = luminance < thresh ? 0.0 : 1.0;
    col = vec3(dither) * col;

    
    fragColor = vec4( col, 1.0 );
}""")

class mainImagePostTraceV6(mainSDFTrace):

    def __init__(self, name=None, template=None, *args, **kwargs):
        if template is None:
            template = mainImage_post_trace_template
        if name is None:
            name = "main_sdf_trace"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["setCamera_v1", "getSunDirection_v1", "render_post_trace_v6", "DitherUtils_v6"]
        self.vardeps = ["_AA", "cameraOrigin", "cameraDistance", "cameraAngleX", "cameraAngleY", "resolution", "_FOCAL_LENGTH", "_ZERO", "DITHER_INTENSITY_FACTOR"]
        self.inputs = ["fragColor", "fragCoord"]
        self.outputs = ["fragColor"]
        self.aa = 1

SMMap['mainImage_post_trace_v6'] = mainImagePostTraceV6


render_post_trace_v6 = register_shader_module("""
@name render_post_trace_v6
@inputs ro, rd, rdx, rdy, lig
@outputs col
@dependencies raycast_post_trace_v2, calcNormal_v1, calcLighting_v6, getMaterial_v2, DitherUtils_v6
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
    // vec3  nor = calcNormal(pos);
    vec3  nor = (m.x < 0.0) ? vec3(0.0, 1.0, 0.0) : calcNormal(pos);
    vec3  ref = reflect(rd, nor);

    // Material determination
    Material mat = getMaterial(m, pos, ro, rd, rdx, rdy);

    // Lighting
    vec3 color = calcLighting(pos, nor, ref, rd, mat, lig);

    // vec3 color = mat.albedo;
    float outline = CalculateConstantOutline(ro, rd, hit.x);
    // Apply outline directly as in original
    color = mix(color, vec3(0.0), outline);
    return color;
}""")