from ..shader_module import register_shader_module

Hash = register_shader_module("""
@name Hash
@inputs p
@outputs color
@dependencies 
@vardeps 
// Hashing function
// Returns a random number in [-1,1]
float Hash(float seed)
{
    return fract(sin(seed)*43758.5453 );
}
// Hashing function
// Returns a random number in [-1,1]
// p : Vector in space
float Hash(in vec3 p)  
{
    p  = fract( p*0.3199+0.152 );
	p *= 17.0;
    return fract( p.x*p.y*p.z*(p.x+p.y+p.z) );
}""")

Hash3 = register_shader_module("""
@name Hash3
@inputs p
@outputs color
@dependencies 
@vardeps 
float Hash3(vec3 p)
{
    return fract(sin(1e3*dot(p,vec3(1,57,-13.7)))*4375.5453);
}""")

Noise = register_shader_module("""
@name Noise
@inputs p
@outputs color
@dependencies Hash
@vardeps 
// Procedural value noise with cubic interpolation
// x : Point 
float Noise(in vec3 p)
{
    vec3 i = floor(p);
    vec3 f = fract(p);
  
    f = f*f*(3.0-2.0*f);
    // Could use quintic interpolation instead of cubic
    // f = f*f*f*(f*(f*6.0-15.0)+10.0);

    return mix(mix(mix( Hash(i+vec3(0,0,0)), 
                        Hash(i+vec3(1,0,0)),f.x),
                   mix( Hash(i+vec3(0,1,0)), 
                        Hash(i+vec3(1,1,0)),f.x),f.y),
               mix(mix( Hash(i+vec3(0,0,1)), 
                        Hash(i+vec3(1,0,1)),f.x),
                   mix( Hash(i+vec3(0,1,1)), 
                        Hash(i+vec3(1,1,1)),f.x),f.y),f.z);
}""")

Voronoi = register_shader_module("""
@name Voronoi
@inputs p
@outputs color
@dependencies Hash
@vardeps 
// Compute the distance to the Voronoi boundary
// x : Point
// Return (closest distance, second closest, cell id)
vec3 Voronoi( in vec3 x )
{
    vec3 p = floor( x );
    vec3 f = fract( x );

	float id = 0.0;
    vec2 res = vec2( 100.0 );
    for( int k=-1; k<=1; k++ )
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec3 b = vec3( float(i), float(j), float(k) );
        vec3 r = vec3( b ) - f + Hash( p + b );
        float d = dot( r, r );

        if( d < res.x )
        {
			id = dot( p+b, vec3(1.0,57.0,113.0 ) );
            res = vec2( d, res.x );			
        }
        else if( d < res.y )
        {
            res.y = d;
        }
    }

    return vec3( sqrt( res ), abs(id) );
}""")

VoronoiE = register_shader_module("""
@name VoronoiE
@inputs p
@outputs color
@dependencies  Hash
@vardeps _ST_EPSILON
// based on https://www.shadertoy.com/view/llG3zy
vec3 VoronoiE( in vec3 x )
{
    vec3 n = floor(x);
    vec3 f = fract(x);

    //----------------------------------
    // first pass: regular voronoi
    //----------------------------------
	vec3 mr;

    float md = 8.0;
    for( int k=-1; k<=1; k++ )
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec3 g = vec3(float(i),float(j), float(k));
		vec3 o = vec3( g ) - f + Hash( n + g );
        vec3 r = g + o - f;
        float d = dot(r,r);

        if( d<md )
        {
            md = d;
            mr = r;
        }
    }

    //----------------------------------
    // second pass: distance to borders,
    // visits only neighbouring cells
    //----------------------------------
    md = 8.0;
    for( int k=-1; k<=1; k++ )
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec3 g = vec3(float(i),float(j), float(k));
		vec3 o = vec3( g ) - f + Hash( n + g );
		vec3 r = g + o - f;

        if( dot(mr-r,mr-r)>_ST_EPSILON ) // skip the same cell
        md = min( md, dot( 0.5*(mr+r), normalize(r-mr) ) );
    }

    return vec3( md, mr );
}""")

Fbm = register_shader_module("""
@name Fbm
@inputs p
@outputs color
@dependencies Noise, MatRotationX
@vardeps 
// Fractal brownian motion
float Fbm(vec3 p, int octave) {

    float v = 0.,  a = .5;
    mat3 R = MatRotationX(.37);

    for (int i = 0; i < octave; ++i, p*=2.0, a/=2.0) 
        p *= R,
        v += a * Noise(p);

    return v;
}""")


FbmVoronoi = register_shader_module("""
@name FbmVoronoi
@inputs p
@outputs color
@dependencies MatRotationX, Voronoi
@vardeps 
// Voronoi fractal brownian motion
vec3 FbmVoronoi(vec3 p, int octave) {

    vec3 v = vec3(0.0);
    float a = 0.5;
    mat3 R = MatRotationX(.37);

    for (int i = 0; i < octave; ++i, p*=2.0, a/=2.0) 
        p *= R,
        v += a * Voronoi(p);

    return v;
}""")

MatRotationX = register_shader_module("""
@name MatRotationX
@inputs p
@outputs color
@dependencies 
@vardeps 
mat3 MatRotationX(float theta)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    return mat3(    1,     0,     0,
                    0,  _cos, -_sin,
                    0,  _sin,  _cos);
}""")

MatRotationY = register_shader_module("""
@name MatRotationY
@inputs p
@outputs color
@dependencies 
@vardeps 
// Create rotation matrix for theta angle around Y axis (radians)
mat3 MatRotationY(float theta)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    return mat3( _cos,     0, -_sin,
                    0,     1,     0,
                 _sin,     0,  _cos);
}""")

MatRotationZ = register_shader_module("""
@name MatRotationZ
@inputs p
@outputs color
@dependencies 
@vardeps // Create rotation matrix for theta angle around Z axis (radians)
mat3 MatRotationZ(float theta)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    return mat3(_cos, -_sin,  0,
                _sin,  _cos,  0,
                0,     0,     1);
}""")


MatRotateZ = register_shader_module("""
@name MatRotateZ
@inputs p
@outputs color
@dependencies 
@vardeps 
// Rotate point p around X axis (radians)
vec3 MatRotateX(float theta, vec3 p)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    mat3 M = mat3(  1,     0,     0,
                    0,  _cos, -_sin,
                    0,  _sin,  _cos);
    
    return M*p;
}""")    

MatRotateY = register_shader_module("""
@name MatRotateY
@inputs p
@outputs color
@dependencies 
@vardeps 
// Rotate point p around Y axis (radians)
vec3 MatRotateY(float theta, vec3 p)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    mat3 M = mat3( _cos,    0,  -_sin,
                    0,      1,      0,
                   _sin,    0,   _cos);
    
    return M*p;
}""")

MatRotateZ = register_shader_module("""
@name MatRotateZ
@inputs p
@outputs color
@dependencies 
@vardeps 
// Rotate point p around Z axis (radians)
vec3 MatRotateZ(float theta, vec3 p)
{   
    float _sin = sin(theta);
    float _cos = cos(theta);

    mat3 M = mat3(  _cos,  -_sin,   0,
                    _sin,   _cos,   0,
                    0,      0,      1);

    return M*p;
}""")    
