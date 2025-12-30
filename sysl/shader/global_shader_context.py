"""
Global shader context for managing shader generation state.

This module provides the GlobalShaderContext class which maintains global state
during shader code generation, including:
- Shader module registry and dependency resolution
- Uniform and constant variable management
- Texture registry for 2D/3D textures
- Variable linking via UBO or inline code
- Topological sorting of shader modules for correct emission order

The context coordinates between LocalShaderContext instances (for individual
functions) and the overall shader assembly process.
"""

from collections import deque, defaultdict
from typing import List, Dict, Set, Tuple, Any, Optional
from string import Template
import sympy as sp
from .shader_module import SMMap, ShaderModule
from .local_shader_context import LocalShaderContext, SCENE_EXPR_PROPS, mat_master_template
from .shader_templates.common import CONSTANTS, UNIFORMS, PRELIMINARIES
from .utils.ubo import create_var_map_with_ubo, generate_ubo_glsl_code, generate_inline_glsl_code
from .utils.ubo import create_var_map_with_param_to_texture, generate_param_to_texture_glsl_code
from .utils.ubo import _get_variable_type_and_value, _to_float

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

GLSL_SDF_TRACE_TEMPLATE = Template("""#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
precision highp sampler3D;
#endif
out vec4 fragColor;  // Define the output color variable (only .r will be stored in R32F FBO)

${INNER_CODE}

void main(void)
{
  ${LOAD_PARAMS_CALL}
  main_sdf_trace(fragColor, gl_FragCoord.xy);
}""")

GLSL_POST_SDF_TRACE_TEMPLATE = Template("""#version 300 es
#ifdef GL_ES
precision highp float;
precision highp sampler2D;
precision highp sampler3D;
#endif
out vec4 fragColor;  // Define the output color variable
uniform sampler2D distance_travelled;

${INNER_CODE}

void main(void)
{
  ${LOAD_PARAMS_CALL}
  mainImage_post_trace(fragColor, gl_FragCoord.xy);
}""")


