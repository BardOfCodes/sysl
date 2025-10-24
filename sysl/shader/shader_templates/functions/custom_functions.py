# SDFGrid3D
# Custom nodes.
import numpy as np
from ...shader_module import register_shader_module, ShaderModule, SMMap
from string import Template

LOW_PRECISION_RANGE = np.sqrt(0.5)

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
    def __init__(self, name=None,template=None, *args, **kwargs):
        if template is None:
            template = EncodedSDFGrid3DTemplate
        if name is None:
            name = "EncodedSDFGrid3D"

        super().__init__(name, template, *args, **kwargs)
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


SMMap["EncodedSDFGrid3D"] = EncodedSDFGrid3D

EncodedLowPrecisionSDFGrid3DTemplate = Template("""
float ${func_name}( vec3 p )
{
  float box_sdf = Box3D(p, vec3(1.0));
  if (box_sdf < ${bound_threshold}) {
    // p is in -1 to 1. Convert to 0–1 and flip to ZYX layout
    vec3 p_local = (p + 1.0) / 2.0;
    p_local = p_local.zyx;

    // vec2 rg = texture(${texture_name}, p_local).rg;
    // float coarse_bin = floor(rg.r * 255.0);
    // float fine_bin   = floor(rg.g * 255.0);

    float r = texture(${texture_name}, p_local).r;
    float sdf = r * (2.0 * ${low_precision_range}) - ${low_precision_range};  // maps to [-√3, √3]

    // float bin_size = (2.0 * ${low_precision_range}) / 256.0;
    // float sdf = coarse_bin * bin_size + (fine_bin / 256.0) * bin_size - ${low_precision_range};
    // float sdf = coarse_bin * bin_size; // + (fine_bin / 256.0) * bin_size - ${low_precision_range};
    return sdf;
  } else {
    return box_sdf;
  }
}
""")

class EncodedLowPrecisionSDFGrid3D(EncodedSDFGrid3D):
    def __init__(self, *args, **kwargs):
        template = EncodedLowPrecisionSDFGrid3DTemplate
        name = "EncodedLowPrecisionSDFGrid3D"
        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["Box3D"]
        self.bound_thresholds = []
        self.sdf_texture_names = []
        self.template = EncodedLowPrecisionSDFGrid3DTemplate

    def generate_code(self):
        code_parts = []
        for ind, function_name in enumerate(self.function_names):
            code = self.template.substitute(texture_name=self.sdf_texture_names[ind], func_name=function_name, 
                                            bound_threshold=self.bound_thresholds[ind], low_precision_range=LOW_PRECISION_RANGE)
            code_parts.append(code)
        self.code = "\n".join(code_parts)

SMMap["EncodedLowPrecisionSDFGrid3D"] = EncodedLowPrecisionSDFGrid3D

#  Custom material function. 

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

class EncodedRGBGrid3D(EncodedSDFGrid3D):
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


SMMap["EncodedRGBGrid3D"] = EncodedRGBGrid3D


AABBEncodedSDFGrid3DTemplate = Template("""
float ${func_name}( vec3 p )
{
  vec3 local_p = p - ${bbox_origin};
  float box_sdf = Box3D(local_p, ${bbox_scale});
  if (box_sdf < ${bound_threshold}) {
    // Scale by the required scale on each axis.
    local_p = local_p / ${bbox_scale};
    // p is in -1 to 1. Convert to 0 1
    local_p = (local_p + 1.0) / 2.0;
    local_p = local_p.zyx;
    float sdf = texture(${texture_name}, local_p).r;
    return sdf;
  }else{
    return box_sdf;
  }
}""")

class AABBEncodedSDFGrid3D(CustomFunctionShaderModule):
    def __init__(self, name=None,template=None, *args, **kwargs):
        if template is None:
            template = AABBEncodedSDFGrid3DTemplate
        if name is None:
            name = "AABBEncodedSDFGrid3D"

        super().__init__(name, template, *args, **kwargs)
        self.dependencies = ["Box3D",]
        self.bound_thresholds = []
        self.sdf_texture_names = []
        self.bbox_origins = []
        self.bbox_scales = []
    def register_hit(self, *args, **kwargs):
        sdf_texture_name = kwargs.get("sdf_texture_name", None)
        assert sdf_texture_name is not None, "Texture name is required"
        function_name = kwargs.get("function_name", None)
        assert function_name is not None, "Function name is required"
        bound_threshold = kwargs.get("bound_threshold", None)
        assert bound_threshold is not None, "Bound threshold is required"
        bbox_origin = kwargs.get("bbox_origin", None)
        assert bbox_origin is not None, "Bbox origin is required"
        bbox_scale = kwargs.get("bbox_scale", None)
        assert bbox_scale is not None, "Bbox scale is required"
        self.vardeps.append(sdf_texture_name)
        self.function_names.add(function_name)
        self.bound_thresholds.append(bound_threshold)
        self.sdf_texture_names.append(sdf_texture_name)
        self.bbox_origins.append(bbox_origin)
        self.bbox_scales.append(bbox_scale)
        self.hit_count += 1

    def generate_code(self):
        code_parts = []
        for ind, function_name in enumerate(self.function_names):
            code = self.template.substitute(texture_name=self.sdf_texture_names[ind], func_name=function_name, 
                                            bound_threshold=self.bound_thresholds[ind], 
                                            bbox_origin=self.bbox_origins[ind], 
                                            bbox_scale=self.bbox_scales[ind])
            code_parts.append(code)
        self.code = "\n".join(code_parts)

    def emit_code(self):
        if self.code is None:
            self.generate_code()
        return self.code


SMMap["AABBEncodedSDFGrid3D"] = AABBEncodedSDFGrid3D
