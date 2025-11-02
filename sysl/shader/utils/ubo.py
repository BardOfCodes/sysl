"""
UBO (Uniform Buffer Object) packing and management utilities.

This module provides efficient packing of shader variables into UBO format,
optimizing memory usage by grouping similar types together.
"""

import base64
import zlib
import numpy as np
import sympy as sp
from typing import Dict, List, Tuple, Any, Optional, Union

# Type aliases for better readability
VarMapBase = Dict[str, Any]
VarMapping = Dict[str, Dict[str, Any]]
ClassifiedVars = Dict[str, List[Tuple[str, Any]]]
UBODataDict = Dict[str, Any]

# Constants
VARIABLE_TYPES = ['float', 'bool', 'vec2', 'vec3', 'vec4']
COMPONENT_NAMES = ['x', 'y', 'z', 'w']

# Utility functions to reduce code repetition

def _to_float(value: Any) -> float:
    """Convert value to float, handling sympy integers."""
    if isinstance(value, sp.Integer):
        return float(value)
    return float(value)

def _normalize_vector(param: Any) -> List[float]:
    """Convert parameter to normalized float vector."""
    if hasattr(param, '__len__') and len(param) > 0:
        return [_to_float(x) for x in param]
    return [_to_float(param)]

def _get_variable_type_and_value(param: Any) -> Tuple[str, Any]:
    """Determine variable type and normalized value from parameter."""
    if isinstance(param, str):
        raise NotImplementedError("String parameters not supported in UBO")
    
    # Handle scalar values (including empty containers)
    if not hasattr(param, '__len__') or len(param) == 0:
        if isinstance(param, bool):
            return 'bool', param
        return 'float', _to_float(param)
    
    # Handle vectors
    length = len(param)
    if length == 1:
        return 'float', _to_float(param[0])
    elif length == 2:
        return 'vec2', _normalize_vector(param)
    elif length == 3:
        return 'vec3', _normalize_vector(param)
    elif length == 4:
        return 'vec4', _normalize_vector(param)
    else:
        raise ValueError(f"Parameter has too many components: {length}")

def classify_variables(var_map_base: VarMapBase) -> ClassifiedVars:
    """
    Classify variables by type for efficient packing.
    
    Args:
        var_map_base: Dictionary mapping variable names to their values
        
    Returns:
        Dictionary with keys: 'float', 'bool', 'vec2', 'vec3', 'vec4'
        Each containing list of (var_name, value) tuples
    """
    classified = {var_type: [] for var_type in VARIABLE_TYPES}
    
    for var_name, param in var_map_base.items():
        var_type, normalized_value = _get_variable_type_and_value(param)
        classified[var_type].append((var_name, normalized_value))
    
    return classified


# Additional utility functions for packing

def _create_var_mapping_entry(vec4_index: int, components: str, var_type: str) -> Dict[str, Any]:
    """Create a standardized variable mapping entry."""
    return {
        'vec4_index': vec4_index,
        'components': components,
        'type': var_type
    }

def _pack_scalars_to_vec4(vars_list: List[Tuple[str, Any]], var_type: str, 
                         convert_bool: bool = False) -> Tuple[List[List[float]], VarMapping]:
    """Pack scalar variables (floats/bools) into vec4s efficiently."""
    vec4_entries = []
    var_mapping = {}
    components = COMPONENT_NAMES
    
    # Process in groups of 4
    while len(vars_list) >= 4:
        group = vars_list[:4]
        vars_list = vars_list[4:]
        
        if convert_bool:
            vec4_components = [1.0 if value else 0.0 for _, value in group]
        else:
            vec4_components = [float(value) for _, value in group]
            
        vec4_index = len(vec4_entries)
        vec4_entries.append(vec4_components)
        
        for i, (var_name, _) in enumerate(group):
            var_mapping[var_name] = _create_var_mapping_entry(vec4_index, components[i], var_type)
    
    # Handle remaining variables (1-3)
    if vars_list:
        vec4_components = [0.0, 0.0, 0.0, 0.0]
        
        for i, (var_name, value) in enumerate(vars_list):
            if convert_bool:
                vec4_components[i] = 1.0 if value else 0.0
            else:
                vec4_components[i] = float(value)
        
        vec4_index = len(vec4_entries)
        vec4_entries.append(vec4_components)
        
        for i, (var_name, _) in enumerate(vars_list):
            var_mapping[var_name] = _create_var_mapping_entry(vec4_index, components[i], var_type)
    
    return vec4_entries, var_mapping

