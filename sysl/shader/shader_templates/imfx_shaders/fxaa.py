from string import Template


FXAA_SHADER_TEMPLATE = Template("""
#version 300 es
precision highp float;

out vec4 fragColor;

uniform sampler2D image_AA;    // MUST be bound to the 1024×1024 atlas

void main()
{
    ivec2 outPx = ivec2(gl_FragCoord.xy);   // 0..511
    ivec2 atlasPx = outPx * ${aa_amount};              // map to 0..1023

    // Fetch ${num_samples} exact texels (no filter) for ${aa_amount}x${aa_amount} AA
${fetch_lines}

    fragColor = vec4((${sum_expr}) * ${avg_factor}, 1.0);
}""")


def fxaa_shader(aa_amount):
    """
    Generate FXAA shader code for a given anti-aliasing amount.
    
    Args:
        aa_amount: Integer, the anti-aliasing amount (e.g., 2 for 2x2, 3 for 3x3)
    
    Returns:
        Template object that can be substituted with ${resolution}
    """
    if aa_amount < 1:
        raise ValueError("aa_amount must be at least 1")
    
    # Generate variable names and texel fetch statements
    # The original uses a specific naming: c00, c01, c02, c03 for 2x2
    # where the pattern is: iterate x first, then y (column-major order)
    fetch_lines = []
    variable_names = []
    
    sample_index = 0
    for y in range(aa_amount):
        for x in range(aa_amount):
            # Generate variable name with two digits (c00, c01, etc.)
            # For aa_amount > 10, this will need adjustment, but that's unlikely
            var_name = f"c{sample_index // 10}{sample_index % 10}" if sample_index < 100 else f"c{sample_index}"
            variable_names.append(var_name)
            
            if x == 0 and y == 0:
                # First sample doesn't need offset
                fetch_lines.append(f"    vec3 {var_name} = texelFetch(image_AA, outPx, 0).rgb;")
            else:
                # Other samples need offset
                fetch_lines.append(f"    vec3 {var_name} = texelFetch(image_AA, outPx + ivec2({x},{y}) * ${{resolution}}, 0).rgb;")
            
            sample_index += 1
    
    # Calculate averaging factor
    num_samples = aa_amount * aa_amount
    avg_factor = 1.0 / num_samples
    
    # Generate sum expression
    sum_expr = " + ".join(variable_names)
    
    # Substitute into template (using safe_substitute to preserve ${resolution})
    shader_code = FXAA_SHADER_TEMPLATE.safe_substitute(
        aa_amount=aa_amount,
        num_samples=num_samples,
        fetch_lines="\n".join(fetch_lines),
        sum_expr=sum_expr,
        avg_factor=f"{avg_factor:.15f}"
    )
    
    return Template(shader_code)

