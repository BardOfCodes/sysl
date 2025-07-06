from ..shader_module import register_shader_module, ShaderModule, SMMap
from string import Template


ToneID_to_ToneMapping = {
    0: "Gamma",
    1: "Filmic",
    2: "Reinhard",
    3: "FilmicReinhard",
    4: "Uncharted2", 
    5: "ACESFitted",
}

tone_map_template = Template("""
vec3 ToneMapping(vec3 color) {
    color = color*0.2;
    color = ${ColorFunc}(color);
    color = clamp(LinearToSRGB(color), 0.0, 1.0);
    return color;
}""")

class ToneMapping(ShaderModule):
    def __init__(self):
        name = "ToneMapping"
        code = ""
        dependencies = ["ToneMappingBase"]
        vardeps = []
        inputs = ["color"]
        outputs = ["color"]
        properties = {}
        super().__init__(name, code, dependencies, vardeps, inputs, outputs, **properties)
    
    def set_config(self, *args, **kwargs):
        constants = kwargs.get("constants", {})
        tone_mapping_mode = constants.get("TONEMAP_MODE", 5)
        toning_mode = ToneID_to_ToneMapping[tone_mapping_mode]
        self.dependencies.append(toning_mode)
        self.code = tone_map_template.substitute(ColorFunc=toning_mode)

def ToneMappingFactory():
    return ToneMapping()

SMMap["ToneMapping"] = ToneMappingFactory

Gamma = register_shader_module("""
@name Gamma
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 Gamma(vec3 color) 
{
    return pow(color, vec3(0.4545));
}
""")

Uncharted2 = register_shader_module("""
@name Uncharted2
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 Uncharted2Curve(vec3 x)
{
    float A = 0.15;
    float B = 0.50;
    float C = 0.10;
    float D = 0.20;
    float E = 0.02;
    float F = 0.30;

    return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F;
}

vec3 Uncharted2(vec3 color)
{
    vec3 white_scale = Uncharted2Curve(vec3(W));
    return Uncharted2Curve(color) / white_scale;
}""")

Reinhard = register_shader_module("""
@name Reinhard
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 ReinhardCurve (vec3 x)
{
	return x / (1.0 + x);
}

vec3 Reinhard(vec3 color) 
{
    vec3 white_scale = ReinhardCurve(vec3(W));
    return ReinhardCurve(color) / white_scale;
}""")

FilmicReinhard = register_shader_module("""
@name FilmicReinhard
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 FilmicReinhardCurve (vec3 x) 
{
    const float T = 0.01;
    vec3 q = (T + 1.0)*x*x;
	return q / (q + x + T);
}

vec3 FilmicReinhard(vec3 color) 
{
    vec3 white_scale = FilmicReinhardCurve(vec3(W));
    return FilmicReinhardCurve(color) / white_scale;
}""")

Filmic = register_shader_module("""
@name Filmic
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 FilmicCurve(vec3 x)
{
	return ((x*(0.22*x+0.1*0.3)+0.2*0.01)/(x*(0.22*x+0.3)+0.2*0.3))-0.01/0.3;
}

vec3 Filmic(vec3 color)
{
    vec3 white_scale = FilmicCurve(vec3(W));
    return FilmicCurve(color) / white_scale;
}""")

ACESFitted = register_shader_module("""
@name ACESFitted
@inputs color
@outputs color
@dependencies 
@vardeps 
vec3 ACESFitted(vec3 color) {

    color = pow(color, vec3(0.833));
    color *= 1.07;

    const mat3 ACESInput = mat3(
        0.59719, 0.35458, 0.04823,
        0.07600, 0.90834, 0.01566,
        0.02840, 0.13383, 0.83777
    );

    const mat3 ACESOutput = mat3(
        1.60475, -0.53108, -0.07367,
        -0.10208,  1.10813, -0.00605,
        -0.00327, -0.07276,  1.07602
    );


    color = color * ACESInput;

    // Apply RRT and ODT
    vec3 a = color * (color + 0.0245786) - 0.000090537;
    vec3 b = color * (0.983729 * color + 0.4329510) + 0.38081;
    color = a/b;

    return color * ACESOutput;
}""")

ToneMappingBase = register_shader_module("""
@name ToneMappingBase
@inputs color
@outputs color
@dependencies 
@vardeps 

const float W =11.2; // white scale

// filmic (John Hable)

// Where is this even used?
const float A = 0.22; // shoulder strength
const float B = 0.3; // linear strength
const float C = 0.1; // linear angle
const float D = 0.20; // toe strength
const float E = 0.01; // toe numerator
const float F = 0.30; // toe denominator

vec3 LinearToSRGB(vec3 x) 
{
    vec3 t = step(x,vec3(0.0031308));
    return mix(1.055*pow(x, vec3(1./2.4)) - 0.055, 12.92*x, t);
}
""")
