# SDFGrid3D
# Custom nodes.
from .shader_module import register_shader_module, ShaderModule, SMMap
from string import Template

DEFAULT_BOUND_THRESHOLD = 0.1
class CustomFunctionShaderModule(ShaderModule):

    def __init__(self, template, *args, **kwargs):
        code = None
        dependencies = []
        vardeps = []
        inputs = None
        outputs = None
        name = "CustomFunction"
        super().__init__(name, code, dependencies=dependencies, vardeps=vardeps, inputs=inputs, outputs=outputs)
        self.function_names = set()
        self.template = template
    
    def register_hit(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def generate_code(self):
        raise NotImplementedError("Not implemented")

EncodedSDFGrid3DTemplate = Template("""
float ${func_name}( vec3 p )
{
  float box_sdf = Box3D(p, vec3(1.0));
  if (box_sdf < ${bound_threshold}) {
    // p is in -1 to 1. Convert to 0 1
    vec3 p_local = (p + 1.0) / 2.0;
    float sdf = texture(${texture_name}, p_local).r;
    return sdf;
  }else{
    return box_sdf;
  }
}""")

class EncodedSDFGrid3D(CustomFunctionShaderModule):
    def __init__(self, *args, **kwargs):
        template = EncodedSDFGrid3DTemplate
        name = "EncodedSDFGrid3D"
        super().__init__(template, *args, **kwargs)
        self.name = "EncodedSDFGrid3D"
        self.dependencies = ["Box3D"]
        self.bound_thresholds = []
        self.texture_names = []

    def register_hit(self, *args, **kwargs):
        texture_name = kwargs.get("texture_name", None)
        assert texture_name is not None, "Texture name is required"
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        bound_threshold = kwargs.get("bound_threshold", DEFAULT_BOUND_THRESHOLD)
        self.vardeps.append(texture_name)
        self.function_names.add(function_name)
        self.bound_thresholds.append(bound_threshold)
        self.texture_names.append(texture_name)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for ind, function_name in enumerate(self.function_names):
            code = self.template.substitute(texture_name=self.texture_names[ind], func_name=function_name, 
                                            bound_threshold=self.bound_thresholds[ind])
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code

SMMap["EncodedSDFGrid3D"] = EncodedSDFGrid3D