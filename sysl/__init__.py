"""
SySL: Symbolic Scene Language

A library for converting symbolic scene expressions into GLSL shader code
for sphere-traced rendering and interactive WebGL visualization.

Example:
    >>> import geolipi.symbolic as gls
    >>> import sysl.symbolic as sls
    >>> from sysl.shader import evaluate_to_shader
    >>> from sysl.shader_runtime import create_shader_html
    >>> 
    >>> # Create a simple scene
    >>> sphere = gls.Sphere3D((1.0,))
    >>> material = sls.MaterialV4((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.5, 0.3, 0.0))
    >>> scene = sls.MatSolidV4(sphere, material)
    >>> 
    >>> # Generate shader code
    >>> shader_code, uniforms, textures = evaluate_to_shader(scene)
    >>> 
    >>> # Create interactive HTML
    >>> html = create_shader_html(shader_code, uniforms, textures)
"""

__version__ = "0.1.0"
__author__ = "Aditya Ganeshan"

# =============================================================================
# Public API
# =============================================================================

# Shader evaluation
from .shader import evaluate_to_shader, DEFAULT_SETTINGS, RenderMode

# Shader runtime (HTML generation, offline rendering)
from .shader_runtime import (
    create_shader_html,
    create_multibuffer_shader_html,
    make_jupyter_compatible_html,
)

# Conditionally import offline rendering (requires moderngl)
try:
    from .shader_runtime import render_single_pass, render_multipass
    _HAS_OFFLINE_RENDER = True
except ImportError:
    _HAS_OFFLINE_RENDER = False

# Symbolic module (re-export for convenience)
from . import symbolic

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Shader evaluation
    "evaluate_to_shader",
    "DEFAULT_SETTINGS",
    "RenderMode",
    # HTML generation
    "create_shader_html",
    "create_multibuffer_shader_html",
    "make_jupyter_compatible_html",
    # Symbolic module
    "symbolic",
]

# Add offline rendering to exports if available
if _HAS_OFFLINE_RENDER:
    __all__.extend(["render_single_pass", "render_multipass"])






