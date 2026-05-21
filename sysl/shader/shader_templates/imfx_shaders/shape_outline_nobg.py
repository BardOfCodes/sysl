from string import Template

SHAPE_OUTLINE_NOBG_SHADER = Template("""
#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
#endif

out vec4 fragColor;

uniform sampler2D distance_travelled;
uniform sampler2D ${input_name};

uniform vec2 resolution; // (width, height)
const int nhbd = ${nhbd}; // 1 -> 3x3, 2 -> 5x5

const float OUTLINE_AMOUNT = 0.8;

bool is_outline(vec2 uv)
{
    vec2 texel = 1.0 / resolution;

    float center_ind = texture(distance_travelled, uv).g;
    int center_id = int(floor(center_ind + 0.5));
    if (center_id < 0) return false;

    // Only outline the outer foreground shape, ignoring part-id changes.
    for (int dy = -nhbd; dy <= nhbd; ++dy) {
        for (int dx = -nhbd; dx <= nhbd; ++dx) {
            if (dx == 0 && dy == 0) continue; // skip self
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            float n_ind = texture(distance_travelled, uv + offset).g;
            int n_id = int(floor(n_ind + 0.5));
            if (n_id < 0) return true;
        }
    }
    return false;
}
void main(void)
{
    vec2 uv = gl_FragCoord.xy / resolution;

    vec4 base_color = texture(${input_name}, uv);
    bool outline = is_outline(uv);

    fragColor = outline
        ? mix(base_color, vec4(0.0, 0.0, 0.0, 1.0), OUTLINE_AMOUNT)
        : base_color;
    float center_ind = texture(distance_travelled, uv).g;
    int center_id = int(floor(center_ind + 0.5));
    fragColor = center_id < 0 ? vec4(1.0, 1.0, 1.0, 1.0) : fragColor;
}
""")
