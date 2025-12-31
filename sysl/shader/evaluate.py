"""
Main entry point for evaluating SySL expressions to shader code.

This module provides a unified interface for converting symbolic expressions
into GLSL shader code, supporting both single-pass and multi-pass rendering modes.
"""

from typing import Dict, Any, List
import geolipi.symbolic as gls
import sysl.symbolic as sls

from .evaluate_singlepass import evaluate_singlepass
from .evaluate_multipass import evaluate_multipass
from .shader_templates.common import RenderMode
from .utils.conversion import convert_solid_types

DEFAULT_SETTINGS = {
    "render_mode": RenderMode.DEFAULT,
    "variables": {
        "_ADD_FLOOR_PLANE": False,
        "_RAYCAST_MAX_STEPS": 200,
        "_RAYCAST_CONSERVATIVE_STEPPING_RATE": 0.99,
        "_AA": 1,   
        "castShadows": True,
    },
    "extract_vars": False,
    "use_define_vars": False
}

def evaluate_to_shader(expression: gls.GLFunction | gls.GLExpr, 
                         mode: str = "singlepass",
                         settings: Dict[str, Any] | None = None, 
                         insert_types: bool=True,
                         *args, **kwargs) -> List[Dict[str, Any]] | str:

    if settings is None:
        settings = DEFAULT_SETTINGS
    render_mode = settings.get("render_mode", RenderMode.DEFAULT)
    if insert_types:
        expression = convert_solid_types(expression, render_mode)
    
    if mode == "singlepass":
        shader_output = evaluate_singlepass(expression, settings, *args, **kwargs)
    elif mode == "multipass":
        shader_output = evaluate_multipass(expression, settings, *args, **kwargs)
    else:
        raise ValueError(f"Invalid mode: {mode}")

    return shader_output
