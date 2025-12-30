"""
Shader function templates and factory functions.

This package contains all GLSL template definitions and factory functions
for generating shader modules.
"""

# Import factory functions to register them in SMMap
from .combinators import *
from .material_functions import *
from .grid_functions import * 
from .shader_functions_2d import *
from .shader_functions_3d import *

