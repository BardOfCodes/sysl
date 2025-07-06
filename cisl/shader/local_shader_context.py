from string import Template
from .shader_module import ShaderModule
from typing import List, Tuple

CODEBOOK_TEMPLATE = Template("""
${out_type} ${func_name}(${in_args}) {
    ${codebook}
}""")
SCENE_EXPR_PROPS = {
    "in_args": "vec3 pos_0",
}
MATERIAL_EXPR_PROPS = {
    "in_args": "vec3 pos_0, vec3 n_0",
    "out_type": "Material",
}

mat_master_template = Template("""
Material SCENE_MATERIAL(in vec3 p, in vec3 n, in float y)
{
    int index = int(y);
    switch (index) {
        ${mat_switch_cases}
        default: return MatPlastic(p, n);
    }
}
""")


class LocalShaderContext(ShaderModule):
    
    def __init__(self, name, scene_expr_props, dependencies=None, vardeps=None,
                inputs="p", outputs="res",  
                **properties):
        self.name = name
        self.local_sc = []
        self.dependencies = dependencies or []
        self.vardeps = vardeps or []  # Variable dependencies
        self.inputs = inputs
        self.outputs = outputs
        self.scene_expr_props = scene_expr_props
        self.properties = properties
        self.hit_count = 0
        self.pos_stack = ['pos_0']
        self.pos_count = 0
        self.res_sdf_stack: List[Tuple[str, str]] = []
        self.res_sdf_count = 0
        self.tracked_variables = []

    def emit_code(self):
        # Convert into a function from the codebook.
        assert 'out_type' in self.scene_expr_props, "Expected out_type in the codebook - resolve_code must be called first"
        out_type = self.scene_expr_props['out_type']
        func_name = self.name
        in_args = self.scene_expr_props['in_args']
        codebook = "\n".join(self.local_sc)
        code = CODEBOOK_TEMPLATE.substitute(
            out_type=out_type, 
            func_name=func_name, 
            in_args=in_args, 
            codebook=codebook)
        return code
    
    def add_codeline(self, code):
        self.local_sc.append(code)
    
    def add_dependency(self, dependency):
        self.dependencies.append(dependency)
    
    def add_vardep(self, vardep):
        self.vardeps.append(vardep)
    
    
    def emit_shadermodule(self):
        code = self.emit_code()
        return ShaderModule(
            name=self.name,
            code=code,
            dependencies=self.dependencies,
            vardeps=self.vardeps,
            inputs=self.inputs,
            outputs=self.outputs,
            **self.properties
        )

    def __repr__(self):
        return f"<LocalShaderContext {self.name}>"

    def add_code(self, code):
        self.local_sc.append(code)

    def resolve_code(self):
        res_type, recent_res = self.res_sdf_stack.pop()
        assert res_type in ["vec2", "vec4", "float", "Material"], "Expected vec2, vec4 or float in the codebook"
        assert len(self.res_sdf_stack) == 0, "Expected no sdf in the codebook"
        self.scene_expr_props['out_type'] = res_type
        self.add_codeline(f"return {recent_res};")
        print("Resolved codebook")
