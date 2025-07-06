from .shader_module import register_shader_module, ShaderModule, SMMap
from string import Template
import geolipi.symbolic as gls
# Template for 2-argument functions
BASE_TEMPLATE = Template("""
${type} ${func_name}( ${type} d1, ${type} d2 )
{
	return (${condition}) ? d1 : d2;
}
""")

# Template for n-argument functions
NARY_TEMPLATE = Template("""
${type} ${func_name}(${args})
{
    return ${inner_code};
}
""")

# Operation definitions
OPERATIONS = {
    "Union": {
        "float": "d1<d2",
        "vec": "d1.x<d2.x"
    },
    "Intersection": {
        "float": "d1>d2", 
        "vec": "d1.x>d2.x"
    }
}

# Supported types
VECTOR_TYPES = ["vec2", "vec3", "vec4"]
ALL_TYPES = ["float"] + VECTOR_TYPES

class NAryShaderModule(ShaderModule):
    def __init__(self, name, *args, **kwargs):
        code = None
        dependencies = []
        vardeps = []
        inputs = None
        outputs = None
        super().__init__(name, code, dependencies=dependencies, vardeps=vardeps, inputs=inputs, outputs=outputs)
        self.func_name = name
        self.input_formats = []
    
    def register_hit(self, *args, **kwargs):
        input_format = kwargs.get("input_format", None)
        assert input_format is not None, "Input format is required"
        self.input_formats.append(input_format)
        self.hit_count += 1

    def generate_code(self):
        # Group input formats by type
        type_to_arities = {}
        for input_format in self.input_formats:
            if isinstance(input_format, tuple) and len(input_format) >= 2:
                input_type, arity = input_format[0], input_format[1]
                if input_type not in type_to_arities:
                    type_to_arities[input_type] = set()
                type_to_arities[input_type].add(arity)
        
        # For each type, determine all required functions (including dependencies)
        all_required_functions = set()
        for input_type, arities in type_to_arities.items():
            required_arities = set()
            for arity in arities:
                self._collect_required_arities(arity, required_arities)
            
            # Add all combinations of type and arity to required functions
            for arity in required_arities:
                all_required_functions.add((input_type, arity))
        
        # Generate code for each required function
        code_parts = []
        # Sort by arity to ensure base cases come first
        sorted_functions = sorted(all_required_functions, key=lambda x: x[1])
        
        for input_type, arity in sorted_functions:
            code_parts.append(self._generate_function_for_type_and_arity(input_type, arity))
        
        # Join all code parts
        self.code = "\n".join(code_parts)
    
    def _collect_required_arities(self, arity, required_arities):
        """Recursively collect all required arities for a given arity"""
        if arity in required_arities:
            return
        
        required_arities.add(arity)
        
        if arity <= 2:
            return
        
        # Decompose based on strategy
        if arity == 3:
            self._collect_required_arities(2, required_arities)
        elif arity == 4:
            self._collect_required_arities(2, required_arities)
        else:
            # For higher arities, split roughly in half
            first_half = arity // 2
            second_half = arity - first_half
            self._collect_required_arities(first_half, required_arities)
            self._collect_required_arities(second_half, required_arities)
    
    def _generate_function_for_type_and_arity(self, input_type, arity):
        """Generate GLSL code for a specific type and arity combination"""
        if arity == 1:
            return self._generate_single_arg_function(input_type)
        elif arity == 2:
            return self._generate_base_function(input_type)
        else:
            return self._generate_nary_function(input_type, arity)
    
    def _generate_single_arg_function(self, input_type):
        """Generate function for single argument (identity function)"""
        return NARY_TEMPLATE.substitute(
            type=input_type,
            func_name=self.func_name,
            args=f"{input_type} d1",
            inner_code="d1"
        ).strip()
    
    def _generate_base_function(self, input_type):
        """Generate base 2-argument function"""
        # Get condition based on operation and type
        condition = self._get_condition_for_type(input_type)
        
        return BASE_TEMPLATE.substitute(
            type=input_type,
            func_name=self.func_name,
            condition=condition
        ).strip()
    
    def _generate_nary_function(self, input_type, arity):
        """Generate n-argument function with decomposition"""
        # Generate parameter list
        args = ", ".join(f"{input_type} d{i+1}" for i in range(arity))
        
        # Generate inner code based on decomposition strategy
        inner_code = self._generate_inner_code(arity)
        
        return NARY_TEMPLATE.substitute(
            type=input_type,
            func_name=self.func_name,
            args=args,
            inner_code=inner_code
        ).strip()
    
    def _get_condition_for_type(self, input_type):
        """Get the appropriate condition for the given type and operation"""
        if self.func_name not in OPERATIONS:
            # Default to Union behavior
            operation = OPERATIONS["Union"]
        else:
            operation = OPERATIONS[self.func_name]
        
        if input_type == "float":
            return operation["float"]
        else:
            return operation["vec"]
    
    def _generate_inner_code(self, arity):
        """Generate the inner code for n-argument functions"""
        if arity == 3:
            return f"{self.func_name}({self.func_name}(d1, d2), d3)"
        elif arity == 4:
            return f"{self.func_name}({self.func_name}(d1, d2), {self.func_name}(d3, d4))"
        else:
            # For higher arities, split roughly in half
            first_half = arity // 2
            second_half = arity - first_half
            
            # Generate first group parameters
            first_params = [f"d{i+1}" for i in range(first_half)]
            first_call = f"{self.func_name}({', '.join(first_params)})"
            
            # Generate second group parameters  
            second_params = [f"d{i+first_half+1}" for i in range(second_half)]
            second_call = f"{self.func_name}({', '.join(second_params)})"
            
            return f"{self.func_name}({first_call}, {second_call})"

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code

