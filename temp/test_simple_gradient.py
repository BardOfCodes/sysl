#!/usr/bin/env python3
"""
Simple gradient test - should show red-green gradient if rendering works
"""

from sysl.sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html

# Two passes: first to FBO, then to canvas
shader_definitions = [
    {
        # Pass 1: Render gradient to FBO
        "shader_code": """#version 300 es
precision highp float;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    // Red-green gradient
    fragColor = vec4(uv.x, uv.y, 0.0, 1.0);
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [],
        "output_FBO": {"name": "buffer1", "width": 512, "height": 512, "type": "vec4"}
    },
    {
        # Pass 2: Copy from FBO to canvas
        "shader_code": """#version 300 es
precision highp float;
uniform sampler2D buffer1;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    vec4 color = texture(buffer1, uv);
    // Just copy the color
    fragColor = color;
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [{"name": "buffer1", "width": 512, "height": 512, "type": "vec4"}],
        "output_FBO": "image"
    }
]

if __name__ == "__main__":
    output_path = "/sensei-fs-3/users/aganeshan/projects/mpspy/temp/test_simple_gradient.html"
    html_content = create_multibuffer_shader_html(
        shader_definitions,
        backend="twgl",
        show_controls=True
    )
    
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    print(f"Generated {output_path}")
