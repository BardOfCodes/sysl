"""
Shader module class definitions for template-based shader generation.

This module contains the core classes used for generating shader code from templates,
separated from the actual template definitions for better organization.
"""

from .shader_module import ShaderModule
from string import Template


class NAryShaderModule(ShaderModule):
    """
    Shader module for generating n-ary operations with dynamic arity support.
    
    This class generates shader functions that can handle operations with varying
    numbers of arguments by decomposing them into binary operations.
    """
    
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
        if input_format[0] not in ["float", "vec2", "vec3", "vec4"]:
            self.dependencies.append(input_format[0])
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
        from .shader_templates.functions.combinator_templates import NARY_TEMPLATE
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
        
        from .shader_templates.functions.combinator_templates import BASE_TEMPLATE
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
        
        from .shader_templates.functions.combinator_templates import NARY_TEMPLATE
        return NARY_TEMPLATE.substitute(
            type=input_type,
            func_name=self.func_name,
            args=args,
            inner_code=inner_code
        ).strip()
    
    def _get_condition_for_type(self, input_type):
        """Get the appropriate condition for the given type and operation"""
        from .shader_templates.functions.combinator_templates import OPERATIONS
        
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


class FixedArityShaderModule(ShaderModule):
    """
    Shader module for operations with fixed arity and predefined templates.
    
    This class handles shader functions where the code is predefined for specific
    input type and arity combinations.
    """
    
    def __init__(self, name, arity_to_code_map):
        code = None
        dependencies = []
        vardeps = []
        inputs = None
        outputs = None
        super().__init__(name, code, dependencies=dependencies, vardeps=vardeps, inputs=inputs, outputs=outputs)
        self.func_name = name
        self.input_formats = set()
        self.arity_to_code_map = arity_to_code_map
    
    def register_hit(self, *args, **kwargs):
        input_format = kwargs.get("input_format", None)
        assert input_format is not None, "Input format is required"
        self.input_formats.add(input_format)
        if input_format[0] not in ["float", "vec2", "vec3", "vec4"]:
            self.dependencies.append(input_format[0])
        self.hit_count += 1
    
    def generate_code(self):
        code_parts = []
        for input_format in self.input_formats:
            arity_code = self.arity_to_code_map[input_format]
            code_parts.append(arity_code)
        self.code = "\n".join(code_parts)
    
    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


class CustomFunctionShaderModule(ShaderModule):

    def __init__(self, name=None, template=None, *args, **kwargs):
        code = None
        dependencies = []
        vardeps = []
        inputs = None
        outputs = None
        if name is None:
          name = "CustomFunction"
        super().__init__(name, code, dependencies=dependencies, vardeps=vardeps, inputs=inputs, outputs=outputs)
        self.function_names = set()
        self.template = template
    
    def register_hit(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def generate_code(self):
        raise NotImplementedError("Not implemented")
