from ...shader_module import register_shader_module
from ..common import UNIFORMS
UNIFORMS.update({
    "iTime": {
        'type': 'float', "init_value": 0.0,
        "min": [0.0,], "max": [1.0],
    },
})

Material_v4 = register_shader_module("""
@name BaseMaterials_v4
@inputs p
@outputs color
@dependencies 
@vardeps 
// Structure for texture
// c : Color
// s : Specular
struct Material {
    vec3 albedo;
    vec3 emissive;
    vec3 mrc;
};
// saturate
float sat(float x) {

    return clamp(x, 0.0, 1.0);
}
// saturate
vec3 sat(vec3 x) {

    return clamp(x, 0.0, 1.0);
}
Material MixMaterial(Material a, Material b, float t) {

    Material mat;
    mat.albedo = mix(a.albedo, b.albedo, t);
    mat.emissive = mix(a.emissive, b.emissive, t);
    mat.mrc = mix(a.mrc, b.mrc, t);

    return mat;
}""")

MatFloor = register_shader_module("""
@name MatFloor_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Voronoi, Fbm
@vardeps 

Material MatFloor(vec3 p) {

    Material mat;

    float checker = mod(dot(ceil(p*0.2), vec3(1)), 2.0);

    vec3 v = Voronoi(p + 2.45 + Fbm(p*1.5, 4)*2.0);

    float fact = sat(pow(v.x*0.9,10.0));
    float bt = sat(pow(v.z*0.0025, 0.7));

    mat.albedo = vec3(fact);

    vec3 marble = mix(vec3(0.9,0.87,0.85), 
                vec3(0.08,0.07,0.05), abs(fact-checker));

    mat.albedo = marble;
    mat.mrc.y = v.x*0.05 + 0.05;

    return mat;
}""")



MatCarCoat = register_shader_module("""
@name MatCarCoat_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Noise
@vardeps 
Material MatCarCoat(vec3 p) {

    Material mat;

    float glitters = Noise(p*25.0);

    mat.albedo = mix(vec3(1,0,0), vec3(0.7,0,0), glitters);
    mat.mrc = vec3(1.0, glitters * 0.1 + 0.3, 1.0);
    return mat;
}

""")

MatAmbers = register_shader_module("""
@name MatAmbers_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, FbmVoronoi, Noise, Voronoi, Fbm
@vardeps iTime
Material MatAmbers(vec3 p) {

    Material mat;

    vec3 v = FbmVoronoi(p*vec3(3,2.0,2.0), 3);

    float t = pow(1.0-v.y, 2.0);
    float ef = pow(v.x, 6.0);
    float bf = Noise(p*2.0 + iTime);

    float emissive = mix(vec3(1,0.01,0),
                        vec3(0.980, 0.321, 0),
                        sat(pow(ef*pow(bf, 5.0)*4.0,0.2)));

    emissive *= pow(sat(ef*4.0),2.0)*bf*7.0;
    mat.emissive = emissive;

    float r = pow(Voronoi(p*2.0 + Fbm(p*2.0, 3)*2.0).x, 10.0);
    r += Fbm(p, 4)*0.5 + ef;

    mat.mrc.y = min(r*2.0, 1.0);
    mat.albedo = vec3((1.0-mat.mrc.y)*0.01);
    return mat;
}""")


MatWood = register_shader_module("""
@name MatWood_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, FbmVoronoi
@vardeps 
Material MatWood(vec3 p) {

    Material mat;

    p += Fbm(p*0.9, 3)*1.0;
    p.x += 1.0;

    mat.mrc.y = 0.05;
    vec3 v =  FbmVoronoi(p*vec3(2,0.02,0.0), 3);
    float t = sat(pow(v.x*2.0 ,3.0));
    vec3 a = mix(vec3(0.247, 0.105, 0.054), vec3(0.5,0.2,0.1), t);

    mat.albedo = a;
    mat.mrc.x = v.x;

    return mat;
}""")

MatBurnedWood = register_shader_module("""
@name MatBurnedWood_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, MatRotateZ, Fbm, MatWood, MatAmbers
@vardeps 
Material MatBurnedWood(vec3 p) {

    Material mat;

    p = MatRotateZ(-0.2, p);

    float fact = smoothstep(0.5, 0.55, Fbm(p*0.14, 5));

    Material wood = MatWood(p);
    Material ambers = MatAmbers(p);

    return MixMaterial(wood, ambers, fact);
}""")