def pack_variables_to_vec4s(classified_vars: ClassifiedVars) -> Tuple[List[List[float]], VarMapping]:
    """
    Pack classified variables into vec4 entries efficiently.
    
    Packing strategy:
    - 4 floats -> 1 vec4
    - 4 bools -> 1 vec4 (as 0.0/1.0)
    - 2 vec2s -> 1 vec4
    - 1 vec3 + 1 float -> 1 vec4
    - 1 vec4 -> 1 vec4
    
    Args:
        classified_vars: Output from classify_variables()
        
    Returns:
        Tuple of:
        - List of vec4 entries (each is [x, y, z, w])
        - Variable mapping info: {var_name: {'vec4_index': int, 'components': str, 'type': str}}
    """
    vec4_entries = []
    var_mapping = {}
    
    # Helper function to add a vec4 entry
    def add_vec4(components: List[float]) -> int:
        assert len(components) == 4, f"Invalid vec4 components: {components}"
        vec4_entries.append(components)
        return len(vec4_entries) - 1
    
    # Process vec4s first (no packing needed)
    for var_name, vec4_val in classified_vars['vec4']:
        vec4_index = add_vec4(vec4_val)
        var_mapping[var_name] = _create_var_mapping_entry(vec4_index, 'xyzw', 'vec4')
    
    # Process vec3s with float padding  
    vec3_vars = classified_vars['vec3'].copy()
    float_vars = classified_vars['float'].copy()
    
    for var_name, vec3_val in vec3_vars:
        # Try to find a float to pack with this vec3
        padding_float = 0.0
        padding_var_name = None
        
        if float_vars:
            padding_var_name, padding_float = float_vars.pop(0)
        
        # Create vec4: [vec3.x, vec3.y, vec3.z, float]
        vec4_components = vec3_val + [padding_float]
        vec4_index = add_vec4(vec4_components)
        
        var_mapping[var_name] = _create_var_mapping_entry(vec4_index, 'xyz', 'vec3')
        
        if padding_var_name:
            var_mapping[padding_var_name] = _create_var_mapping_entry(vec4_index, 'w', 'float')
    
    # Process vec2s in pairs
    vec2_vars = classified_vars['vec2'].copy()
    while len(vec2_vars) >= 2:
        var1_name, vec2_val1 = vec2_vars.pop(0)
        var2_name, vec2_val2 = vec2_vars.pop(0)
        
        # Create vec4: [vec2_1.x, vec2_1.y, vec2_2.x, vec2_2.y]
        vec4_components = vec2_val1 + vec2_val2
        vec4_index = add_vec4(vec4_components)
        
        var_mapping[var1_name] = _create_var_mapping_entry(vec4_index, 'xy', 'vec2')
        var_mapping[var2_name] = _create_var_mapping_entry(vec4_index, 'zw', 'vec2')
    
    # Handle remaining single vec2s with float padding
    for var_name, vec2_val in vec2_vars:
        # Try to find 2 floats to pack with this vec2
        padding_floats = [0.0, 0.0]
        padding_var_names = [None, None]
        
        for i in range(2):
            if float_vars:
                padding_var_names[i], padding_floats[i] = float_vars.pop(0)
        
        # Create vec4: [vec2.x, vec2.y, float1, float2]
        vec4_components = vec2_val + padding_floats
        vec4_index = add_vec4(vec4_components)
        
        var_mapping[var_name] = _create_var_mapping_entry(vec4_index, 'xy', 'vec2')
        
        for i, padding_var_name in enumerate(padding_var_names):
            if padding_var_name:
                var_mapping[padding_var_name] = _create_var_mapping_entry(vec4_index, 'zw'[i], 'float')
    
    # Process remaining floats using helper function
    if float_vars:
        float_entries, float_mapping = _pack_scalars_to_vec4(float_vars, 'float')
        # Adjust indices to account for existing vec4s
        base_index = len(vec4_entries)
        for name, mapping in float_mapping.items():
            mapping['vec4_index'] += base_index
            var_mapping[name] = mapping
        vec4_entries.extend(float_entries)
    
    # Process remaining bools using helper function  
    bool_vars = classified_vars['bool'].copy()
    if bool_vars:
        bool_entries, bool_mapping = _pack_scalars_to_vec4(bool_vars, 'bool', convert_bool=True)
        # Adjust indices to account for existing vec4s
        base_index = len(vec4_entries)
        for name, mapping in bool_mapping.items():
            mapping['vec4_index'] += base_index
            var_mapping[name] = mapping
        vec4_entries.extend(bool_entries)
    
    return vec4_entries, var_mapping


