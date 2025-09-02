


// Constants
const vec3 _lambda = vec3(6.8e-07, 5.5e-07, 4.5e-07);
const float _turbidity = 10.0;
const int _RAYCAST_MAX_STEPS = 70;
const vec3 _K = vec3(0.686, 0.678, 0.666);
const float _EE = 1000.0;
const float _reileighCoefficient = 2.0;
const vec3 _SCENE_BOX_CENTER = vec3(0.0, 0.5, 0.0);
const float _AS_pn = 0.035;
const float _mieCoefficient = 0.005;
const float _V = 4.0;
const float _steepness = 1.5;
const float _mieDirectionalG = 0.75;
const float _FOCAL_LENGTH = 2.5;
const float _AO_MAX_DIST = 3.0;
const float _rayleighZenithLength = 8400.0;
const float _cutoffAngle = 1.6110731556870734;
const float _mieZenithLength = 1250.0;
const float AngularDiameterCos = 0.9999566769464484;
const int _AA = 1;
const int _SHADOW_MAX_STEPS = 64;
const float _SCENE_RADIUS = 100.0;
const int _AO_STEPS = 4;
const vec3 _SCENE_BOX_SIZE = vec3(10.0, 5.0, 10.0);
const vec3 _up = vec3(0.0, 0.0, 1.0);
const float _AS_n = 1.0003;
const float PI = 3.141592653589793;
const float _AS_N = 2.545e+25;
const int _ZERO = 0;
const bool _ADD_FLOOR_PLANE = false;
const float cameraAngleX = 0.7853981633974483;
const vec3 cameraOrigin = vec3(0, 0.5, 0);
const float cameraAngleY = 0.5235987755982988;
const float cameraDistance = 5.0;
const vec2 resolution = vec2(512, 512);

// Module: Sphere3D
float Sphere3D( vec3 p, float s )
{
  return length(p)-s;
}

// Module: MatSolidV3
vec2 MatSolidV3( float sdf, float mat )
{
  return vec2(sdf, mat);
}
vec2 MatSolidV3( vec2 res, float mat )
{
  return vec2(res.x, mat);
}

// Module: Translate3D
vec3 Translate3D( vec3 p, vec3 translation )
{
    return p - translation;
}

// Module: SmoothUnion

vec2 SmoothUnion( vec2 res1, vec2 res2, float k )
{
    float h = clamp( 0.5 + 0.5*(res2.x - res1.x)/k, 0.0, 1.0 );
    return mix( res2, res1, h ) - k*h*(1.0-h);
}


// Module: BaseMaterials
struct Material {
    vec3 albedo;
    vec3 emissive;
    float roughness;
    float clearcoat;
    float metallic;
};
float sat(float x) {
    return clamp(x, 0.0, 1.0);
}
vec3 sat(vec3 x) {
    return clamp(x, 0.0, 1.0);
}
Material MixMaterial(Material a, Material b, float t) {
    Material mat;
    mat.albedo = mix(a.albedo, b.albedo, t);
    mat.roughness = mix(a.roughness, b.roughness, t);
    mat.emissive = mix(a.emissive, b.emissive, t);
    mat.clearcoat = mix(a.clearcoat, b.clearcoat, t);
    mat.metallic = mix(a.metallic, b.metallic, t);
    return mat;
}

// Module: setCamera_v1
mat3 setCamera( in vec3 ro, in vec3 ta, float cr )
{
	vec3 cw = normalize(ta-ro);
	vec3 cp = vec3(sin(cr), cos(cr),0.0);
	vec3 cu = normalize( cross(cw,cp) );
	vec3 cv =          ( cross(cu,cw) );
    return mat3( cu, cv, cw );
}

// Module: ToneMappingBase
const float W =11.2; // white scale
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

// Module: ACESFitted
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
    vec3 a = color * (color + 0.0245786) - 0.000090537;
    vec3 b = color * (0.983729 * color + 0.4329510) + 0.38081;
    color = a/b;
    return color * ACESOutput;
}

// Module: SCENE_EXPRESSION

vec2 SCENE_EXPRESSION(vec3 pos_0) {
    float sdf_0 = Sphere3D(pos_0, 0.500000000000000);
float mat_0 = 0.0;
vec2 res_1 = MatSolidV3(sdf_0, mat_0);
vec3 pos_1 = Translate3D(pos_0, vec3(0.0, 0.5, 0.0));
float sdf_2 = Sphere3D(pos_1, 0.500000000000000);
float mat_1 = 1.0;
vec2 res_3 = MatSolidV3(sdf_2, mat_1);
vec2 sdf_4 = SmoothUnion(res_1, res_3, 0.0);
return sdf_4;
}

