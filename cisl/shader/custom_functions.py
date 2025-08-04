# SDFGrid3D
# Custom nodes.
from .shader_module import register_shader_module, ShaderModule, SMMap
from string import Template

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
    p_local = p_local.zyx;
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
        self.sdf_texture_names = []

    def register_hit(self, *args, **kwargs):
        sdf_texture_name = kwargs.get("sdf_texture_name", None)
        assert sdf_texture_name is not None, "Texture name is required"
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        bound_threshold = kwargs.get("bound_threshold", None)
        assert bound_threshold is not None, "Bound threshold is required"
        self.vardeps.append(sdf_texture_name)
        self.function_names.add(function_name)
        self.bound_thresholds.append(bound_threshold)
        self.sdf_texture_names.append(sdf_texture_name)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for ind, function_name in enumerate(self.function_names):
            code = self.template.substitute(texture_name=self.sdf_texture_names[ind], func_name=function_name, 
                                            bound_threshold=self.bound_thresholds[ind])
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


#  Custom material function. 
SMMap["EncodedSDFGrid3D"] = EncodedSDFGrid3D


EncodedRGBGrid3DTemplate = Template("""
Material ${func_name}( vec3 p, vec3 n)
{
  float box_sdf = Box3D(p, vec3(1.0));
  if (box_sdf < ${bound_threshold}) {
    // p is in -1 to 1. Convert to 0 1
    vec3 p_local = (p + 1.0) / 2.0;
    p_local = p_local.zyx;
    vec3 rgb = texture(${texture_name}, p_local).rgb;
    Material mat;
    mat.albedo = rgb;
    mat.metallic = ${metallic};
    mat.roughness = ${roughness};
    return mat;
  }else{
    Material mat;
    mat.albedo = vec3(0.0);
    mat.metallic = ${metallic};
    mat.roughness = ${roughness};
    return mat;
  }
}""")

class EncodedRGBGrid3D(CustomFunctionShaderModule):
    def __init__(self, *args, **kwargs):
        template = EncodedRGBGrid3DTemplate
        name = "EncodedRGBGrid3D"
        super().__init__(template, *args, **kwargs)
        self.name = "EncodedRGBGrid3D"
        self.dependencies = ["Box3D"]
        self.bound_thresholds = []
        self.rgb_texture_names = []
        self.metallics = []
        self.roughnesses = []
    def register_hit(self, *args, **kwargs):
        rgb_texture_name = kwargs.get("rgb_texture_name", None)
        assert rgb_texture_name is not None, "Texture name is required"
        metallic = kwargs.get("metallic", None)
        assert metallic is not None, "Metallic is required"
        roughness = kwargs.get("roughness", None)
        assert roughness is not None, "Roughness is required"
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        bound_threshold = kwargs.get("bound_threshold", None)
        assert bound_threshold is not None, "Bound threshold is required"
        self.vardeps.append(rgb_texture_name)
        self.function_names.add(function_name)
        self.metallics.append(metallic)
        self.roughnesses.append(roughness)
        self.bound_thresholds.append(bound_threshold)
        self.rgb_texture_names.append(rgb_texture_name)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for ind, function_name in enumerate(self.function_names):
            code = self.template.substitute(
                texture_name=self.rgb_texture_names[ind], 
                func_name=function_name, 
                metallic=self.metallics[ind], 
                roughness=self.roughnesses[ind], 
                bound_threshold=self.bound_thresholds[ind]
            )
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code

SMMap["EncodedRGBGrid3D"] = EncodedRGBGrid3D