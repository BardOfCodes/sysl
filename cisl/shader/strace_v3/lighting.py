from ..shader_module import register_shader_module, SMMap
from ..strace_v1 import CONSTANTS
import numpy as np

CONSTANTS.update({
    "_AO_STEPS": ("int", 4),
    "_AO_MAX_DIST": ("float", 3.0),
    "_turbidity": ("float", 10.0),
    "_reileighCoefficient": ("float", 2.0),
    "_mieCoefficient": ("float", 0.005),
    "_mieDirectionalG": ("float", 0.75),
    "_AS_n": ("float", 1.0003),
    "_AS_N": ("float", 2.545E25),
    "_AS_pn": ("float", 0.035),
    "_lambda": ("vec3", (680E-9, 550E-9, 450E-9)),
    "_K": ("vec3", (0.686, 0.678, 0.666)),
    "_V": ("float", 4.0),
    "_rayleighZenithLength": ("float", 8.4E3),
    "_mieZenithLength": ("float", 1.25E3),
    "_up": ("vec3", (0.0, 0.0, 1.0)),
    "_EE": ("float", 1000.0),
    "_cutoffAngle": ("float", np.pi/1.95),
    "_steepness": ("float", 1.5),
    "PI": ("float", np.pi),
    "AngularDiameterCos": ("float", 0.999956676946448443553574619906976478926848692873900859324),
})


