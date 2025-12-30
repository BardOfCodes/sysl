"""
Expression type conversion utilities for shader generation.

This module provides functions to convert generic MatSolid expressions
into version-specific solid types required by different render modes.
"""

import geolipi.symbolic as gls
import sysl.symbolic as sls
from ..shader_templates.common import RenderMode

# Maps render mode to the corresponding MatSolid class
solid_map = {
    RenderMode.V1: sls.MatSolidV1,
    RenderMode.V2: sls.MatSolidV2,
    RenderMode.V3: sls.MatSolidV3,
    RenderMode.V4: sls.MatSolidV4,
    RenderMode.V5: sls.MatSolidV4,  # V5 uses same solid type as V4
    RenderMode.V6: sls.MatSolidV2,  # V6 uses same solid type as V2
}


def convert_solid_types(expression, version=RenderMode.V1):
    """
    Convert generic MatSolid expressions to version-specific solid types.
    
    Args:
        expression: A SySL expression tree
        version: Render mode version (e.g., RenderMode.V1, RenderMode.V4)
        
    Returns:
        Expression with MatSolid nodes converted to the appropriate version
    """
    if isinstance(expression, sls.MatSolid):
        args = expression.get_args()
        new_args = []
        for arg in args:
            new_arg = convert_solid_types(arg, version)
            new_args.append(new_arg)
        return solid_map[version](*new_args)
    elif isinstance(expression, gls.GLFunction):
        args = expression.get_args()
        new_args = []
        for arg in args:
            new_arg = convert_solid_types(arg, version)
            new_args.append(new_arg)
        return expression.__class__(*new_args)
    else:
        return expression