def union_factory():
    name = "Union"
    module = NAryShaderModule(name)
    return module

SMMap["Union"] = union_factory

def intersection_factory():
    name = "Intersection"
    module = NAryShaderModule(name)
    return module

SMMap["Intersection"] = intersection_factory


## OTHERS:

class FixedArityShaderModule(ShaderModule):
    def __init__(self, name, arity__to_code_map):
        code = None
        dependencies = []
        vardeps = []
        inputs = None
        outputs = None
        super().__init__(name, code, dependencies=dependencies, vardeps=vardeps, inputs=inputs, outputs=outputs)
        self.func_name = name
        self.input_formats = set()
        self.arity__to_code_map = arity__to_code_map
    
    def register_hit(self, *args, **kwargs):
        input_format = kwargs.get("input_format", None)
        assert input_format is not None, "Input format is required"
        self.input_formats.add(input_format)
        self.hit_count += 1
    
    def generate_code(self):
        code_parts = []
        for input_format in self.input_formats:
            arity_code = self.arity__to_code_map[input_format]
            code_parts.append(arity_code)
        self.code = "\n".join(code_parts)
    
    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code

## DIFFERENCE:

float_diff_code = """
float Difference( float sdf1, float sdf2 )
{
  return max(sdf1, -sdf2);
}
"""
n_ary_diff_code = Template("""
${type} Difference( ${type} res1, ${type} res2 )
{
  if (res1.x > -res2.x) {
    return res1;
  }else{
    res2.x = -res2.x;
    return res2;
  }
}
""")

diff_arity_map = {
    ("float", 2): float_diff_code,
    ("vec2", 2): n_ary_diff_code.substitute(type="vec2"),
    ("vec3", 2): n_ary_diff_code.substitute(type="vec3"),
    ("vec4", 2): n_ary_diff_code.substitute(type="vec4"),
}

def diff_factory():
    name = "Difference"
    module = FixedArityShaderModule(name, diff_arity_map)
    return module

SMMap["Difference"] = diff_factory


## SWITCHED DIFFERENCE:

float_switched_diff_code = """
float SwitchedDifference( float sdf1, float sdf2 )
{
  return max(-sdf1, sdf2);
}
"""
n_ary_switched_diff_code = Template("""
${type} SwitchedDifference( ${type} res1, ${type} res2 )
{
  if (-res1.x > res2.x) {
    res1.x = -res1.x;
    return res1;
  }else{
    return res2;
  }
}
""")

switched_diff_arity_map = {  
    ("float", 2): float_switched_diff_code,
    ("vec2", 2): n_ary_switched_diff_code.substitute(type="vec2"),
    ("vec3", 2): n_ary_switched_diff_code.substitute(type="vec3"),
    ("vec4", 2): n_ary_switched_diff_code.substitute(type="vec4"),
}

