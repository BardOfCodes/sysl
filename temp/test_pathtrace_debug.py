#!/usr/bin/env python3
"""
Debug version of path tracing - visualize what the second shader is receiving
"""

from sysl.sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html

# First pass - just output a test pattern
shader_1 = """#version 300 es
precision highp float;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    // Output a simple test pattern to the float texture
    float value = uv.x * 0.5 + uv.y * 0.5;
    fragColor = vec4(value, 0.0, 0.0, 1.0);
}
"""

# Second pass - visualize what we're reading
shader_2 = """#version 300 es
precision highp float;
uniform sampler2D distance_travelled;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 fragCoord = gl_FragCoord.xy;
    
    // Read from the texture
    float dist = texelFetch(distance_travelled, ivec2(fragCoord), 0).r;
    
    // Visualize the distance value
    // If it's working, we should see the gradient pattern
    fragColor = vec4(dist, dist, dist, 1.0);
    
    // Debug: also show UV coordinates as color
    vec2 uv = fragCoord / resolution;
    fragColor = vec4(dist, uv.x * 0.5, uv.y * 0.5, 1.0);
}
"""

shader_definitions = [
    {
        "shader_code": shader_1,
        "uniforms": {},
        "textures": {},
        "input_FBOs": [],
        "output_FBO": {"name": "distance_travelled", "width": 512, "height": 512, "type": "float"}
    },
    {
        "shader_code": shader_2,
        "uniforms": {},
        "textures": {},
        "input_FBOs": [{"name": "distance_travelled", "width": 512, "height": 512, "type": "float"}],
        "output_FBO": "image"
    }
]

if __name__ == "__main__":
    output_path = "/sensei-fs-3/users/aganeshan/projects/mpspy/temp/test_pathtrace_debug.html"
    html_content = create_multibuffer_shader_html(
        shader_definitions,
        backend="twgl",
        show_controls=True
    )
    
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    print(f"Generated {output_path}")










