from string import Template

SELECTION_HIGHLIGHT_SHADER = Template("""
#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
#endif

out vec4 fragColor;

uniform sampler2D distance_travelled;
uniform sampler2D intermediate_image;

uniform vec2 resolution; // (width, height)
const int nhbd = 1;            // 1 -> 3x3, 2 -> 5x5

#define SELECT_ID 1

bool is_outline(vec2 uv)
{
    // Compute pixel step size in UV space
    vec2 texel = 1.0 / resolution;

    // Fetch center pixel part index (second channel)
    float center_ind = texture(distance_travelled, uv).g;
    int center_id = int(round(center_ind));

    // Check neighborhood
    for (int dy = -nhbd; dy <= nhbd; ++dy) {
        for (int dx = -nhbd; dx <= nhbd; ++dx) {
            vec2 offset = vec2(float(dx), float(dy)) * texel;
            float n_ind = texture(distance_travelled, uv + offset).g;
            int n_id = int(round(n_ind));
            if (n_id != center_id) return true;
        }
    }
    return false;
}

void main(void)
{
    // Convert from gl_FragCoord to UVs
    vec2 uv = gl_FragCoord.xy / resolution;
    
    vec4 base_color = texture(intermediate_image, uv);
    float center_ind = texture(distance_travelled, uv).g;
    int center_id = int(round(center_ind));

    bool outline = false;
    if (SELECT_ID != -1){
        if (center_id == SELECT_ID){
            outline = is_outline(uv);
        }
    }
    fragColor = outline? mix(base_color, vec4(1.0, 0.0, 0.0, 1.0), 0.5) : base_color;
}
""")