// Module: mat_0_func

Material mat_0_func(vec3 pos_0, vec3 n_0) {
    
    Material mat_0;
    mat_0.albedo = vec3(0.0, 1.0, 0.0);
    mat_0.roughness = 1.00000000000000;
    mat_0.clearcoat = 1.00000000000000;
    mat_0.metallic = 0.300000000000000;
return mat_0;
}

// Module: mat_1_func

Material mat_1_func(vec3 pos_0, vec3 n_0) {
    
    Material mat_0;
    mat_0.albedo = vec3(0.0, 0.0, 1.0);
    mat_0.roughness = 1.00000000000000;
    mat_0.clearcoat = 1.00000000000000;
    mat_0.metallic = 0.300000000000000;
return mat_0;
}

// Module: MatPlastic
Material MatPlastic(vec3 p, vec3 n) {
    Material mat;
    mat.albedo = vec3(1);
    mat.metallic = 0.0;
    mat.roughness = 0.2;
    return mat;
}

// Module: ToneMapping

vec3 ToneMapping(vec3 color) {
    color = color*0.2;
    color = ACESFitted(color);
    color = clamp(LinearToSRGB(color), 0.0, 1.0);
    return color;
}

// Module: LightPackage
#define SPECULAR_GGX 0
#define SPECULAR_BLINN 1
#define SPECULAR_BECKMANN 2
#define SPECULAR_MODE SPECULAR_GGX
struct DirectionalLight {
    vec3 direction;
    vec3 color;
    float energy;
    float shadow_dist;
};
vec3 totalRayleigh()
{
    return (8.0 * pow(PI, 3.0) * pow(pow(_AS_n, 2.0) - 1.0, 2.0) * (6.0 + 3.0 * _AS_pn)) / (3.0 * _AS_N * pow(_lambda, vec3(4.0)) * (6.0 - 7.0 * _AS_pn));
}
float rayleighPhase(float cosTheta)
{
    return (3.0 / (16.0*PI)) * (1.0 + pow(cosTheta, 2.0));
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
    vec3 betaR = totalRayleigh() * reileigh;
    vec3 betaM = totalMie() * _mieCoefficient;
    float zenithAngle = acos(max(0.0, dot(_up, worldNormal)));
    float sR = _rayleighZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
    float sM = _mieZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
    Fex = exp(-(betaR * sR + betaM * sM));
    cosTheta = dot(worldNormal, lightDirection);
    float rPhase = rayleighPhase(cosTheta*0.5+0.5);
    vec3 betaRTheta = betaR * rPhase;
    float mPhase = hgPhase(cosTheta, _mieDirectionalG);
    vec3 betaMTheta = betaM * mPhase;
    Lin = pow(lightEnergy * ((betaRTheta + betaMTheta) / (betaR + betaM)) * (1.0 - Fex),vec3(1.5));
    Lin *= mix(vec3(1.0),pow(lightEnergy * ((betaRTheta + betaMTheta) / (betaR + betaM)) * Fex,vec3(1.0/2.0)),clamp(pow(1.0-dot(_up, lightDirection),5.0),0.0,1.0));
}
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
    vec3 betaR = totalRayleigh() * reileigh;
    vec3 betaM = totalMie() * _mieCoefficient;
    float zenithAngle = acos(max(0.0, dot(_up, light.direction)));
    float sR = _rayleighZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
    float sM = _mieZenithLength / (cos(zenithAngle) + 0.15 * pow(93.885 - ((zenithAngle * 180.0) / PI), -1.253));
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
vec3 SkyAmbient(DirectionalLight sun) {
    return Env(normalize(sun.direction*1.8 + vec3(0,0,1)), sun);
}
float phong_diffuse()
{
    return (1.0 / PI);
}
vec3 fresnel_factor(in vec3 f0, in float product)
{
    return mix(f0, vec3(1.0), pow(1.01 - product, 5.0));
}
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
float Specular(vec3 l, vec3 n, vec3 r, float k)
{
    vec3 half_dir = normalize(l + r);
    float spec_angle = max(dot(half_dir, n), 0.0);
    return pow(spec_angle, k);
}
float AmbientOcclusion(vec3 p,vec3 n) {
    const float SCALE = _AO_MAX_DIST / pow(2.0, float(_AO_STEPS))*2.0;
    float ocl = 0.0;
    for(int i = 1; i <= _AO_STEPS; ++i) {
        float dist = pow(2.0, float(i)) * SCALE;
        ocl += 1.0 - (max(0.0, SCENE_EXPRESSION(p + n * dist).x) / dist);
    }
    return min(1.0-(ocl / float(_AO_STEPS)),1.0);
}
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
vec3 Shade(DirectionalLight sun, Material mat, vec3 p, vec3 rd, vec3 n, 
    vec3 reflection, vec3 clearcoat) 
{
    vec3 ambient = SkyAmbient(sun) * 0.7;
    ambient *= AmbientOcclusion(p, n);
    vec3 specular = mix(vec3(0.02), mat.albedo, mat.metallic);
    vec3 L = sun.direction;
    vec3 N = n;
    vec3 _V = -rd;
    vec3 H = normalize(_V+L);
    float NdL = max(0.000, dot(N, L));
    float NdV = max(0.001, dot(N, _V));
    float NdH = max(0.001, dot(N, H));
    float HdV = max(0.001, dot(H, _V));
    vec3 specfresnel = fresnel_factor(specular, HdV);
    vec3 specref = cooktorrance_specular(NdL, NdV, NdH, specfresnel, mat.roughness);
    specref *= vec3(NdL);
    vec3 diffref = (vec3(1.0) - specfresnel) * phong_diffuse() * NdL;
    float s = Shadow(p+n*0.1, L, sun.shadow_dist, 20.0);
    vec3 reflected_light = vec3(0);
    vec3 diffuse_light = vec3(0);
    vec3 light_color = sun.color * sun.energy * 0.01;
    reflected_light += specref * light_color * s;
    diffuse_light += diffref * light_color * s;
    reflected_light += min(vec3(0.99), fresnel_factor(specular, NdV)) * reflection;
    reflected_light += min(vec3(0.99), fresnel_factor(vec3(0.02), NdV)) * clearcoat * 0.2;
    diffuse_light += ambient * (1.0 / PI);
    vec3 result = diffuse_light * mix(mat.albedo, vec3(0.0), mat.metallic);
    result += reflected_light;
    result += mat.emissive;
    return result;
}

