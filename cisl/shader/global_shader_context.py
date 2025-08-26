
from collections import deque, defaultdict
from typing import List, Dict, Set  
from string import Template
import sympy as sp
from .shader_module import SMMap, ShaderModule
from .local_shader_context import LocalShaderContext, SCENE_EXPR_PROPS, mat_master_template
from .strace_v1 import CONSTANTS, UNIFORMS, PRELIMINARIES
from .ubo import create_var_map_with_ubo, generate_glsl_var_declarations, generate_glsl_load_statements

GLSL_TEMPLATE = Template("""#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
precision highp sampler3D;
#endif
out vec4 fragColor;  // Define the output color variable

${INNER_CODE}

void main(void)
{
  ${LOAD_PARAMS_CALL}
  mainImage(fragColor, gl_FragCoord.xy);
}""")

ShaderToy_TEMPLATE = Template("""
${INNER_CODE}
void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
  ${LOAD_PARAMS_CALL}
  mainImage_ST(fragColor, fragCoord);
}
""")


class GlobalShaderContext:
    def __init__(self):
        self.shader_modules = {}
        self.uniforms = {}
        self.constants = {}
        self.local_sc = LocalShaderContext("SCENE_EXPRESSION", SCENE_EXPR_PROPS)
        self.codebook_stack = []
        self.custom_func_count = 0
        self.material_stack = []
        self.material_count = 0
        self.material_registry = {}
        self.texture_registry = {}
        self.var_map = {}
        self.var_map_base = {}
        self.set_to_ubo = False
        self.ubo_data = None

    def add_texture(self, texture_data):
        # pack the texture data. 
        name = texture_data["name"]
        self.texture_registry[name] = texture_data
    def create_var_map(self, var_map_base, set_to_ubo=True):
        """Create variable map with efficient UBO packing and store all related data."""
        # Store for reference
        self.var_map_base = var_map_base
        self.set_to_ubo = set_to_ubo
        
        # Create var map and UBO data using the new efficient packing
        self.var_map, self.ubo_data = create_var_map_with_ubo(var_map_base, set_to_ubo)

    def get_textures(self):
        return self.texture_registry
    


    def add_shader_module(self, module_name, *args, **kwargs):
        if module_name not in self.shader_modules:
            module = SMMap[module_name]()
            module.set_config(*args, **kwargs)
            self.shader_modules[module_name] = module
        else:
            module = self.shader_modules[module_name]
            module.register_hit(self, *args, **kwargs)
    
    def resolve_dependencies(self):
        """Recursively resolve all dependencies for shader modules."""
        # Keep track of modules we need to process
        to_process = set(self.shader_modules.keys())
        processed = set()
        
        while to_process:
            current_modules = list(to_process)
            to_process.clear()
            
            for module_name in current_modules:
                if module_name in processed:
                    continue
                    
                module = self.shader_modules[module_name]
                
                # Check if dependencies is a list or None
                if module.dependencies:
                    dependencies = module.dependencies if isinstance(module.dependencies, list) else [module.dependencies]
                    
                    for dep_name in dependencies:
                        if dep_name not in self.shader_modules:
                            # Check if dependency exists in SMMap
                            if dep_name in SMMap:
                                self.shader_modules[dep_name] = SMMap[dep_name]()
                                self.shader_modules[dep_name].set_config(constants=self.constants, 
                                                                      uniforms=self.uniforms)
                                to_process.add(dep_name)
                            else:
                                raise ValueError(f"Dependency '{dep_name}' not found in SMMap for module '{module_name}'")
                
                processed.add(module_name)
    
    def collect_variable_dependencies(self, settings):
        """Collect all variable dependencies from shader modules and populate constants/uniforms."""
        all_vardeps = set()
        var_settings = settings.get("variables", {})
        # Collect all variable dependencies from all shader modules
        for module_name, module in self.shader_modules.items():
            if module.vardeps:
                vardeps = module.vardeps if isinstance(module.vardeps, list) else [module.vardeps]
                all_vardeps.update(vardeps)
        
        # Populate constants and uniforms based on collected dependencies
        for var_name in all_vardeps:
            if var_name in CONSTANTS:
                self.constants[var_name] = CONSTANTS[var_name]
                if var_name in var_settings:
                    self.constants[var_name] = (self.constants[var_name][0], var_settings[var_name])
            elif var_name in UNIFORMS:
                self.uniforms[var_name] = UNIFORMS[var_name]
                if var_name in var_settings:
                    self.uniforms[var_name]["init_value"] = var_settings[var_name]
            elif var_name in self.texture_registry:
                # Its just a "temp" variable. 
                pass
            else:
                raise ValueError(f"Variable '{var_name}' not found in CONSTANTS, TEXTURES or UNIFORMS")

        convert_uniforms_to_constants = settings.get("convert_uniforms_to_constants", False)
        if convert_uniforms_to_constants:
            self.convert_uniforms_to_constants()
    def emit_constants(self) -> str:
        """Emit shader code to declare constants."""
        if not self.constants:
            return ""
        
        code_lines = ["// Constants"]
        for var_name, (var_type, value) in self.constants.items():
            if var_type == 'int':
                code_lines.append(f"const int {var_name} = {value};")
            elif var_type == 'float':
                code_lines.append(f"const float {var_name} = {value};")
            elif var_type == 'vec2':
                if isinstance(value, tuple) and len(value) == 2:
                    code_lines.append(f"const vec2 {var_name} = vec2({value[0]}, {value[1]});")
                else:
                    code_lines.append(f"const vec2 {var_name} = {value};")
            elif var_type == 'vec3':
                if isinstance(value, tuple) and len(value) == 3:
                    code_lines.append(f"const vec3 {var_name} = vec3({value[0]}, {value[1]}, {value[2]});")
                else:
                    code_lines.append(f"const vec3 {var_name} = {value};")
            elif var_type == 'vec4':
                if isinstance(value, tuple) and len(value) == 4:
                    code_lines.append(f"const vec4 {var_name} = vec4({value[0]}, {value[1]}, {value[2]}, {value[3]});")
                else:
                    code_lines.append(f"const vec4 {var_name} = {value};")
            elif var_type == 'bool':
                code_lines.append(f"const bool {var_name} = {str(value).lower()};")
            else:
                code_lines.append(f"const {var_type} {var_name} = {value};")
        
        code_lines.append("")  # Empty line for separation
        return "\n".join(code_lines)
    
    def emit_uniforms(self) -> str:
        """Emit shader code to declare uniforms."""
        if not self.uniforms:
            return ""
        
        code_lines = ["// Uniforms"]
        for var_name, var_info in self.uniforms.items():
            var_type = var_info['type']
            code_lines.append(f"uniform {var_type} {var_name};")
        
        code_lines.append("")  # Empty line for separation
        return "\n".join(code_lines)
    
    def emit_textures(self) -> str:
        """Emit shader code to declare textures."""
        if not self.texture_registry:
            return ""
        
        code_lines = ["// Textures"]
        for var_name, var_info in self.texture_registry.items():
            shape = var_info['shape']
            if len(shape) == 2:
                code_lines.append(f"uniform sampler2D {var_name};")
            elif len(shape) == 3:
                code_lines.append(f"uniform sampler3D {var_name};")
            elif len(shape) == 4:
                code_lines.append(f"uniform sampler3D {var_name};")
            else:
                raise ValueError(f"Invalid texture shape: {shape}")
        
        code_lines.append("")  # Empty line for separation
        return "\n".join(code_lines)
    
    def emit_varlinking(self, settings) -> str:
        """Emit shader code to link variables (lightweight version)."""
        if not self.var_map:
            return None
        
        # Check if we should use #define directives instead of loadParams
        use_define_vars = settings.get("use_define_vars", False)
        
        code_lines = ["// Varlinking"]
        
        # Emit UBO declaration if using UBO
        if self.set_to_ubo and self.ubo_data:
            n_vec4s = self.ubo_data['n_vec4s']
            code_lines.append(f"layout(std140) uniform UBO_PARAMS_MASTER {{")
            code_lines.append(f"    vec4 UBO_PARAMS[{n_vec4s}];")
            code_lines.append("};")
        
        # Generate variable declarations and assignments
        if self.set_to_ubo and self.ubo_data:
            if use_define_vars:
                # Use #define directives for direct variable mapping
                code_lines.append("// Variable definitions using #define")
                var_mapping = self.ubo_data['var_mapping']
                
                for var_name, mapping_info in var_mapping.items():
                    vec4_index = mapping_info['vec4_index']
                    components = mapping_info['components']
                    var_type = mapping_info['type']
                    
                    # Generate appropriate #define based on variable type
                    if var_type == 'bool':
                        # Convert float back to bool for #define
                        code_lines.append(f"#define {var_name} (UBO_PARAMS[{vec4_index}].{components} > 0.5)")
                    elif var_type == 'int':
                        # Convert float to int for #define
                        code_lines.append(f"#define {var_name} int(UBO_PARAMS[{vec4_index}].{components})")
                    else:
                        # Direct assignment for float, vec2, vec3, vec4
                        code_lines.append(f"#define {var_name} UBO_PARAMS[{vec4_index}].{components}")
                
                # Create empty loadParams function (still needed for compatibility)
                code_lines.append("void loadParams() {")
                code_lines.append("    // Variables initialized via #define directives")
                code_lines.append("}")
            else:
                # Use traditional variable declarations + loadParams function
                var_declarations = generate_glsl_var_declarations(self.ubo_data['var_mapping'])
                code_lines.extend(var_declarations)
                
                # Generate loadParams function
                load_statements = generate_glsl_load_statements(self.ubo_data['var_mapping'])
                code_lines.append("void loadParams() {")
                code_lines.extend(load_statements)
                code_lines.append("}")
        else:
            # Fallback to inline declarations and assignments (non-UBO case)
            if use_define_vars:
                # Use #define directives for inline values
                code_lines.append("// Variable definitions using #define")
                for var_name, var_info in self.var_map.items():
                    var_type, var_value = var_info["type"], var_info["value"]
                    code_lines.append(f"#define {var_name} {var_value}")
                
                # Create empty loadParams function
                code_lines.append("void loadParams() {")
                code_lines.append("    // Variables initialized via #define directives")
                code_lines.append("}")
            else:
                # Use traditional variable declarations + loadParams function
                function_lines = []
                for var_name, var_info in self.var_map.items():
                    var_type, var_value = var_info["type"], var_info["value"]
                    code_lines.append(f"{var_type} {var_name};")
                    function_lines.append(f"    {var_name} = {var_value};")
                code_lines.append("void loadParams() {")
                code_lines.extend(function_lines)
                code_lines.append("}")
        
        code_lines.append("")  # Empty line for separation
        return "\n".join(code_lines)

    def topological_sort(self) -> List[str]:
        """Perform topological sort of shader modules based on dependencies."""
        # Build the dependency graph
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        
        # Initialize in_degree for all modules
        for module_name in self.shader_modules:
            in_degree[module_name] = 0
        
        # Build graph and calculate in-degrees
        for module_name, module in self.shader_modules.items():
            if module.dependencies:
                dependencies = module.dependencies if isinstance(module.dependencies, list) else [module.dependencies]
                for dep_name in dependencies:
                    graph[dep_name].append(module_name)
                    in_degree[module_name] += 1
        
        # Kahn's algorithm for topological sorting
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for circular dependencies
        if len(result) != len(self.shader_modules):
            raise ValueError("Circular dependency detected in shader modules")
        
        return result
    def resolve_codebook(self):
        # More Processing based on the sdf and pos stack. 
        self.local_sc.resolve_code()
        codebook_module = self.local_sc.emit_shadermodule()
        self.shader_modules[self.local_sc.name] = codebook_module

    def push_codebook(self, name, scene_expr_props):
        self.codebook_stack.append(self.local_sc)
        self.local_sc = LocalShaderContext(name, scene_expr_props)

    def pop_codebook(self):
        # Save certain information - 
        self.local_sc = self.codebook_stack.pop()

    def emit_shader_code(self, settings) -> str:
        """Emit complete shader code including constants, uniforms, and modules."""
        # First resolve all dependencies
        self.resolve_dependencies()
        
        # Collect variable dependencies and populate constants/uniforms
        self.collect_variable_dependencies(settings)
        
        # Get topologically sorted modules
        sorted_modules = self.topological_sort()
        
        # Build complete shader code
        code_blocks = [PRELIMINARIES]

        # Emit constants first
        constants_code = self.emit_constants()
        if constants_code:
            code_blocks.append(constants_code)
        
        # Emit uniforms
        uniforms_code = self.emit_uniforms()
        if uniforms_code:
            code_blocks.append(uniforms_code)
        
        # varlinking code
        varlinking_code = self.emit_varlinking(settings)
        if varlinking_code:
            load_params_call = "loadParams();"
            code_blocks.append(varlinking_code)
        else:
            load_params_call = ""

        # Emit textures
        textures_code = self.emit_textures()
        if textures_code:
            code_blocks.append(textures_code)
        # Emit shader modules in topological order
        for module_name in sorted_modules:
            module = self.shader_modules[module_name]
            code = module.emit_code()
            if code:
                code_blocks.append(f"// Module: {module_name}")
                code_blocks.append(code)
                code_blocks.append("")  # Empty line for separation
        inner_code = "\n".join(code_blocks)


        if settings.get("target", "GLSL") == "GLSL":
            real_code = GLSL_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
        elif settings.get("target", "GLSL") == "ShaderToy":
            #  rename MainImage.
            inner_code = inner_code.replace("void mainImage", "void mainImage_ST")
            real_code = ShaderToy_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
        else:
            raise ValueError(f"Invalid target: {settings.get('target', 'GLSL')}")
        return real_code
    def get_uniforms(self):
        new_uniforms = {}
        new_uniforms.update(self.uniforms)
        
        # Add UBO data if it was created during var map creation
        if self.set_to_ubo and self.ubo_data:
            new_uniforms["UBO_PARAMS"] = {
                "type": "uniform_buffer",
                "binding": 0,  # UBO binding point
                **self.ubo_data  # Include data_b64, shape, dtype, n_vec4s, var_mapping
            }
        
        return new_uniforms
    
    def convert_uniforms_to_constants(self):
        del_names = []
        for var_name, var_info in self.uniforms.items():
            value = var_info["init_value"]
            if isinstance(value, List):
                value = tuple(value)
            self.constants[var_name] = (var_info["type"], value)
            del_names.append(var_name)
        for var_name in del_names:
            del self.uniforms[var_name]

    def get_shader_modules(self):
        return self.shader_modules

    def resolve_material_stack(self):
        cases = []
        dependencies = []
        for mat_func_name, mat_index in self.material_registry.items():
            cases.append(f"case {mat_index}: return {mat_func_name}(p, n);")
            # cases.append(f"case {mat_index}: return MatBricks(p, n);")
            dependencies.append(f"{mat_func_name}")
        dependencies.append("BaseMaterials")
        dependencies.append("MatPlastic")
        mat_switch_cases = "\n".join(cases)
        mat_func_code = mat_master_template.substitute(mat_switch_cases=mat_switch_cases)
        def scene_mat_factory():
            scene_mat_module = ShaderModule("SCENE_MATERIAL", mat_func_code, dependencies)
            return scene_mat_module
        SMMap["SCENE_MATERIAL"] = scene_mat_factory
        self.add_shader_module("SCENE_MATERIAL")
# An online Code book -> which will be used to create SCENE_EXPRESSION function.
