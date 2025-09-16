#!/usr/bin/env python3
"""
Simple HTML generator for ReGL shader projects.
Reads JSON configuration and generates HTML using Jinja templates.
"""

import json
import os
import html
from jinja2 import Environment, FileSystemLoader
from ..shader.utils.ubo import get_variable_info_for_editing

def generate_html(data, template_name='shader_vis.html.j2', output_file=None, mouse_control=True, resolution_via_scale=True, show_controls=False, backend='regl', layout_horizontal=False, allow_overflow=False, allow_singular_ubo_edit=False, enable_ubo_animation=False):
    """
    Generate HTML from JSON configuration using Jinja template.
    
    Args:
        json_file (str): Path to JSON configuration file
        template_name (str): Name of the Jinja template file
        output_file (str): Output HTML file path (optional)
        mouse_control (bool): Enable mouse-controlled camera
        resolution_via_scale (bool): Enable resolution scaling
        show_controls (bool): Show shader control sliders
        backend (str): Rendering backend to use ('regl' or 'twgl')
        layout_horizontal (bool): Use horizontal layout (canvas left, controls right)
        allow_overflow (bool): Allow controls to expand parent div (vs scroll within)
        allow_singular_ubo_edit (bool): Show UBO editing controls for individual variables
    """
    
    # Validate backend parameter
    if backend not in ['regl', 'twgl']:
        raise ValueError(f"backend must be 'regl' or 'twgl', got '{backend}'")
    texture_data = data.get('textures', {})
    if len(texture_data) > 0:
        load_textures = True
    else:
        load_textures = False

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    
    # Process uniforms based on control flags
    input_uniforms = data.get('uniforms', [])
    
    # underlying_uniforms: ALL uniforms for ReGL viewer (shader uniforms)
    underlying_uniforms = input_uniforms.copy()
    
    # Find required uniforms for features validation
    resolution_uniform = None
    camera_uniforms = {}
    
    for uniform in input_uniforms:
        uniform_name = uniform.get('name')
        uniform_type = uniform.get('type')
        
        # Check for resolution vec2 uniform
        if uniform_name == 'resolution' and uniform_type == 'vec2':
            resolution_uniform = uniform
        
        # Check for camera control uniforms
        if uniform_name in ['cameraAngleX', 'cameraAngleY', 'cameraDistance']:
            camera_uniforms[uniform_name] = uniform
    
    # Validate and process resolution_via_scale
    if resolution_via_scale:
        assert resolution_uniform is not None, \
            "resolution_via_scale requires a 'resolution' vec2 uniform in the input JSON"
    
    # Validate and process mouse_control
    if mouse_control:
        required_camera_uniforms = {'cameraAngleX', 'cameraAngleY', 'cameraDistance'}
        missing_camera_uniforms = required_camera_uniforms - set(camera_uniforms.keys())
        assert not missing_camera_uniforms, \
            f"mouse_control requires uniforms: {required_camera_uniforms}. Missing: {missing_camera_uniforms}"
    
    # ctrl_uniforms: Uniforms that will have UI controls created
    ctrl_uniforms = []
    camera_defaults = {}
    resolution_defaults = {}
    
    for uniform in input_uniforms:
        uniform_name = uniform.get('name')
        
        # Exclude camera controls from UI if mouse control is enabled
        if mouse_control and uniform_name in camera_uniforms:
            camera_defaults[uniform_name] = uniform.get('default', 0)
        # Exclude resolution control from UI if resolution_via_scale is enabled
        elif resolution_via_scale and uniform_name == 'resolution':
            # Store default resolution values from the vec2 uniform
            resolution_defaults['width'] = uniform.get('default', [512, 512])[0]
            resolution_defaults['height'] = uniform.get('default', [512, 512])[1]
        else:
            # Include in UI controls
            ctrl_uniforms.append(uniform)
    
    # Setup Jinja environment
    template_dir = os.path.join(script_dir, 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    
    # Render template with JSON data
    html_content = template.render(
        title=data.get('title', 'Untitled'),
        frag_str=data.get('frag_str', ''),
        load_textures=load_textures,
        textures=texture_data,
        uniforms=ctrl_uniforms,  # UI controls uniforms
        underlying_uniforms=underlying_uniforms,  # All uniforms for ReGL
        ubo_uniforms=data.get('ubo_uniforms', {}),  # UBO uniforms data
        ubo_variable_info=data.get('ubo_variable_info', {}),  # UBO variable info for editing
        mouse_control=mouse_control,
        camera_defaults=camera_defaults,
        resolution_via_scale=resolution_via_scale,
        resolution_defaults=resolution_defaults,
        show_controls=show_controls,
        backend=backend,
        layout_horizontal=layout_horizontal,
        allow_overflow=allow_overflow,
        allow_singular_ubo_edit=allow_singular_ubo_edit,
        enable_ubo_animation=enable_ubo_animation
    )
    
    
    return html_content



def create_shader_html(shader_code, sysl_uniforms, sysl_textures, title="Generated Shader",
    template_name='shader_vis.html.j2', output_file=None, mouse_control=True,
    resolution_via_scale=True, show_controls=False, backend='regl',
    script_dir=None, layout_horizontal=False, allow_overflow=False, allow_singular_ubo_edit=False, enable_ubo_animation=False):
    """
    Create complete HTML structure for the shader visualizer.
    
    Args:
        shader_code (str): The fragment shader code
        sysl_uniforms (dict): SySL uniforms dictionary
        title (str): Title for the shader
        template_name (str): Name of the Jinja template file
        output_file (str): Output HTML file path (optional)
        mouse_control (bool): Enable mouse-controlled camera
        resolution_via_scale (bool): Enable resolution scaling
        show_controls (bool): Show shader control sliders
        backend (str): Rendering backend to use ('regl' or 'twgl')
        script_dir (str): Script directory (optional)
        layout_horizontal (bool): Use horizontal layout (canvas left, controls right)
        allow_overflow (bool): Allow controls to expand parent div (vs scroll within)
        allow_singular_ubo_edit (bool): Show UBO editing controls for individual variables
    """
    json_uniforms = create_shader_json(shader_code, sysl_uniforms, sysl_textures, title)
    return generate_html(json_uniforms, template_name=template_name, output_file=output_file, mouse_control=mouse_control, resolution_via_scale=resolution_via_scale, show_controls=show_controls, backend=backend, layout_horizontal=layout_horizontal, allow_overflow=allow_overflow, allow_singular_ubo_edit=allow_singular_ubo_edit, enable_ubo_animation=enable_ubo_animation)

def create_shader_json(shader_code, sysl_uniforms, sysl_textures, title="Generated Shader"):
    """
    Create complete JSON structure for the HTML template system.
    
    Args:
        shader_code (str): The fragment shader code
        sysl_uniforms (dict): SySL uniforms dictionary
        title (str): Title for the shader
        
    Returns:
        dict: Complete JSON structure for template rendering
    """
    json_uniforms = convert_sysl_uniforms_to_json(sysl_uniforms, title)
    # Extract UBO uniforms and prepare variable info for editing
    ubo_uniforms = {name: data for name, data in sysl_uniforms.items() 
                    if data.get('type') == 'uniform_buffer'}
    
    # Get variable info for UBO editing controls
    ubo_variable_info = {}
    for ubo_name, ubo_data in ubo_uniforms.items():
        ubo_variable_info[ubo_name] = get_variable_info_for_editing(ubo_data)
    
    return {
        "title": title,
        "frag_str": shader_code,
        "uniforms": json_uniforms,
        "textures": sysl_textures,
        "ubo_uniforms": ubo_uniforms,
        "ubo_variable_info": ubo_variable_info
    }


def convert_sysl_uniforms_to_json(sysl_uniforms, title="Generated Shader"):
    """
    Convert SySL uniforms format to JSON format compatible with the HTML template system.
    
    Args:
        sysl_uniforms (dict): SySL uniforms in format:
            {
                "uniformName": {
                    'type': 'float|bool|vec2|vec3|int|uniform_buffer', 
                    "init_value": value,
                    "min": [min_values], 
                    "max": [max_values]
                }
            }
        title (str): Title for the generated shader
        
    Returns:
        list: List of uniform dictionaries compatible with the template system
    """
    json_uniforms = []
    render_uniforms = ["sunAzimuth", "sunElevation", "resolution", "castShadows"]
    camera_uniforms = ["cameraAngleX", "cameraAngleY", "cameraDistance", "cameraOrigin"]
    for uniform_name, uniform_data in sysl_uniforms.items():
        uniform_type = uniform_data.get('type', 'float')
        init_value = uniform_data.get('init_value', 0)
        min_vals = uniform_data.get('min', [])
        max_vals = uniform_data.get('max', [])
        if uniform_name in render_uniforms:
            set_name = "Settings"
        elif uniform_name in camera_uniforms:
            set_name = "Settings"
        else:
            set_name = "Knobs"
        
        # Handle UBO uniforms specially - don't create UI controls for them
        if uniform_type == 'uniform_buffer':
            # UBO uniforms are passed through to the underlying_uniforms but don't get UI controls
            continue
        
        # Handle different uniform types
        if uniform_type == 'bool':
            # Boolean uniform
            json_uniforms.append({
                "type": "bool",
                "name": uniform_name,
                "label": _format_label(uniform_name),
                "set_name": set_name,
                "default": bool(init_value)
            })
            
        elif uniform_type == 'float':
            # Float uniform -> range slider UI
            min_val = min_vals[0] if min_vals else 0.0
            max_val = max_vals[0] if max_vals else 1.0
            step_size = (max_val - min_val) / 1000
            # step = 0.01
            
            json_uniforms.append({
                "type": "float",
                "name": uniform_name,
                "label": _format_label(uniform_name),
                "min": float(min_val),
                "max": float(max_val),
                "step": step_size,
                "set_name": set_name,
                "default": float(init_value)
            })
            
        elif uniform_type == 'int':
            # Integer uniform -> range slider UI with step 1
            min_val = min_vals[0] if min_vals else 0
            max_val = max_vals[0] if max_vals else 100
            
            json_uniforms.append({
                "type": "int",
                "name": uniform_name,
                "label": _format_label(uniform_name),
                "min": int(min_val),
                "max": int(max_val),
                "step": 1,
                "set_name": set_name,
                "default": int(init_value)
            })
            
        elif uniform_type in ['vec2', 'vec3', 'vec4']:
            # Vector types -> single entry with list min/max values
            vector_size = len(init_value) if hasattr(init_value, '__len__') else int(uniform_type[-1])
            
            # Build min/max lists, padding with defaults if needed
            min_list = []
            max_list = []
            for i in range(vector_size):
                min_val = min_vals[i] if i < len(min_vals) else -1.0
                max_val = max_vals[i] if i < len(max_vals) else 1.0
                min_list.append(float(min_val))
                max_list.append(float(max_val))
            
            step_size = (max_val - min_val) / 1000
            json_uniforms.append({
                "type": uniform_type,
                "name": uniform_name,
                "label": _format_label(uniform_name),
                "min": min_list,
                "max": max_list,
                "step": step_size,
                "set_name": set_name,
                "default": list(init_value) if hasattr(init_value, '__len__') else [float(init_value)] * vector_size
            })
    
    return json_uniforms

def _format_label(uniform_name):
    """Convert camelCase or snake_case to readable label"""
    # Convert camelCase to words
    import re
    # Insert spaces before uppercase letters
    name = re.sub('([a-z0-9])([A-Z])', r'\1 \2', uniform_name)
    # Replace underscores with spaces
    name = name.replace('_', ' ')
    # Capitalize first letter of each word
    return name.title()

def make_jupyter_compatible_html(html_code):
    """
    Make the HTML code compatible with Jupyter notebooks.
    """
    escaped_html = html.escape(html_code)
    iframe_html = f"""<iframe
        srcdoc="{escaped_html}"
        style="width: 100%; height: 800px; border: none;"
        sandbox="allow-scripts allow-same-origin"
    ></iframe>"""
    return iframe_html