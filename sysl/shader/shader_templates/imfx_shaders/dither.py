from string import Template

DITHER_SHADER = Template("""
#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
#endif

out vec4 fragColor;

uniform sampler2D distance_travelled;
uniform sampler2D ${input_name};

uniform vec2 resolution; // (width, height)

const float DITHER_INTENSITY_FACTOR = ${dither_intensity_factor};

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

void main(void)
{
    vec2 uv = gl_FragCoord.xy / resolution;

    vec4 base_color = texture(${input_name}, uv);
    vec3 col = base_color.rgb;

    // Dithering with light intensity - similar to original
    ivec2 pix = ivec2(mod(gl_FragCoord.xy, 4.));
    
    // Adjust threshold based on slider (affects dithering intensity)
    float thresh = bayerThreshold(pix.x, pix.y) * DITHER_INTENSITY_FACTOR;
    
    // Compute luminance
    float luminance = dot(col, vec3(0.299, 0.587, 0.114));
    
    // Apply dithering - darker areas will have more black pixels
    float dither = luminance < thresh ? 0.0 : 1.0;
    col = vec3(dither) * col;

    fragColor = vec4(col, base_color.a);
}
""")