MatMoss = register_shader_module("""
@name MatMoss_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Noise, Fbm
@vardeps 
Material MatMoss(vec3 p) {
    
    Material mat;

    float t = Noise(p*15.0);

    mat.albedo = mix(
                    mix(
                        vec3(0.125, 0.074, 0.015),
                        vec3(0.145, 0.105, 0.011),
                        Fbm(p*3.0, 2)*2.0),
                    mix(vec3(0.113, 0.2, 0.062),
                        vec3(0.074, 0.156, 0.023),t),
                    sat(Noise(p)*1.0)
                );
    
    mat.mrc.y = min(t*0.3 + 0.5, 1.0);
    
    return mat;
}""")

MatSoil = register_shader_module("""
@name MatSoil_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, FbmVoronoi, MatMoss_v4, Voronoi
@vardeps 
Material MatSoil(vec3 p) {

    Material mat;

    vec3 v = FbmVoronoi(p*0.2, 3);
    float stone =  max(1.0 - pow(v.y, 3.0)*3.0, 0.0 );
    stone = max(stone, Fbm(p*0.5, 4));
    stone = pow(sat(stone), 2.0)*0.7;

    Material moss = MatMoss(p);
    float t = min(pow(Voronoi(p*0.75).x + 0.2, 5.0), 1.0);
    // float fact = 
    mat.albedo = vec3(stone);
    mat.mrc.y = Fbm(p, 3);

    return MixMaterial(mat, moss, t);
}""")


MatMarble = register_shader_module("""
@name MatMarble_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, Voronoi
@vardeps 
Material MatMarble(vec3 p) {

    Material mat;

    vec3 v = Voronoi(p*0.7+ Fbm(p*1.5, 4)*2.0);
    float fact = sat(pow(v.x*1.1,5.0));
    float bt = sat(pow(v.z*0.0025, 0.7));


    mat.albedo = mix(vec3(0.9,0.87,0.85), 
                vec3(0.17,0.15,0.1), fact);
    mat.mrc = vec3(0.0, 1.0 - v.x, 0.7);

    return mat;
}""")

MatGranite = register_shader_module("""
@name MatGranite_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm
@vardeps 
Material MatGranite(vec3 p) {

    Material mat;

    float fact = pow(sat(Fbm(p*7.0, 3)*2.5),4.0);

    mat.albedo = mix(
                    vec3(0.019, 0.023, 0.015),

                    mix(vec3(0.596, 0.560, 0.580),
                        vec3(0.141, 0.137, 0.141),
                        smoothstep(0.0, 0.7, Fbm(p*7.0,3))),
                    fact);
    mat.mrc.yz = vec2(min(fact + 0.2, 1.0), 1.0);

    return mat;
}""")

MatLava = register_shader_module("""
@name MatLava_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, FbmVoronoi
@vardeps iTime
Material MatLava(vec3 p) {

    Material mat;
    float fact = pow(FbmVoronoi(p*0.5 + vec3(0,0,iTime*0.2), 3).x*1.2, 3.0);
    vec3 em = mix(vec3(1,0.01,0), vec3(1,0.3,0.1), fact);
    float solid = smoothstep(0.0, 0.5, fact);

    mat.emissive = em*solid*20.0;

    mat.mrc.y = sat(solid*2.0 + 0.8) ;

    return mat;
}""")

MatRust = register_shader_module("""
@name MatRust_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, Noise
@vardeps 
Material MatRust(vec3 p) {

    Material mat;

    float var = min(Noise(p*20.0)*0.3 + 0.3 + Fbm(p, 3)*0.5, 1.0);

    mat.albedo = vec3(0.129, 0.023, 0.007)*var;
    mat.mrc.y = var;

    return mat;
}
""")

MatRustedMetal = register_shader_module("""
@name MatRustedMetal_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, MatRust_v4
@vardeps 
Material MatRustedMetal(vec3 p) {

    Material mat;

    float var = Fbm(p,4);

    mat.albedo = vec3(var*0.1 + 0.2);
    mat.mrc.xy = vec2(1.0, var*0.2+0.1);

    Material rust = MatRust(p);

    float fact = sat(Fbm(vec3(p.xy*2.0, 0), 3) - p.z*0.2 + 0.3);

    return MixMaterial(rust, mat, fact);
}""")