# Data compression/decompression utilities

def _compress_float_array(data_array: np.ndarray) -> str:
    """Compress and base64 encode a numpy float array."""
    compressed = zlib.compress(data_array.tobytes())
    return base64.b64encode(compressed).decode('utf-8')

def _decompress_float_array(data_b64: str, shape: Tuple[int, ...], dtype: str) -> np.ndarray:
    """Decompress base64 encoded float array."""
    compressed_data = base64.b64decode(data_b64)
    decompressed_data = zlib.decompress(compressed_data)
    data_array = np.frombuffer(decompressed_data, dtype=dtype)
    return data_array.reshape(shape)

def _create_ubo_data_dict(data_array: np.ndarray, var_mapping: VarMapping, 
                         n_params: int = 1) -> UBODataDict:
    """Create standardized UBO data dictionary."""
    n_vec4s = data_array.shape[-1] // 4  # Last dimension should be K*4
    
    return {
        "data_b64": _compress_float_array(data_array),
        "shape": data_array.shape,
        "dtype": str(data_array.dtype),
        "n_vec4s": n_vec4s,
        "var_mapping": var_mapping,
        "n_params": n_params,
        "param_shape": (1, data_array.shape[-1]) if n_params > 1 else None
    }

def create_ubo_data(var_map_base: VarMapBase) -> Optional[UBODataDict]:
    """
    Create packed UBO data from variable map.
    
    Args:
        var_map_base: Dictionary mapping variable names to their values
        
    Returns:
        Dictionary containing UBO data or None if no variables
    """
    if not var_map_base:
        return None
    
    # Classify and pack variables
    classified_vars = classify_variables(var_map_base)
    vec4_entries, var_mapping = pack_variables_to_vec4s(classified_vars)
    
    if not vec4_entries:
        return None
    
    # Create numpy array for compression
    # Shape: (1, n_vec4s * 4) - 1 for current time step, will be (T, n_vec4s * 4) for animation
    n_vec4s = len(vec4_entries)
    ubo_data = np.zeros((1, n_vec4s * 4), dtype=np.float32)
    
    # Fill the array
    for i, vec4 in enumerate(vec4_entries):
        start_idx = i * 4
        ubo_data[0, start_idx:start_idx + 4] = vec4
    
    return _create_ubo_data_dict(ubo_data, var_mapping)


def create_param_texture_data(var_map_base: VarMapBase) -> Optional[UBODataDict]:
    """
    Create packed UBO data from variable map.
    
    Args:
        var_map_base: Dictionary mapping variable names to their values
        
    Returns:
        Dictionary containing UBO data or None if no variables
    """
    # Classify and pack variables
    classified_vars = classify_variables(var_map_base)
    vec4_entries, var_mapping = pack_variables_to_vec4s(classified_vars)
    
    if not vec4_entries:
        return None
    
    # Create numpy array for compression
    # Shape: (1, n_vec4s * 4) - 1 for current time step, will be (T, n_vec4s * 4) for animation
    n_vec4s = len(vec4_entries)
    data_array = np.zeros((1, n_vec4s, 4), dtype=np.float32)
    
    # Fill the array
    for i, vec4 in enumerate(vec4_entries):
        start_idx = i
        data_array[0, start_idx] = vec4
    
    # numpy code
    tex_shape = data_array.shape
    tex_dtype = str(data_array.dtype)
    compressed = zlib.compress(data_array.tobytes())
    b64_data = base64.b64encode(compressed).decode('utf-8')
    texture_data = {'name': "PARAM_TEX", 
                    'data_b64': b64_data,
                    'shape': tex_shape, 
                    'dtype': tex_dtype,
                    }
    return var_mapping, texture_data

