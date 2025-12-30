"""
Common constants and configuration for shader generation.

This module defines shared constants used across the shader generation system,
including render modes, shader constants, and uniform definitions.
"""

import numpy as np


# =============================================================================
# Render Mode Constants
# =============================================================================
# These define the different rendering pipelines available in SySL.
# Each mode uses different material representations and shading approaches.

class RenderMode:
    """Render mode identifiers for shader generation."""
    V1 = "v1"  # Basic SDF with simple material (float)
    V2 = "v2"  # SDF with vec4 material data
    V3 = "v3"  # SDF with material index reference (deferred material lookup)
    V4 = "v4"  # SDF with MATPoint material (recommended default)
    V5 = "v5"  # Same as V4 (MATPoint)
    V6 = "v6"  # Same as V2 (vec4)
    
    DEFAULT = V4
    
    @classmethod
    def all_modes(cls):
        """Return all valid render modes."""
        return [cls.V1, cls.V2, cls.V3, cls.V4, cls.V5, cls.V6]


# =============================================================================
# GLSL Preliminaries
# =============================================================================

PRELIMINARIES = """
"""


CONSTANTS = {
    "_ZERO": ('int', 0),
    "_FOCAL_LENGTH": ('float', 2.5),
    "_AA": ('int', 1),
    "_SCENE_RADIUS": ('float', 100.0),
    "_SCENE_BOX_CENTER": ('vec3', (0.0, 0.5, 0.0)),
    "_SCENE_BOX_SIZE": ('vec3', (10.0, 5.0, 10.0)),
    "_RAYCAST_MAX_STEPS": ('int', 100),
    "_RAYCAST_CONSERVATIVE_STEPPING_RATE": ('float', 1.0),
    "_ADD_FLOOR_PLANE": ('bool', False),
    "_SHADOW_MAX_STEPS": ('int', 64),
    "_NORMAL_STEPS": ('int', 4),
    "_AO_STEPS": ('int', 5),
    "_COLOR_FACTOR": ('float', 2.0),
    "EPSILON": ('float', 1e-9),
}
UNIFORMS = {
    "castShadows": {
        'type': 'bool', "init_value": "true", 
        "min": "", "max": ""},
    "sunElevation": {
        'type': 'float', "init_value": 0.5,
        "min": [0.0,], "max": [np.pi/2],
    },
    "sunAzimuth": {
        'type': 'float', "init_value": 0.0,
        "min": [-np.pi], "max": [np.pi]},
    "cameraOrigin": {
        'type': 'vec3', "init_value": [0, -1.0, 0],
        "min": [-10, -10, -10], "max": [10, 10, 10]},
    "cameraDistance": {
        'type': 'float', "init_value": 3.0,
        "min": [0.0], "max": [10.0]},
    "cameraAngleX": {
        'type': 'float', "init_value": np.pi/4,
        "min": [-np.pi], "max": [np.pi]},
    "cameraAngleY": {
        'type': 'float', "init_value": np.pi/4,
        "min": [-np.pi], "max": [np.pi]},
    "resolution": {
        'type': 'vec2', "init_value": [512, 512],
        "min": [1, 1], "max": [10000, 10000]},
    "backgroundElevation": {
        'type': 'float', "init_value": 0.5,
        "min": [-np.pi/4], "max": [np.pi/4],
    },
    "backgroundAzimuth": {
        'type': 'float', "init_value": -2.0,
        "min": [-np.pi], "max": [np.pi]},
}