MatBricks = register_shader_module("""
@name MatBricks_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, Hash3
@vardeps 
Material MatBricks(vec3 p) {

    Material mat;

    float var = Fbm(p*2.0, 4)*2.0;
    mat.mrc.y = var*0.3 + 0.7;
    p += var*0.07;
    p.z += 0.1;

    float fact = smoothstep(0.4, 0.6,abs(fract(p.z) - 0.5));
    p.xy = p.xy*0.4 + 0.5 + mod(ceil(p.z), 2.0)*0.5;

    vec2 xy = smoothstep(0.45, 0.55, abs(fract(p.xy) - 0.5));
    fact = max(fact, max(xy.x , xy.y));

    vec3 brick = vec3(ceil(p.z),ceil(p.xy));
    var += Hash3(brick)-0.5;

    brick = vec3(vec3(0.133, 0.015, 0.007) + var*0.04);

    mat.albedo = mix(brick, vec3(1.0,0.95,0.9), fact);

    return mat;
}""")

MatAsphalt = register_shader_module("""
@name MatAsphalt_v4     
@inputs p
@outputs color
@dependencies BaseMaterials_v4, Fbm, Voronoi
@vardeps 
Material MatAsphalt(vec3 p) {

    Material mat;
    float disp = Fbm(p*4.0,4)*0.05;

    vec3 v = Voronoi(p*12.0);
    vec3 asphalt = vec3(0.05-v.y*0.04);
    float t = smoothstep(0.27, 0.3, abs(fract((p.x+p.y)*0.35) - 0.5 + disp));

    t *= max((Fbm(p*0.7,4)-0.3)*2.0, 0.0);

    mat.albedo = mix(asphalt,
                    vec3(0.6,0.2,0), t);

    mat.mrc.y = min(mix(v.x*5.0 + 0.5, 0.5, t), 1.0);

    return mat;
}""")

MatGold = register_shader_module("""
@name MatGold_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4
@vardeps 
Material MatGold(vec3 p) {

    Material mat;
    mat.mrc.xy = vec2(1.0, 0.0);
    mat.albedo = vec3(1, 0.317, 0.039);
    return mat;
}""")


MatRustyPaint = register_shader_module("""
@name MatRustyPaint_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4, MatRotationX, Fbm, VoronoiE, MatRust_v4
@vardeps 
Material MatRustyPaint(vec3 p) {

    Material mat;
    p.z += 5.0;

    float fact = 1.0 - smoothstep(0.25, 0.45, Fbm(p*0.5, 4));
    float paint = 1.0;
    vec3 pp = p;
    mat3 R = MatRotationX(0.37);
    float a = 0.5;

    for (int i = 0; i < 3; ++i, pp*=2.0) {
        pp = R*pp;
        paint -= a*VoronoiE(pp).x;
    }

    paint = sat(pow(paint*2.0-0.8, 4.0));

    // overlay blending
    if (fact  < 0.5)
        fact = 2.0*fact*paint;
    else
        fact = 1.0 - 2.0*(1.0-fact)*(1.0-paint);
    
    float var = Fbm(p, 4);
    mat.albedo = vec3(0.074, 0.117, 0.203)*(var*0.3 + 0.5);
    mat.mrc.y = 0.3 + var*0.3;

    return MixMaterial(mat, MatRust(p), fact);
}""")


MatPlastic = register_shader_module("""
@name MatPlastic_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4
@vardeps 
Material MatPlastic(vec3 p) {

    Material mat;
    mat.albedo = vec3(1);
    mat.mrc.xy = vec2(0.0, 0.2);
    return mat;
}""")




MatCarbonFiber = register_shader_module("""
@name MatCarbonFiber_v4
@inputs p
@outputs color
@dependencies BaseMaterials_v4
@vardeps 
// THIS IS NOT SUPPORTED YET AS IT REQUIRES Normal as Input
Material PlanarCarbonFiber(vec2 p) {

    Material mat;

    float offset = ceil(p.x*10.0)*0.3;
    float stride = fract((p.y*2.0)+offset);

    mat.albedo = vec3(ceil(stride-0.5)*0.01);
    mat.mrc.yz = vec2(max(1.0-stride*0.7 + 0.1, 0.0), 1.0);

    return mat;
}
Material MatCarbonFiber(vec3 p, vec3 n) {

    // triplanar projection
    Material result = 
        MixMaterial(MixMaterial(PlanarCarbonFiber(p.xz),
                                PlanarCarbonFiber(p.yz),
                                pow(abs(n.x),5.0)),
                    PlanarCarbonFiber(p.xy),
                    pow(abs(n.z),5.0));
    
    return result;
}
""")