def generate_glsl_var_declarations(var_mapping: VarMapping) -> List[str]:
    """
    Generate GLSL variable declarations from var mapping.
    
    Args:
        var_mapping: Variable mapping from pack_variables_to_vec4s()
        
    Returns:
        List of GLSL declaration strings
    """
    declarations = []
    
    for var_name, mapping_info in var_mapping.items():
        var_type = mapping_info['type']
        declarations.append(f"{var_type} {var_name};")
    
    return declarations


def generate_glsl_load_statements(var_mapping: VarMapping, ubo_name: str = "UBO_PARAMS") -> List[str]:
    """
    Generate GLSL load statements for loadParams() function.
    
    Args:
        var_mapping: Variable mapping from pack_variables_to_vec4s()
        ubo_name: Name of the UBO array in GLSL
        
    Returns:
        List of GLSL assignment strings
    """
    load_statements = []
    
    for var_name, mapping_info in var_mapping.items():
        vec4_index = mapping_info['vec4_index']
        components = mapping_info['components']
        var_type = mapping_info['type']
        
        if var_type == 'bool':
            # Convert float back to bool
            load_statements.append(f"    {var_name} = {ubo_name}[{vec4_index}].{components} > 0.5;")
        elif var_type == 'int':
            # Convert float to int
            load_statements.append(f"    {var_name} = int({ubo_name}[{vec4_index}].{components});")
        else:
            # Direct assignment for float, vec2, vec3, vec4
            load_statements.append(f"    {var_name} = {ubo_name}[{vec4_index}].{components};")
    
    return load_statements


def generate_ubo_glsl_code(ubo_data: Optional[UBODataDict], use_define_vars: bool = False, 
                          ubo_name: str = "UBO_PARAMS") -> Tuple[str, str]:
    """
    Generate complete UBO GLSL code including declarations and load function.
    
    Args:
        ubo_data: UBO data dictionary or None
        use_define_vars: Whether to use #define directives instead of loadParams
        ubo_name: Name of the UBO array in GLSL
        
    Returns:
        Tuple of (ubo_declarations, load_params_function)
    """
    if not ubo_data:
        return "", "void loadParams() {}"
    
    code_lines = ["// UBO Variables"]
    n_vec4s = ubo_data['n_vec4s']
    var_mapping = ubo_data['var_mapping']
    
    # UBO declaration
    code_lines.append(f"layout(std140) uniform UBO_PARAMS_MASTER {{")
    code_lines.append(f"    vec4 {ubo_name}[{n_vec4s}];")
    code_lines.append("};")
    
    if use_define_vars:
        # Use #define directives for direct variable mapping
        code_lines.append("// Variable definitions using #define")
        
        for var_name, mapping_info in var_mapping.items():
            vec4_index = mapping_info['vec4_index']
            components = mapping_info['components']
            var_type = mapping_info['type']
            
            # Generate appropriate #define based on variable type
            if var_type == 'bool':
                code_lines.append(f"#define {var_name} ({ubo_name}[{vec4_index}].{components} > 0.5)")
            elif var_type == 'int':
                code_lines.append(f"#define {var_name} int({ubo_name}[{vec4_index}].{components})")
            else:
                code_lines.append(f"#define {var_name} {ubo_name}[{vec4_index}].{components}")
        
        load_params_code = "void loadParams() {\n    // Variables initialized via #define directives\n}"
    else:
        # Use traditional variable declarations + loadParams function
        var_declarations = generate_glsl_var_declarations(var_mapping)
        code_lines.extend(var_declarations)
        
        # Generate loadParams function

        load_statements = []
        
        for var_name, mapping_info in var_mapping.items():
            vec4_index = mapping_info['vec4_index']
            components = mapping_info['components']
            var_type = mapping_info['type']
            
            if var_type == 'bool':
                code_lines.append(f"{var_name} = ({ubo_name}[{vec4_index}].{components} > 0.5)")
            elif var_type == 'int':
                code_lines.append(f"{var_name} = int({ubo_name}[{vec4_index}].{components})")
            else:
                code_lines.append(f"{var_name} = {ubo_name}[{vec4_index}].{components}")
                
        load_params_code = "void loadParams() {\n" + "\n".join(load_statements) + "\n}"
    
    ubo_declarations = "\n".join(code_lines)
    return ubo_declarations, load_params_code