class GlobalShaderContext:
    """
    Global context for managing shader code generation state.
    
    Maintains shader modules, uniforms, constants, textures, and coordinates
    the assembly of complete shader programs from symbolic expressions.
    """
    
    def __init__(self) -> None:
        self.shader_modules: Dict[str, ShaderModule] = {}
        self.uniforms: Dict[str, Dict[str, Any]] = {}
        self.constants: Dict[str, Tuple[str, Any]] = {}
        self.local_sc: LocalShaderContext = LocalShaderContext("SCENE_EXPRESSION", SCENE_EXPR_PROPS)
        self.codebook_stack: List[LocalShaderContext] = []
        self.custom_func_count: int = 0
        self.material_stack: List[str] = []
        self.material_count: int = 0
        self.material_registry: Dict[str, int] = {}
        self.texture_registry: Dict[str, Dict[str, Any]] = {}
        self.var_map: Dict[str, Dict[str, str]] = {}
        self.var_map_base: Dict[str, Any] = {}
        self.set_to_ubo: bool = False
        self.ubo_data: Optional[Dict[str, Any]] = None
        self.prim_count: int = 0

    def add_texture(self, texture_data: Dict[str, Any]) -> None:
        """Add a texture to the registry."""
        name = texture_data["name"]
        self.texture_registry[name] = texture_data
        
    def create_var_map(self, var_map_base: Dict[str, Any], 
                       set_to_ubo: bool = False, 
                       set_param_to_texture: bool = False) -> None:
        """Create variable map and delegate UBO processing to UBO module."""
        self.var_map_base = var_map_base
        self.set_to_ubo = set_to_ubo
        self.set_param_to_texture = set_param_to_texture
        if set_to_ubo and set_param_to_texture:
            raise ValueError("Cannot set both UBO and param to texture")
        if set_to_ubo:
            self.var_map, self.ubo_data = create_var_map_with_ubo(var_map_base)
            
        if set_param_to_texture:
            self.var_map, texture_data = create_var_map_with_param_to_texture(var_map_base)
            self.add_texture(texture_data)
            self.ubo_data = None
        else:
            # Create inline variable map (original behavior)
            var_map = {}
            for var_name, param in var_map_base.items():

                var_type, normalized_value = _get_variable_type_and_value(param)
                
                # Generate GLSL value string based on type
                if var_type == "float":
                    var_value = str(normalized_value)
                elif var_type == "bool":
                    var_value = "true" if normalized_value else "false"
                elif var_type in ["vec2", "vec3", "vec4"]:
                    components = ", ".join(str(_to_float(x)) for x in normalized_value)
                    var_value = f"{var_type}({components})"
                else:
                    raise NotImplementedError(f"Unsupported variable type: {var_type}")
                    
                var_map[var_name] = {"type": var_type, "value": var_value}
                
            self.var_map = var_map
            self.ubo_data = None
            self.param_texture_data = None


    def get_textures(self) -> Dict[str, Dict[str, Any]]:
        """Return the texture registry."""
        return self.texture_registry

    def add_shader_module(self, module_name: str, *args: Any, **kwargs: Any) -> None:
        """Add or update a shader module in the context."""
        if module_name not in self.shader_modules:
            module = SMMap[module_name]()
            module.set_config(*args, **kwargs)
            self.shader_modules[module_name] = module
        else:
            module = self.shader_modules[module_name]
            module.register_hit(self, *args, **kwargs)
    
    def resolve_dependencies(self) -> None:
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
    
    def collect_variable_dependencies(self, settings: Dict[str, Any]) -> None:
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
                code_lines.append(f"uniform sampler2D {var_name};")
            elif len(shape) == 4:
                code_lines.append(f"uniform sampler3D {var_name};")
            else:
                raise ValueError(f"Invalid texture shape: {shape}")
        
        code_lines.append("")  # Empty line for separation
        return "\n".join(code_lines)
    
    def emit_varlinking(self, settings: Dict[str, Any]) -> Tuple[str, str]:
        """
        Emit shader code to link variables using UBO module.
        
        Returns:
            Tuple of (variable_declarations, load_params_function)
        """
        if not self.var_map:
            return "", "void loadParams() {}"
        
        use_define_vars = settings.get("use_define_vars", False)
        
        if self.set_to_ubo and self.ubo_data:
            # Delegate UBO code generation to UBO module
            return generate_ubo_glsl_code(self.ubo_data, use_define_vars)
        elif self.set_param_to_texture:
            return generate_param_to_texture_glsl_code(self.var_map)
        else:
            # Delegate inline code generation to UBO module
            return generate_inline_glsl_code(self.var_map, use_define_vars)

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
    def resolve_codebook(self) -> None:
        """Finalize the current codebook and add it as a shader module."""
        self.local_sc.resolve_code()
        codebook_module = self.local_sc.emit_shadermodule()
        self.shader_modules[self.local_sc.name] = codebook_module

    def push_codebook(self, name: str, scene_expr_props: Dict[str, str]) -> None:
        """Push current local context and create a new one for a nested function."""
        self.codebook_stack.append(self.local_sc)
        self.local_sc = LocalShaderContext(name, scene_expr_props)

    def pop_codebook(self) -> None:
        """Restore the previous local context from the stack."""
        self.local_sc = self.codebook_stack.pop()

    def emit_shader_code(self, settings: Dict[str, Any], version: str = "default") -> str:
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
        

        # Emit textures
        textures_code = self.emit_textures()
        if textures_code:
            code_blocks.append(textures_code)
        # Emit shader modules in topological order

        # varlinking code
        varlinking_declarations, load_params_function = self.emit_varlinking(settings)
        if varlinking_declarations:
            load_params_call = "loadParams();"
            code_blocks.append(varlinking_declarations)
            code_blocks.append(load_params_function)
        else:
            load_params_call = ""
            
        for module_name in sorted_modules:
            module = self.shader_modules[module_name]
            code = module.emit_code()
            if code:
                code_blocks.append(f"// Module: {module_name}")
                code_blocks.append(code)
                code_blocks.append("")  # Empty line for separation
        inner_code = "\n".join(code_blocks)

        if version == "default":
            if settings.get("target", "GLSL") == "GLSL":
                real_code = GLSL_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
            elif settings.get("target", "GLSL") == "ShaderToy":
                #  rename MainImage.
                inner_code = inner_code.replace("void mainImage", "void mainImage_ST")
                real_code = ShaderToy_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
            else:
                raise ValueError(f"Invalid target: {settings.get('target', 'GLSL')}")
        elif version == "sdf_trace":
            real_code = GLSL_SDF_TRACE_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
        elif version == "post_sdf_trace":
            real_code = GLSL_POST_SDF_TRACE_TEMPLATE.substitute(INNER_CODE=inner_code, LOAD_PARAMS_CALL=load_params_call)
        else:
            raise ValueError(f"Invalid version: {version}")

        return real_code
    def get_uniforms(self) -> Dict[str, Dict[str, Any]]:
        """Get uniforms including UBO data if available."""
        uniforms = self.uniforms.copy()
        
        if self.set_to_ubo and self.ubo_data:
            uniforms["UBO_PARAMS"] = {
                "type": "uniform_buffer", 
                "binding": 0,
                **self.ubo_data
            }
        
        return uniforms
    
    def convert_uniforms_to_constants(self) -> None:
        """Convert all uniforms to constants for static compilation."""
        del_names = []
        for var_name, var_info in self.uniforms.items():
            value = var_info["init_value"]
            if isinstance(value, List):
                value = tuple(value)
            self.constants[var_name] = (var_info["type"], value)
            del_names.append(var_name)
        for var_name in del_names:
            del self.uniforms[var_name]

    def get_shader_modules(self) -> Dict[str, ShaderModule]:
        """Return all registered shader modules."""
        return self.shader_modules

    def resolve_material_stack(self, version: str = "v3") -> None:
        cases = []
        dependencies = []
        for mat_func_name, mat_index in self.material_registry.items():
            cases.append(f"case {mat_index}: return {mat_func_name}(p, n);")
            # cases.append(f"case {mat_index}: return MatBricks(p, n);")
            dependencies.append(f"{mat_func_name}")
        if version == "v3":
            dependencies.append("BaseMaterials")
            dependencies.append("MatPlastic")
        else:
            raise ValueError(f"Invalid version: {version}")
        mat_switch_cases = "\n".join(cases)
        mat_func_code = mat_master_template.substitute(mat_switch_cases=mat_switch_cases)
        def scene_mat_factory():
            scene_mat_module = ShaderModule("SCENE_MATERIAL", mat_func_code, dependencies)
            return scene_mat_module
        SMMap["SCENE_MATERIAL"] = scene_mat_factory
        self.add_shader_module("SCENE_MATERIAL")
# An online Code book -> which will be used to create SCENE_EXPRESSION function.
