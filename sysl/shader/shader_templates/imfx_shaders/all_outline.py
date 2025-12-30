from string import Template

ALL_OUTLINE_NOBG_SHADER = Template("""
#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
#endif

out vec4 fragColor;

uniform sampler2D distance_travelled; // RGBA = (trace_dist, part_id, oct_x, oct_y)
uniform sampler2D ${input_name};

uniform vec2 resolution; // (width, height)
const int nhbd = ${nhbd}; // 1 -> 3x3, 2 -> 5x5

const float OUTLINE_AMOUNT = 0.8;

// ---- thresholds (tune) ----
// depth: absolute + relative component (relative helps far/near stability)
const float DEPTH_EPS_ABS = 0.1;   // in your trace_dist units
const float DEPTH_EPS_REL = 0.05;  // fraction of center depth

// normals: outline if angle > ~60 degrees => cos(60°) ~ 0.50
const float NORMAL_COS_THRESH = 0.70;

// If you want "one-sided" outlines like your old code, set this true.
// Otherwise edges are symmetric.
const bool ONE_SIDED = true;

// ---- oct decode ----
vec3 octDecode(vec2 e01)
{
    // e01 in [0,1]; map to [-1,1]
    vec2 e = e01 * 2.0 - 1.0;

    vec3 n = vec3(e.x, e.y, 1.0 - abs(e.x) - abs(e.y));
    if (n.z < 0.0) {
        n.xy = (1.0 - abs(n.yx)) * sign(n.xy);
    }
    return normalize(n);
}
bool is_outline(vec2 uv)
{
    vec2 texel = 1.0 / resolution;

    vec4 c = texture(distance_travelled, uv);
    float cDepth = c.r;
    int   cId    = int(floor(c.g + 0.5));
    if (cId < 0) return false;

    float depthEps = DEPTH_EPS_ABS + DEPTH_EPS_REL * max(abs(cDepth), 1e-6);

    // center normal (decode once)
    vec3 cN = octDecode(c.ba);

    for (int dy = -nhbd; dy <= nhbd; ++dy) {
        for (int dx = -nhbd; dx <= nhbd; ++dx) {
            if (dx == 0 && dy == 0) continue;

            vec2 offset = vec2(float(dx), float(dy)) * texel;
            vec4 n = texture(distance_travelled, uv + offset);

            float nDepth = n.r;
            int   nId    = int(floor(n.g + 0.5));

            // Neighbor miss => boundary. One-sided should still outline on the hit pixel.
            if (nId < 0) return true;

            // Define "closer neighbor" for one-sided gating
            bool neighborIsCloser = nDepth < cDepth;

            // 2) ID discontinuity
            bool idDisc = (nId != cId);
            if (idDisc) {
                if (!ONE_SIDED) return true;
                if (neighborIsCloser) return true;
            }

            // 1) Depth discontinuity (symmetric test, then one-sided gate)
            bool depthDisc = abs(nDepth - cDepth) > depthEps;
            if (depthDisc) {
                if (!ONE_SIDED) return true;
                if (neighborIsCloser) return true;
            }

            // 3) Normal discontinuity (decode neighbor only if needed)
            vec3 nN = octDecode(n.ba);
            bool normalDisc = dot(cN, nN) < NORMAL_COS_THRESH;
            if (normalDisc) {
                if (!ONE_SIDED) return true;
                if (neighborIsCloser) return true;
            }
        }
    }
    return false;
}
void main(void)
{
    vec2 uv = gl_FragCoord.xy / resolution;

    vec4 base_color = texture(${input_name}, uv);

    // Background handling (as you had)
    float center_ind = texture(distance_travelled, uv).g;
    int center_id = int(floor(center_ind + 0.5));
    if (center_id < 0) {
        base_color = vec4(1.0, 1.0, 1.0, 1.0);
    }

    bool outline = is_outline(uv);

    fragColor = outline
        ? mix(base_color, vec4(0.0, 0.0, 0.0, 1.0), OUTLINE_AMOUNT)
        : base_color;
}
""")