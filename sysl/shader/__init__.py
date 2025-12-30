"""
SySL Shader Generation Package.

This package converts symbolic SySL expressions into GLSL shader code.
Importing this module registers all shader modules (primitives, combinators,
transforms, materials, and rendering pipelines) in the global shader registry.

Main Entry Points:
    - evaluate_to_shader: Convert expression to shader code
    - DEFAULT_SETTINGS: Default configuration for shader generation
    - RenderMode: Constants for render mode selection (V1-V6)

Example:
    >>> from sysl.shader import evaluate_to_shader, DEFAULT_SETTINGS
    >>> shader_code, uniforms, textures = evaluate_to_shader(expression)
"""

# =============================================================================
# Shader Module Registration
# =============================================================================
# These imports register shader modules in the global SMMap registry.
# They are imported for their side effects (decorator-based registration).
from .shader_templates import *
# =============================================================================
# Public API
# =============================================================================

from .evaluate import evaluate_to_shader, DEFAULT_SETTINGS
from .shader_templates.common import RenderMode

__all__ = [
    # Main entry point
    "evaluate_to_shader",
    "DEFAULT_SETTINGS",
    # Render mode constants
    "RenderMode",
]