def switched_diff_factory():
    name = "SwitchedDifference"
    module = FixedArityShaderModule(name, switched_diff_arity_map)
    return module

SMMap["SwitchedDifference"] = switched_diff_factory


## COMPLEMENT:

complement_code = Template("""
${type} Complement( ${type} res )
{
  return -res;
}
""")
complement_arity_map = {
    ("float", 1): complement_code.substitute(type="float"),
    ("vec2", 1): complement_code.substitute(type="vec2"),
    ("vec3", 1): complement_code.substitute(type="vec3"),
    ("vec4", 1): complement_code.substitute(type="vec4"),
}

def complement_factory():
    name = "Complement"
    module = FixedArityShaderModule(name, complement_arity_map)
    return module

SMMap["Complement"] = complement_factory


## SMOOTH UNION:

smooth_union_float_code = """
float SmoothUnion( float res1, float res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2 - res1)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}
"""
smooth_union_vec_code = Template("""
${type} SmoothUnion( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}
""")

smooth_union_arity_map = {
    ("float", 2): smooth_union_float_code,
    ("vec2", 2): smooth_union_vec_code.substitute(type="vec2"),
    ("vec3", 2): smooth_union_vec_code.substitute(type="vec3"),
    ("vec4", 2): smooth_union_vec_code.substitute(type="vec4"),
}

def smooth_union_factory():
    name = "SmoothUnion"
    module = FixedArityShaderModule(name, smooth_union_arity_map)
    return module

SMMap["SmoothUnion"] = smooth_union_factory


## SMOOTH INTERSECTION:
smooth_intersection_float_code = """
float SmoothIntersection( float res1, float res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2-res1)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) + k*h*(1.0-h);
}
"""
smooth_intersection_vec_code = Template("""
${type} SmoothIntersection( ${type} res1, ${type} res2, float k )
{   
    float h = clamp( 0.5 - 0.5*(res2.x-res1.x)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) + k*h*(1.0-h);
}
""")

smooth_intersection_arity_map = {
    ("float", 2): smooth_intersection_float_code,
    ("vec2", 2): smooth_intersection_vec_code.substitute(type="vec2"),
    ("vec3", 2): smooth_intersection_vec_code.substitute(type="vec3"),
    ("vec4", 2): smooth_intersection_vec_code.substitute(type="vec4"),
}

def smooth_intersection_factory():
    name = "SmoothIntersection"
    module = FixedArityShaderModule(name, smooth_intersection_arity_map)
    return module   

SMMap["SmoothIntersection"] = smooth_intersection_factory


## SMOOTH DIFFERENCE:

smooth_difference_float_code = """
float SmoothDifference( float res1, float res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2+res1)/k, 0.0, 1.0 );
    return mix( res1, -res2, h ) + k*h*(1.0-h);
}
"""
smooth_difference_vec_code = Template("""
${type} SmoothDifference( ${type} res1, ${type} res2, float k )
{
    float h = clamp( 0.5 - 0.5*(res2.x+res1.x)/k, 0.0, 1.0 );
    res2.y = -res2.y;
    return mix( res1, -res2, h ) + k*h*(1.0-h);
}
""")

smooth_difference_arity_map = {
    ("float", 2): smooth_difference_float_code,
    ("vec2", 2): smooth_difference_vec_code.substitute(type="vec2"),
    ("vec3", 2): smooth_difference_vec_code.substitute(type="vec3"),
    ("vec4", 2): smooth_difference_vec_code.substitute(type="vec4"),
}

def smooth_difference_factory():
    name = "SmoothDifference"
    module = FixedArityShaderModule(name, smooth_difference_arity_map)
    return module

SMMap["SmoothDifference"] = smooth_difference_factory

## OTHERS:


Dilate3D = register_shader_module("""
@name Dilate3D
@inputs sdf
@outputs sdf
@dependencies
float Dilate3D( float sdf, float k)
{
    return sdf + k;
}
""")

Erode3D = register_shader_module("""
@name Erode3D
@inputs sdf
@outputs sdf
@dependencies
float Erode3D( float sdf, float k)
{
    return sdf - k;
}
""")