// Module: SphereTraceV2
vec2 SphereTrace(in vec3 ro, in vec3 rd, float e, out bool _h,out int _s){
    vec2 res = vec2(-1.0,-1.0);
    float b = dot(ro, ro) - _SCENE_RADIUS*_SCENE_RADIUS;
    float c = dot(ro, rd);
    float disc = c*c - b;
    if (disc <= 0.0) {
        _h = false;
        _s = 0;
        return res;
    }
    float s   = sqrt(disc);
    float t0  = -c - s;
    float t1  = -c + s;
    if (t1 < 0.0) {
        _h = false;
        _s = 0;
        return res;
    }                   // both intersections behind camera
    float tmin = max(1.0, t0);
    float tmax = min(20.0, t1);
    if (_ADD_FLOOR_PLANE) {
        float tp = -ro.y / rd.y;
        if (tp > 0.0 && tp < tmax) {
            tmax = tp;
            res = vec2(tp, 1.0);
            _h = true;
            _s = 0;
        }
    }
    vec3 inv_rd = 1.0 / rd;  // hoist reciprocal
    vec3 tA = ( _SCENE_BOX_CENTER - _SCENE_BOX_SIZE - ro ) * inv_rd;
    vec3 tB = ( _SCENE_BOX_CENTER + _SCENE_BOX_SIZE - ro ) * inv_rd;
    vec3 tMin3 = min(tA, tB);
    vec3 tMax3 = max(tA, tB);
    float tbmin = max( max(tMin3.x, tMin3.y), tMin3.z );
    float tbmax = min( min(tMax3.x, tMax3.y), tMax3.z );
    if (tbmin < tbmax && tbmax > 0.0 && tbmin < tmax) {
        tmin = max(tmin, tbmin);
        tmax = min(tmax, tbmax);
        float t = tmin;
        for (int i = _ZERO; i < _RAYCAST_MAX_STEPS && t < tmax; i++) {
            vec2 h = SCENE_EXPRESSION(ro + rd * t);
            if (abs(h.x) < 0.0001 * t) {
                res = vec2(t, h.y);
                _h = true;
                _s = i;
                break;
            }
            t += h.x;
        }
    }
    return res;
}

