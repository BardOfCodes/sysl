# Make it simpler to evaluate geolipi expressions. 
from typing import Dict, Any, List
import geolipi.symbolic as gls
import sysl.symbolic as sls

from .evaluate_singlepass import evaluate_to_shader
from .evaluate_multipass import evaluate_to_multipass_shader

from .utils.conversion import convert_solid_types

DEFAULT_SETTINGS = {
    "render_mode": "v4",
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
                         insert_types: bool=True) -> List[Dict[str, Any]] | str:

    if settings is None:
        settings = DEFAULT_SETTINGS
    render_mode = settings.get("render_mode", "v4")
    if insert_types:
        expression = convert_solid_types(expression, render_mode)
    
    if mode == "singlepass":
        shader_output = evaluate_to_shader(expression, settings, insert_types=insert_types)
    elif mode == "multipass":
        shader_output = evaluate_to_multipass_shader(expression, settings, insert_types=insert_types)
    else:
        raise ValueError(f"Invalid mode: {mode}")

    return shader_output