def generate_param_to_texture_glsl_code( 
                    var_mapping: VarMapping,
                    use_define_vars: bool = False, 
                    param_name: str = "PARAM_TEX") -> Tuple[str, str]:
    """
    Generate complete UBO GLSL code including declarations and load function.
    
    Args:
        ubo_data: UBO data dictionary or None
        use_define_vars: Whether to use #define directives instead of loadParams
        ubo_name: Name of the UBO array in GLSL
        
    Returns:
        Tuple of (ubo_declarations, load_params_function)
    """
    code_lines = ["// Param to Texture Variables"]
    
    if not use_define_vars:

        # Use traditional variable declarations + loadParams function
        var_declarations = generate_glsl_var_declarations(var_mapping)
        code_lines.extend(var_declarations)
        
        # Generate loadParams function

        load_statements = []
        
        for var_name, mapping_info in var_mapping.items():
            vec4_index = mapping_info['vec4_index']
            components = mapping_info['components']
            var_type = mapping_info['type']
            
            if var_type == 'bool':
                load_statements.append(f"{var_name} = (texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components} > 0.5);")
            elif var_type == 'int':
                load_statements.append(f" {var_name} = int(texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components});")
            else:
                load_statements.append(f" {var_name} = texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components};")
                
        load_params_code = "void loadParams() {\n" + "\n".join(load_statements) + "\n}"
    else:
        # Use #define directives for direct variable mapping
        code_lines.append("// Variable definitions using #define")
        
        for var_name, mapping_info in var_mapping.items():
            vec4_index = mapping_info['vec4_index']
            components = mapping_info['components']
            var_type = mapping_info['type']
            
            # Generate appropriate #define based on variable 
            #  texelFetch(paramTex, ivec2(i, 0), 0);
            if var_type == 'bool':
                code_lines.append(f"#define {var_name} (texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components} > 0.5)")
            elif var_type == 'int':
                code_lines.append(f"#define {var_name} int(texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components})")
            else:
                code_lines.append(f"#define {var_name} texelFetch({param_name}, ivec2({vec4_index}, 0), 0).{components}")
        
        load_params_code = "void loadParams() {\n    // Variables initialized via #define directives\n}"
    param_declarations = "\n".join(code_lines)
    return param_declarations, load_params_code


def generate_inline_glsl_code(var_map: Dict[str, Dict[str, str]], use_define_vars: bool = False) -> Tuple[str, str]:
    """
    Generate inline variable GLSL code (non-UBO case).
    
    Args:
        var_map: Variable mapping with type and value
        use_define_vars: Whether to use #define directives instead of loadParams
        
    Returns:
        Tuple of (variable_declarations, load_params_function)
    """
    if not var_map:
        return "", "void loadParams() {}"
    
    code_lines = ["// Inline Variables"]
    
    if use_define_vars:
        # Use #define directives for inline values
        for var_name, var_info in var_map.items():
            var_type, var_value = var_info["type"], var_info["value"]
            code_lines.append(f"#define {var_name} {var_value}")
        
        load_params_code = "void loadParams() {\n    // Variables initialized via #define directives\n}"
    else:
        # Use traditional variable declarations + loadParams function
        function_lines = []
        for var_name, var_info in var_map.items():
            var_type, var_value = var_info["type"], var_info["value"]
            code_lines.append(f"{var_type} {var_name};")
            function_lines.append(f"    {var_name} = {var_value};")
        
        load_params_code = "void loadParams() {\n" + "\n".join(function_lines) + "\n}"
    
    variable_declarations = "\n".join(code_lines)
    return variable_declarations, load_params_code


