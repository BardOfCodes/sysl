#!/usr/bin/env python3
"""
Debug test: Single pass rendering directly to canvas (no FBOs)
This should show a simple gradient if canvas rendering is working.
"""

from sysl.sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html

# Single pass that renders directly to canvas
shader_definitions = [
    {
        "shader_code": """#version 300 es
precision highp float;
uniform vec2 resolution;
uniform float time;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    // Simple gradient that changes with time
    fragColor = vec4(uv.x, uv.y, 0.5 + 0.5 * sin(time), 1.0);
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [],  # No inputs
        "output_FBO": "image"  # Direct to canvas
    }
]

if __name__ == "__main__":
    html_content = create_multibuffer_shader_html(
        shader_definitions,
        output_filename="/sensei-fs-3/users/aganeshan/projects/mpspy/temp/test_canvas_direct.html",
        backend="twgl",
        show_controls=True
    )
    print("Generated /sensei-fs-3/users/aganeshan/projects/mpspy/temp/test_canvas_direct.html")