// Module: SCENE_NORMAL
vec3 SCENE_NORMAL(in vec3 p )
{
  float eps = 0.001;
  vec3 n;
  float v = SCENE_EXPRESSION(p).x;
  n.x = SCENE_EXPRESSION( vec3(p.x+eps, p.y, p.z) ).x - v;
  n.y = SCENE_EXPRESSION( vec3(p.x, p.y+eps, p.z) ).x - v;
  n.z = SCENE_EXPRESSION( vec3(p.x, p.y, p.z+eps) ).x - v;
  return normalize(n);
}

// Module: SCENE_MATERIAL

Material SCENE_MATERIAL(in vec3 p, in vec3 n, in float y)
{
    int index = int(y);
    switch (index) {
        case 0: return mat_0_func(p, n);
case 1: return mat_1_func(p, n);
        default: return MatPlastic(p, n);
    }
}


// Module: BasicSun
DirectionalLight BasicSun()
{
    DirectionalLight sun;
    sun.direction = normalize(vec3(1,0.5,0.7));
    sun.color = SkyExtinxtion(sun)* 19.0;
    sun.energy = sunIntensity(sun.direction.z) * _EE;
    sun.shadow_dist = 100.0;
    return sun;
}

// Module: background
vec3 background(vec3 r, DirectionalLight sun)
{
    return Sky(sun, r);
}

// Module: ShadeRay
vec3 ShadeRay(DirectionalLight sun, vec3 ro, vec3 rd, out int steps) {
    bool hit = false;
    int s = 0;
    vec2 res = SphereTrace(ro, rd, 100.0, hit, s);
    float t = res.x;
    steps += s;
    vec3 pt = ro + t * rd;
    if (!hit)
        return background(rd, sun);
    vec3 n = SCENE_NORMAL(pt);
    Material mat = SCENE_MATERIAL(pt, n, res.y);
    vec3 reflect_dir = reflect(rd, n);
    vec3 clearcoat = vec3(0);
    vec3 reflection;
    if (mat.clearcoat > 0.0 || mat.roughness == 0.0) {
        s = 0;
        res = SphereTrace(pt+n*0.01, reflect_dir, 100.0, hit, s);
        t = res.x;
        steps += s;
        if (hit) {
            vec3 rpt = pt + t * reflect_dir;
            vec3 rn = SCENE_NORMAL(rpt);
            Material rmat = SCENE_MATERIAL(rpt, rn, res.y);
            vec3 sec_reflection = Env(reflect(reflect_dir, rn), sun);
            clearcoat = Shade(sun, rmat, rpt, reflect_dir, rn, 
                            sec_reflection, sec_reflection*mat.clearcoat);
        } else
            clearcoat = Env(reflect_dir, sun);
    }
    if (mat.roughness == 0.0)
        reflection = clearcoat;
    else {
        float r = 1.0/max(mat.roughness, 0.00001);
        float v = Shadow(pt+n*0.1, reflect_dir, 1000.0, r);
        reflection = mix(SkyAmbient(sun)*0.1, Env(reflect_dir, sun), v);
    }
    clearcoat *= mat.clearcoat;
    return Shade(sun, mat, pt, rd, n, reflection, clearcoat);
}

// Module: mainImage_v3
void mainImage(out vec4 color, in vec2 pxy )
{
    vec2 mo = vec2(0.0, 0.0);
    vec3 ta = vec3( 0.0, 1.0, -0.0 ) + cameraOrigin;
    vec3 ro = ta + cameraDistance * vec3(
        cos(cameraAngleX) * sin(cameraAngleY), // X component
        sin(cameraAngleX),                     // Y component (elevation)
        cos(cameraAngleX) * cos(cameraAngleY)  // Z component
    );
    mat3 ca = setCamera( ro, ta, 0.0 );
    vec3 tot = vec3(0.0);
    DirectionalLight sun = BasicSun();
    int s = 0;
    for( int m=_ZERO; m<_AA; m++ )
    for( int n=_ZERO; n<_AA; n++ )
    {
        vec2 o = vec2(float(m),float(n)) / float(_AA) - 0.5;
        vec2 p = (2.0*(pxy+o)-resolution.xy)/resolution.xy;
        vec3 rd = ca * normalize( vec3(p, _FOCAL_LENGTH) );
        vec3 rgb = ShadeRay(sun, ro, rd, s);
        rgb = ToneMapping(rgb);
        tot += rgb;
    }
    tot /= float(_AA*_AA);
    color = vec4( tot, 1.0 );
}