def create_var_map_with_ubo(var_map_base: VarMapBase) -> Tuple[Dict[str, Dict[str, str]], Optional[UBODataDict]]:
    """
    Create variable map and UBO data in one step.
    
    Args:
        var_map_base: Dictionary mapping variable names to their values
        set_to_ubo: Whether to use UBO or inline values
        
    Returns:
        Tuple of:
        - Variable map: {var_name: {'type': str, 'value': str}}
        - UBO data: Dictionary with UBO info or None
    """
    if not var_map_base:
        return {}, None
    
    var_map = {}
    ubo_data = None
    
    # Create UBO data with efficient packing
    ubo_data = create_ubo_data(var_map_base)
    
    if ubo_data:
        var_mapping = ubo_data['var_mapping']
        ubo_name = "UBO_PARAMS"
        
        # Create var_map entries that reference UBO
        for var_name, mapping_info in var_mapping.items():
            vec4_index = mapping_info['vec4_index']
            components = mapping_info['components']
            var_type = mapping_info['type']
            
            var_value = f"{ubo_name}[{vec4_index}].{components}"
            var_map[var_name] = {"type": var_type, "value": var_value}
    
    return var_map, ubo_data


def create_var_map_with_param_to_texture(var_map_base: VarMapBase, set_to_) -> Tuple[Dict[str, Dict[str, str]], Optional[UBODataDict]]:
    """
    Create variable map and UBO data in one step.
    
    Args:
        var_map_base: Dictionary mapping variable names to their values
        set_to_ubo: Whether to use UBO or inline values
        
    Returns:
        Tuple of:
        - Variable map: {var_name: {'type': str, 'value': str}}
        - UBO data: Dictionary with UBO info or None
    """
    if not var_map_base:
        return {}, None
    
    var_map = {}
    
    # Create UBO data with efficient packing
    var_mapping, param_texture_dict = create_param_texture_data(var_map_base)
    
    ubo_name = "PARAM_TEX"
    
    # Create var_map entries that reference UBO
    # for var_name, mapping_info in var_mapping.items():
    #     vec4_index = mapping_info['vec4_index']
    #     components = mapping_info['components']
    #     var_type = mapping_info['type']
    #     # texelFetch(paramTex, ivec2(i, 0), 0);
    #     var_value = f"texelFetch({ubo_name}, ivec2({vec4_index}, 0), 0).{components}"
    #     var_map[var_name] = {"type": var_type, "value": var_value}
    return var_mapping, param_texture_dict



