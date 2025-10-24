#!/usr/bin/env python3
"""
Test script for multi-buffer shader rendering.
Creates a simple two-pass rendering example:
- Pass 1: Renders a gradient to "buffer1"
- Pass 2: Reads from "buffer1", inverts colors, outputs to "image" (canvas)
"""

# Simple two-pass example with no uniforms or textures
shader_definitions = [
    {
        # Pass 1: Render a gradient to buffer1
        "shader_code": """#version 300 es
precision highp float;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    fragColor = vec4(uv.x, uv.y, 0.5, 1.0);
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [],  # No inputs
        "output_FBO": {"name": "buffer1", "width": 512, "height": 512, "type": "vec4"}  # Output to buffer1
    },
    {
        # Pass 2: Read from buffer1, invert colors, output to canvas
        "shader_code": """#version 300 es
precision highp float;

uniform sampler2D buffer1;  // Input from previous pass
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    vec4 color = texture(buffer1, uv);
    // Invert the colors
    fragColor = vec4(1.0 - color.rgb, 1.0);
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [{"name": "buffer1", "width": 512, "height": 512, "type": "vec4"}],  # Read from buffer1
        "output_FBO": "image"  # Final output to canvas
    }
]

# Example with accumulation (path tracing style)
# This shows a shader reading from its own output for accumulation
accumulation_example = [
    {
        # Accumulation pass - computes actual color + noise, then accumulates
        "shader_code": """#version 300 es
precision highp float;

uniform sampler2D accumBuffer;  // Previous frame
uniform float time;
uniform vec2 resolution;
out vec4 fragColor;

// Simple hash function for noise
float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    
    // Get previous accumulation (RGB = accumulated sum, A = sample count)
    vec4 prev = texture(accumBuffer, uv);
    
    // ===== ACTUAL COLOR (the ground truth we want to converge to) =====
    // Create a colorful gradient pattern as the "true" image
    vec2 centered = uv - 0.5;
    float angle = atan(centered.y, centered.x);
    float radius = length(centered);
    
    // Actual color is a radial gradient with some patterns
    vec3 actualColor = vec3(
        0.5 + 0.5 * cos(angle * 3.0),
        0.5 + 0.5 * sin(radius * 10.0),
        0.5 + 0.5 * cos(radius * 8.0 - angle * 2.0)
    );
    
    // ===== ADD NOISE =====
    // Add random noise that changes each frame (varies with time)
    float noise1 = hash(uv * 100.0 + time * 10.0) - 0.5;
    float noise2 = hash(uv * 100.0 + time * 10.0 + 50.0) - 0.5;
    float noise3 = hash(uv * 100.0 + time * 10.0 + 100.0) - 0.5;
    vec3 noise = vec3(noise1, noise2, noise3) * 0.5;  // Scale noise for visibility
    
    // This frame's noisy sample = actual color + noise
    vec3 noisySample = actualColor + noise;
    
    // ===== ACCUMULATE SUM =====
    // RGB channels store the accumulated SUM (not average)
    // Alpha channel stores the sample COUNT
    float sampleCount = prev.a;  // Previous sample count
    vec3 accumulatedSum = prev.rgb;  // Previous sum
    
    // Add new sample to the sum
    accumulatedSum += noisySample;
    sampleCount += 1.0;
    
    // Store sum in RGB, count in A
    fragColor = vec4(accumulatedSum, sampleCount);
}
""",
        "uniforms": {"time": {"type": "float", "init_value": 0.0}},
        "textures": {},
        "input_FBOs": [{"name": "accumBuffer", "width": 512, "height": 512, "type": "vec4"}],
        "output_FBO": {"name": "accumBuffer", "width": 512, "height": 512, "type": "vec4"}
    },
    {
        # Display pass - divide sum by count to get average and display
        "shader_code": """#version 300 es
precision highp float;

uniform sampler2D accumBuffer;
uniform vec2 resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / resolution;
    vec4 accum = texture(accumBuffer, uv);
    
    // Extract accumulated sum and sample count
    vec3 sum = accum.rgb;
    float count = max(accum.a, 1.0);  // Avoid divide by zero
    
    // Calculate average by dividing sum by count
    vec3 average = sum / count;
    
    // Clamp to valid range [0,1]
    average = clamp(average, 0.0, 1.0);
    
    // Show frame count in corner as visual indicator
    if (uv.x < 0.2 && uv.y > 0.85) {
        // Show convergence progress - red bar that fills as samples accumulate
        float progress = min(count / 100.0, 1.0);  // Full at 100 samples
        if (uv.x < 0.02 + progress * 0.18) {
            average = mix(average, vec3(1.0, 0.2, 0.2), 0.7);
        }
        
        // Add frame count text indicator (as brightness variation)
        if (uv.y > 0.95) {
            float countIndicator = count / 500.0;  // Normalize to 500 samples
            average = mix(average, vec3(countIndicator, countIndicator * 0.5, 0.0), 0.3);
        }
    }
    
    fragColor = vec4(average, 1.0);
}
""",
        "uniforms": {},
        "textures": {},
        "input_FBOs": [{"name": "accumBuffer", "width": 512, "height": 512, "type": "vec4"}],
        "output_FBO": "image"
    }
]

def test_simple_multipass():
    """Test the simple two-pass example."""
    import os
    from sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html
    
    output_path = os.path.abspath("temp/test_twopass.html")
    html = create_multibuffer_shader_html(
        shader_definitions,
        title="Simple Two-Pass Test",
        output_file=output_path
    )
    
    print(f"Generated {output_path}")
    return html

def test_accumulation():
    """Test the accumulation example with self-referencing FBO."""
    import os
    from sysl.shader_vis.generate_shader_html import create_multibuffer_shader_html
    
    output_path = os.path.abspath("temp/test_accumulation.html")
    html = create_multibuffer_shader_html(
        accumulation_example,
        title="Accumulation Test",
        output_file=output_path
    )
    
    print(f"Generated {output_path}")
    return html

if __name__ == "__main__":
    # Run the simple test
    test_accumulation()
