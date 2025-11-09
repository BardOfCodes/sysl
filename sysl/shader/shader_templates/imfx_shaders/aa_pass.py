from string import Template

FXAA_SHADER = Template("""
#version 300 es
precision highp float;

out vec4 fragColor;

uniform sampler2D image_AA;    // MUST be bound to the 1024×1024 atlas

void main()
{
    ivec2 outPx = ivec2(gl_FragCoord.xy);   // 0..511
    ivec2 atlasPx = outPx * 2;              // map to 0..1023

    // Fetch four exact texels (no filter)
    vec3 c00 = texelFetch(image_AA, outPx, 0).rgb;
    vec3 c01 = texelFetch(image_AA, outPx + ivec2(1,0) * ${resolution}, 0).rgb;
    vec3 c02 = texelFetch(image_AA, outPx + ivec2(0,1) * ${resolution}, 0).rgb;
    vec3 c03 = texelFetch(image_AA, outPx + ivec2(1,1) * ${resolution}, 0).rgb;
    // for three x we have 9 things to add
    // vec3 c10 = texelFetch(image_AA, outPx + ivec2(2,0) * ${resolution}, 0).rgb;
    // vec3 c12 = texelFetch(image_AA, outPx + ivec2(2,1) * ${resolution}, 0).rgb;
    // vec3 c20 = texelFetch(image_AA, outPx + ivec2(0,2) * ${resolution}, 0).rgb;
    // vec3 c21 = texelFetch(image_AA, outPx + ivec2(1,2) * ${resolution}, 0).rgb;
    // vec3 c22 = texelFetch(image_AA, outPx + ivec2(2,2) * ${resolution}, 0).rgb;

    fragColor = vec4((c00 + c01 + c02 + c03) * 0.25, 1.0);
    //fragColor = vec4(c00, 1.0);
    // fragColor = vec4((c00 + c01 + c02 + c03 + c10 + c12 + c20 + c21 + c22) * 0.1111111111111111, 1.0);
}
""")