def get_variable_info_for_editing(ubo_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Get variable information formatted for frontend editing controls.
    
    Args:
        ubo_data: UBO data dictionary
        
    Returns:
        Dictionary with variable info for UI generation
    """
    if not ubo_data or 'var_mapping' not in ubo_data:
        return {}
    
    var_info = {}
    var_mapping = ubo_data['var_mapping']
    
    # Decompress current data to get current values
    try:
        data_array = _decompress_float_array(
            ubo_data['data_b64'], 
            ubo_data['shape'], 
            ubo_data['dtype']
        )
    except Exception:
        # If decompression fails, use default values
        data_array = None
    
    for var_name, mapping_info in var_mapping.items():
        vec4_index = mapping_info['vec4_index']
        components = mapping_info['components']
        var_type = mapping_info['type']
        
        # Extract current value if possible
        current_value = None
        if data_array is not None:
            base_idx = vec4_index * 4
            
            if var_type in ['float', 'bool']:
                component_idx = {'x': 0, 'y': 1, 'z': 2, 'w': 3}[components]
                current_value = float(data_array[0, base_idx + component_idx])
                if var_type == 'bool':
                    current_value = current_value > 0.5
            elif var_type == 'vec2':
                if components == 'xy':
                    current_value = data_array[0, base_idx:base_idx + 2].tolist()
                elif components == 'zw':
                    current_value = data_array[0, base_idx + 2:base_idx + 4].tolist()
            elif var_type == 'vec3':
                if components == 'xyz':
                    current_value = data_array[0, base_idx:base_idx + 3].tolist()
            elif var_type == 'vec4':
                if components == 'xyzw':
                    current_value = data_array[0, base_idx:base_idx + 4].tolist()
        
        var_info[var_name] = {
            'type': var_type,
            'current_value': current_value,
            'components': len(components) if var_type in ['float', 'bool'] else int(var_type[-1]) if var_type.startswith('vec') else 1
        }
    
    return var_info


def create_multi_param_ubo(expressions: List[Any], extract_vars: bool = True) -> Dict[str, Any]:
    """
    Create a multi-parameterization UBO from multiple expressions with different parameters.
    
    This function takes multiple expressions (same structure, different parameters) and creates
    a single UBO with shape (N, K*4) where N is the number of expressions and K*4 is the 
    flattened variable data size.
    
    Args:
        expressions: List of expressions with different parameterizations
        extract_vars: Whether to extract variables from expressions
        
    Returns:
        Dictionary with multi-parameter UBO data compatible with existing UBO system
    """
    if not expressions:
        raise ValueError("At least one expression is required")
    
    # Extract variable maps from all expressions
    var_map_bases = []
    for expr in expressions:
        if extract_vars:
            _, _, var_map_base = expr._get_varnamed_expr(exclude_uniforms=True)
        else:
            # If not extracting vars, assume expr is already a var_map_base dict
            var_map_base = expr
        var_map_bases.append(var_map_base)
    
    # Validate that all expressions have the same variable structure
    if len(var_map_bases) > 1:
        first_vars = set(var_map_bases[0].keys())
        for i, var_map_base in enumerate(var_map_bases[1:], 1):
            current_vars = set(var_map_base.keys())
            if first_vars != current_vars:
                raise ValueError(f"Expression {i} has different variables than expression 0: "
                               f"expected {first_vars}, got {current_vars}")
    
    # Create UBO data for each parameterization
    ubo_data_list = []
    for var_map_base in var_map_bases:
        ubo_data = create_ubo_data(var_map_base)
        if ubo_data is None:
            raise ValueError("Failed to create UBO data for one of the expressions")
        ubo_data_list.append(ubo_data)
    
    # Validate that all UBO data have the same structure
    first_shape = ubo_data_list[0]['shape']
    first_n_vec4s = ubo_data_list[0]['n_vec4s']
    first_var_mapping = ubo_data_list[0]['var_mapping']
    
    for i, ubo_data in enumerate(ubo_data_list[1:], 1):
        if (ubo_data['shape'] != first_shape or 
            ubo_data['n_vec4s'] != first_n_vec4s or
            ubo_data['var_mapping'] != first_var_mapping):
            raise ValueError(f"UBO structure mismatch at expression {i}")
    
    # Combine all UBO data into a single (N, K*4) array
    n_expressions = len(expressions)
    k_times_4 = first_shape[1]  # Original shape was (1, K*4)
    
    # Create combined array
    combined_data = np.zeros((n_expressions, k_times_4), dtype=np.float32)
    
    # Fill with data from each expression
    for i, ubo_data in enumerate(ubo_data_list):
        # Decompress individual data using utility function
        data_array = _decompress_float_array(
            ubo_data['data_b64'], 
            ubo_data['shape'], 
            ubo_data['dtype']
        )
        
        # Copy to combined array
        combined_data[i, :] = data_array[0, :]  # Extract from (1, K*4) to (K*4)
    
    # Create the multi-parameter UBO data structure using utility function
    multi_ubo_data = _create_ubo_data_dict(combined_data, first_var_mapping, n_expressions)
    
    return multi_ubo_data


def update_uniforms_with_multi_param_ubo(uniforms: Dict[str, Any], 
                                        expressions: List[Any],
                                        extract_vars: bool = True,
                                        ubo_name: str = "UBO_PARAMS") -> Dict[str, Any]:
    """
    Update existing uniforms dictionary with multi-parameter UBO data.
    
    This function takes a uniforms dict (from evaluate_to_shader) and replaces
    the existing UBO with a multi-parameter version.
    
    Args:
        uniforms: Original uniforms dictionary
        expressions: List of expressions with different parameterizations  
        extract_vars: Whether to extract variables from expressions
        ubo_name: Name of the UBO uniform to replace
        
    Returns:
        Updated uniforms dictionary with multi-parameter UBO
    """
    # Create multi-parameter UBO
    multi_ubo_data = create_multi_param_ubo(expressions, extract_vars)
    
    # Update uniforms
    updated_uniforms = uniforms.copy()
    
    # Replace or add the UBO entry
    updated_uniforms[ubo_name] = {
        "type": "uniform_buffer",
        "binding": uniforms.get(ubo_name, {}).get("binding", 0),
        **multi_ubo_data
    }
    
    return updated_uniforms
