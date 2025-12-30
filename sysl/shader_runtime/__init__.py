"""
Shader runtime module for SySL.

Provides two main capabilities:
1. HTML generation for interactive web-based shader visualization
2. Offline rendering using ModernGL (optional dependency)

Main exports:
    - create_shader_html: Generate HTML for single-pass shader visualization
    - create_multibuffer_shader_html: Generate HTML for multi-pass rendering
    - make_jupyter_compatible_html: Wrap HTML for Jupyter notebook display
    - render_single_pass: Offline render single-pass shader (requires moderngl)
    - render_multipass: Offline render multi-pass shader (requires moderngl)
"""

from .generate_shader_html import (
    create_shader_html,
    create_multibuffer_shader_html,
    make_jupyter_compatible_html,
    generate_html,
    create_shader_json,
    convert_sysl_uniforms_to_json,
)

# Offline rendering requires moderngl - import lazily to make it optional
def render_single_pass(*args, **kwargs):
    """
    Render a single-pass shader to an image (requires moderngl).
    
    See offline_render.render_single_pass for full documentation.
    """
    from .offline_render import render_single_pass as _render_single_pass
    return _render_single_pass(*args, **kwargs)


def render_multipass(*args, **kwargs):
    """
    Render a multi-pass shader pipeline to an image (requires moderngl).
    
    See offline_render.render_multipass for full documentation.
    """
    from .offline_render import render_multipass as _render_multipass
    return _render_multipass(*args, **kwargs)


__all__ = [
    # HTML generation
    "create_shader_html",
    "create_multibuffer_shader_html", 
    "make_jupyter_compatible_html",
    "generate_html",
    "create_shader_json",
    "convert_sysl_uniforms_to_json",
    # Offline rendering (requires moderngl)
    "render_single_pass",
    "render_multipass",
]