LightPackage = register_shader_module("""
@name LightPackage
@inputs sun, sky
@outputs color
@dependencies SCENE_EXPRESSION
@vardeps _AO_STEPS, _AO_MAX_DIST, _SHADOW_MAX_STEPS, PI, _AS_n, _AS_N, _AS_pn, 
@vardeps _lambda, _K, _V, _rayleighZenithLength, _mieZenithLength, _up, _EE, 
@vardeps _cutoffAngle, _steepness, _turbidity, _reileighCoefficient
@vardeps _mieCoefficient, _mieDirectionalG, AngularDiameterCos

#define SPECULAR_GGX 0
#define SPECULAR_BLINN 1
#define SPECULAR_BECKMANN 2
#define SPECULAR_MODE SPECULAR_GGX
// Lighting ----------------------------------------------------------------------------------------------

struct DirectionalLight {
    vec3 direction;
    vec3 color;
    float energy;
    float shadow_dist;
};

// Sky --------------------------------------------------------------------------------

// Atmospheric scattering based on preetham's analytical model
// https://github.com/vorg/pragmatic-pbr/blob/master/local_modules/glsl-sky/index.glsl


vec3 totalRayleigh()
{
    return (8.0 * pow(PI, 3.0) * pow(pow(_AS_n, 2.0) - 1.0, 2.0) * (6.0 + 3.0 * _AS_pn)) / (3.0 * _AS_N * pow(_lambda, vec3(4.0)) * (6.0 - 7.0 * _AS_pn));
}

float rayleighPhase(float cosTheta)
{
    return (3.0 / (16.0*PI)) * (1.0 + pow(cosTheta, 2.0));
    // return (1.0 / (3.0*PI)) * (1.0 + pow(cosTheta, 2.0));
    // return (3.0 / 4.0) * (1.0 + pow(cosTheta, 2.0));
}

vec3 totalMie()
{
    float c = (0.2 * _turbidity) * 10E-18;
    return 0.434 * c * PI * pow((2.0 * PI) / _lambda, vec3(_V - 2.0)) * _K;
}

float hgPhase(float cosTheta, float g)
{
    return (1.0 / (4.0*PI)) * ((1.0 - pow(g, 2.0)) / pow(1.0 - 2.0*g*cosTheta + pow(g, 2.0), 1.5));
}

float sunIntensity(float zenithAngleCos)
{
    return max(0.0, 1.0 - exp(-((_cutoffAngle - acos(zenithAngleCos))/_steepness)));
}



void AtmosphericScattering(DirectionalLight light, vec3 worldNormal, 
    out float cosTheta, out vec3 Lin, out vec3 Fex) 
{

    vec3 lightDirection = light.direction;
    float lightEnergy = light.energy;

    float sunfade = 1.0-clamp(1.0- exp(light.direction.z / 450000.0) ,0.0,1.0);

    float reileigh = _reileighCoefficient - (1.0-sunfade);

    // extinction (absorbtion + out scattering)
    // rayleigh coefficients
    vec3 betaR = totalRayleigh() * reileigh;

    // mie coefficients
    vec3 betaM = totalMie() * _mieCoefficient;

    // optical length
    // cutoff angle at 90 to avoid singularity in next formula.
    //float zenithAngle = acos(max(0.0, dot(_up, normalize(vWorldPosition - cameraPos))));
    float zenithAngle = acos(max(0.0, dot(_up, worldNormal)));
    float sR = _rayleighZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
    float sM = _mieZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));


    // combined extinction factor
    Fex = exp(-(betaR * sR + betaM * sM));

    // in scattering
    cosTheta = dot(worldNormal, lightDirection);

    float rPhase = rayleighPhase(cosTheta*0.5+0.5);
    vec3 betaRTheta = betaR * rPhase;

    float mPhase = hgPhase(cosTheta, _mieDirectionalG);
    vec3 betaMTheta = betaM * mPhase;


    Lin = pow(lightEnergy * ((betaRTheta + betaMTheta) / (betaR + betaM)) * (1.0 - Fex),vec3(1.5));
    Lin *= mix(vec3(1.0),pow(lightEnergy * ((betaRTheta + betaMTheta) / (betaR + betaM)) * Fex,vec3(1.0/2.0)),clamp(pow(1.0-dot(_up, lightDirection),5.0),0.0,1.0));
}


// Get sky color
vec3 Sky(DirectionalLight sun, vec3 viewDir) {

    float CosTheta;
    vec3 Lin;
    vec3 Fex;

    AtmosphericScattering(sun, viewDir, CosTheta, Lin, Fex);

    float sundisk = smoothstep(AngularDiameterCos,AngularDiameterCos+0.00002,CosTheta);
    vec3 L0 = sun.energy * 19000.0 * sundisk * Fex;

    vec3 texColor = (Lin + L0) * 0.04;
    texColor += vec3(0.0,0.001,0.0025)*0.3;

    return texColor;
}


vec3 SkyExtinxtion(DirectionalLight light) 
{

    float sunfade = 1.0-clamp(1.0-exp(light.direction.z),0.0,1.0);

    float reileigh = _reileighCoefficient - (1.0-sunfade);

    // rayleigh coefficients
    vec3 betaR = totalRayleigh() * reileigh;

    // mie coefficients
    vec3 betaM = totalMie() * _mieCoefficient;

    // sun optical length
    float zenithAngle = acos(max(0.0, dot(_up, light.direction)));
    float sR = _rayleighZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
    float sM = _mieZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));

    // combined extinction factor
    return exp(-(betaR * sR + betaM * sM));
}



vec3 Env(vec3 view, DirectionalLight sun) {

    float cosTheta;
    vec3 Lin;
    vec3 Fex;

    AtmosphericScattering(sun, view, cosTheta, Lin, Fex);

    vec3 L0 = Fex * 0.1;

    vec3 texColor = (Lin+L0) * 0.04;
    texColor += vec3(0.0,0.001,0.0025)*0.3;


    return texColor;
}

// PBR -------------------------------------------------------------------------

//https://gist.github.com/galek/53557375251e1a942dfa

// Get sky ambient color
// sunDirection : Sun direction
// worldNormal : Ray direction
vec3 SkyAmbient(DirectionalLight sun) {

    return Env(normalize(sun.direction*1.8 + vec3(0,0,1)), sun);
}


// phong (lambertian) diffuse term
float phong_diffuse()
{
    return (1.0 / PI);
}


// compute fresnel specular factor for given base specular and product
// product could be NdV or VdH depending on used technique
vec3 fresnel_factor(in vec3 f0, in float product)
{
    return mix(f0, vec3(1.0), pow(1.01 - product, 5.0));
}


// following functions are copies of UE4
// for computing cook-torrance specular lighting terms

float D_blinn(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float n = 2.0 / m2 - 2.0;
    return (n + 2.0) / (2.0 * PI) * pow(NdH, n);
}

float D_beckmann(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float NdH2 = NdH * NdH;
    return exp((NdH2 - 1.0) / (m2 * NdH2)) / (PI * m2 * NdH2 * NdH2);
}

float D_GGX(in float roughness, in float NdH)
{
    float m = roughness * roughness;
    float m2 = m * m;
    float d = (NdH * m2 - NdH) * NdH + 1.0;
    return m2 / (PI * d * d);
}

float G_schlick(in float roughness, in float NdV, in float NdL)
{
    float k = roughness * roughness * 0.5;
    float _V = NdV * (1.0 - k) + k;
    float L = NdL * (1.0 - k) + k;
    return 0.25 / (_V * L);
}


// cook-torrance specular calculation                      
vec3 cooktorrance_specular(in float NdL, in float NdV, in float NdH, in vec3 specular, in float roughness)
{
#if SPECULAR_MODE == SPECULAR_BLINN
    float D = D_blinn(roughness, NdH);
#elif SPECULAR_MODE == SPECULAR_BECKMANN
    float D = D_beckmann(roughness, NdH);
#elif SPECULAR_MODE == SPECULAR_GGX
    float D = D_GGX(roughness, NdH);
#endif

    float G = G_schlick(roughness, NdV, NdL);

    float rim = mix(1.0 - roughness * 0.9, 1.0, NdV);

    return max((1.0 / rim) * specular * G * D, 0.0);
}


// Compute Blinn-Phong specular
// l : Vector to light
// n : Normal at point
// r : View ray direction
// k : glossyness
float Specular(vec3 l, vec3 n, vec3 r, float k)
{
    vec3 half_dir = normalize(l + r);
    float spec_angle = max(dot(half_dir, n), 0.0);
    return pow(spec_angle, k);

    // Phong
//     vec3 ref = reflect(r, n);
//     float c = max(dot(ref, r), 0.0);
//     return pow(c, k/4.0);
}

// ------ Lighting Functions ------

// Compute ambient occlusion based on https://www.shadertoy.com/view/3lXyWs
// p : Point
// n : Normal at point
float AmbientOcclusion(vec3 p,vec3 n) {

    const float SCALE = _AO_MAX_DIST / pow(2.0, float(_AO_STEPS))*2.0;
    float ocl = 0.0;

    for(int i = 1; i <= _AO_STEPS; ++i) {
        float dist = pow(2.0, float(i)) * SCALE;
        ocl += 1.0 - (max(0.0, SCENE_EXPRESSION(p + n * dist).x) / dist);
    }
    
    return min(1.0-(ocl / float(_AO_STEPS)),1.0);
    // return pow(abs(SCENE_EXPRESSION(p + 2.0 * n)),0.9);
}


// Cast soft shadow based on https://www.shadertoy.com/view/tlBcDK
// p : Point
// l : Point to light vector
// d : Max tracing distance
// r : Softness radius
float Shadow(vec3 p,vec3 l, float d, float r)
{

    float res = 1.0;
    float t = 0.1;

    for (int i = 0; i < _SHADOW_MAX_STEPS; ++i) {

        if (res < 0.0 || t > d)
            break;
    
        float h = SCENE_EXPRESSION(p+t*l).x;

        res = min(res, r * h / t);
        t += h;    
    }    

    return clamp(res, 0.0, 1.0);
}

// Compute lighting
// sun : Sun data
// mat : Material data
// p : Point on surface
// rd : View ray direction
// n : Normal at Point
// reflection : Computed reflection
// clearcoat : Computed clearcoat reflection
vec3 Shade(DirectionalLight sun, Material mat, vec3 p, vec3 rd, vec3 n, 
    vec3 reflection, vec3 clearcoat) 
{

    // Ambient color
    vec3 ambient = SkyAmbient(sun) * 0.7;

    // Ambient occlusion
    ambient *= AmbientOcclusion(p, n);

    // vec3 diffuse = ambient;
    vec3 specular = mix(vec3(0.02), mat.albedo, mat.metallic);


    vec3 L = sun.direction;
    vec3 N = n;
    vec3 _V = -rd;
    vec3 H = normalize(_V+L);

    float NdL = max(0.000, dot(N, L));
    float NdV = max(0.001, dot(N, _V));
    float NdH = max(0.001, dot(N, H));
    float HdV = max(0.001, dot(H, _V));


    // specular reflectance with COOK-TORRANCE
    vec3 specfresnel = fresnel_factor(specular, HdV);
    vec3 specref = cooktorrance_specular(NdL, NdV, NdH, specfresnel, mat.roughness);

    specref *= vec3(NdL);

    // diffuse is common for any model
    vec3 diffref = (vec3(1.0) - specfresnel) * phong_diffuse() * NdL;

    // visibility
    float s = Shadow(p+n*0.1, L, sun.shadow_dist, 20.0);
    
    // compute lighting
    vec3 reflected_light = vec3(0);
    vec3 diffuse_light = vec3(0);

    // point light
    vec3 light_color = sun.color * sun.energy * 0.01;
    reflected_light += specref * light_color * s;
    diffuse_light += diffref * light_color * s;

    reflected_light += min(vec3(0.99), fresnel_factor(specular, NdV)) * reflection;
    reflected_light += min(vec3(0.99), fresnel_factor(vec3(0.02), NdV)) * clearcoat * 0.2;
    diffuse_light += ambient * (1.0 / PI);

    // final result
    vec3 result = diffuse_light * mix(mat.albedo, vec3(0.0), mat.metallic);
    result += reflected_light;
    result += mat.emissive;

    return result;
}""")

