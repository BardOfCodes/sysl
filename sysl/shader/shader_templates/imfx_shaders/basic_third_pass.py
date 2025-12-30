from string import Template

BASIC_THIRD_PASS_SHADER = Template("""
#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
#endif

out vec4 fragColor;

uniform sampler2D ${input_name};

uniform vec2 resolution; // (width, height)
void main(void)
{
    // Convert from gl_FragCoord to UVs
    vec2 uv = gl_FragCoord.xy / resolution;
    vec4 base_color = texture(${input_name}, uv);
    fragColor = base_color;
}
""")