BasicSun = register_shader_module("""
@name BasicSun
@inputs sun
@outputs color
@dependencies LightPackage
@vardeps _EE
DirectionalLight BasicSun()
{
    DirectionalLight sun;
    sun.direction = normalize(vec3(1,0.5,0.7));
    sun.color = SkyExtinxtion(sun)* 19.0;
    sun.energy = sunIntensity(sun.direction.z) * _EE;
    sun.shadow_dist = 100.0;
    return sun;
}
""")
# Picture in picture

ShadeSteps = register_shader_module("""
@name ShadeSteps
@inputs n
@outputs color
@dependencies 
@vardeps 
// Shading according to the number of steps in sphere tracing
// n : Number of steps
vec3 ShadeSteps(int n)
{
   float t=float(n)/(float(MAX_STEPS-1));
   return 0.5+mix(vec3(0.05,0.05,0.5),vec3(0.65,0.39,0.65),t);
}""")

PIP = register_shader_module("""
@name Pip
@inputs pixel, pip
@outputs color
@dependencies 
@vardeps 

// Picture in picture
// pixel : Pixel
// pip : Boolean, true if pixel was in sub-picture zone
vec2 Pip(in vec2 pixel, out bool pip)
{
    // Pixel coordinates
    vec2 p = (-iResolution.xy + 2.0*pixel)/iResolution.y;
   if (pip==true)
   {    
    const float fraction=1.0/4.0;
    // Recompute pixel coordinates in sub-picture
    if ((pixel.x<iResolution.x*fraction) && (pixel.y<iResolution.y*fraction))
    {
        p=(-iResolution.xy*fraction + 2.0*pixel)/(iResolution.y*fraction);
        pip=true;
    }
       else
       {
           pip=false;
       }
   }
   return p;
}""")