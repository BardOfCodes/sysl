
from ...shader_module import register_shader_module

Sphere3D = register_shader_module("""
@name Sphere3D
@inputs pos, radius
@outputs dist
@dependencies
float Sphere3D( vec3 p, float s )
{
  return length(p)-s;
}""")


Box3D = register_shader_module("""
@name Box3D
@inputs pos, size
@outputs dist
@dependencies
float Box3D( vec3 p, vec3 b )
{
  vec3 d = abs(p) - b;
  return length(max(d,0.0)) + min(max(d.x,max(d.y,d.z)),0.0);
}""")

Cuboid3D = register_shader_module("""
@name Cuboid3D
@inputs pos, size
@outputs dist
@dependencies
float Cuboid3D( vec3 p, vec3 b )
{
  vec3 d = abs(p) - b;
  return length(max(d,0.0)) + min(max(d.x,max(d.y,d.z)),0.0);
}""")

RoundedBox3D = register_shader_module("""
@name RoundedBox3D
@inputs pos, size, radius
@outputs dist
@dependencies
float RoundedBox3D( vec3 p, vec3 b, float r )
{
  vec3 q = abs(p) - b + r;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0) - r;
}""")

BoxFrame3D = register_shader_module("""
@name BoxFrame3D
@inputs pos, size, frame_width
@outputs dist
@dependencies
float BoxFrame3D( vec3 p, vec3 b, float e )
{
       p = abs(p  )-b;
  vec3 q = abs(p+e)-e;
  return min(min(
      length(max(vec3(p.x,q.y,q.z),0.0))+min(max(p.x,max(q.y,q.z)),0.0),
      length(max(vec3(q.x,p.y,q.z),0.0))+min(max(q.x,max(p.y,q.z)),0.0)),
      length(max(vec3(q.x,q.y,p.z),0.0))+min(max(q.x,max(q.y,p.z)),0.0));
}""")

Torus3D = register_shader_module("""
@name Torus3D
@inputs pos, size, radius
@outputs dist
@dependencies
float Torus3D( vec3 p, vec2 t )
{
  vec2 q = vec2(length(p.xz)-t.x,p.y);
  return length(q)-t.y;
}""")

CappedTorus3D = register_shader_module("""
@name CappedTorus3D
@inputs pos, size, angle, ra, rb
@outputs dist
@dependencies
float CappedTorus3D( vec3 p, float angle, float ra, float rb)
{
  vec2 sc = vec2(sin(angle), cos(angle));
  p.x = abs(p.x);
  float k = (sc.y*p.x>sc.x*p.y) ? dot(p.xy,sc) : length(p.xy);
  return sqrt( dot(p,p) + ra*ra - 2.0*ra*k ) - rb;
}""")

Link3D = register_shader_module("""
@name Link3D
@inputs pos, length, radius1, radius2
@outputs dist
@dependencies
float Link3D( vec3 p, float le, float r1, float r2 )
{
  vec3 q = vec3( p.x, max(abs(p.y)-le,0.0), p.z );
  return length(vec2(length(q.xy)-r1,q.z)) - r2;
}""")

InfiniteCylinder3D = register_shader_module("""
@name InfiniteCylinder3D
@inputs pos, radius
@outputs dist
@dependencies
float InfiniteCylinder3D( vec3 p, vec3 c )
{
  return length(p.xz-c.xy)-c.z;
}""")

Cone3D = register_shader_module("""
@name Cone3D
@inputs pos, angle, height
@outputs dist
@dependencies
float Cone3D( vec3 p, float angle, float h )
{
  vec2 c = vec2(sin(angle), cos(angle));
  // c is the sin/cos of the angle, h is height
  // Alternatively pass q instead of (c,h),
  // which is the point at the base in 2D
  vec2 q = h*vec2(c.x/c.y,-1.0);
    
  vec2 w = vec2( length(p.xz), p.y );
  vec2 a = w - q*clamp( dot(w,q)/dot(q,q), 0.0, 1.0 );
  vec2 b = w - q*vec2( clamp( w.x/q.x, 0.0, 1.0 ), 1.0 );
  float k = sign( q.y );
  float d = min(dot( a, a ),dot(b, b));
  float s = max( k*(w.x*q.y-w.y*q.x),k*(w.y-q.y)  );
  return sqrt(d)*sign(s);
}""")

InexactCone3D = register_shader_module("""
@name InexactCone3D
@inputs pos, angle, height
@outputs dist
@dependencies
float InexactCone3D( vec3 p, float angle, float h )
{
  vec2 c = vec2(sin(angle), cos(angle));
  float q = length(p.xz);
  return max(dot(c.xy,vec2(q,p.y)),-h-p.y);
}""")

InfiniteCone3D = register_shader_module("""
@name InfiniteCone3D
@inputs pos, angle
@outputs dist
@dependencies
float InfiniteCone3D( vec3 p, float angle )
{
    vec2 c = vec2(sin(angle), cos(angle));
    vec2 q = vec2( length(p.xz), -p.y );
    float d = length(q-c*max(dot(q,c), 0.0));
    return d * ((q.x*c.y-q.y*c.x<0.0)?-1.0:1.0);
}""")

Plane3D = register_shader_module("""
@name Plane3D
@inputs pos, normal, height
@outputs dist
@dependencies
float Plane3D( vec3 p, vec3 n, float h )
{
  // n must be normalized
  return dot(p,n) + h;
}""")

HexPrism3D = register_shader_module("""
@name HexPrism3D
@inputs pos, height
@outputs dist
@dependencies
float HexPrism3D( vec3 p, vec2 h )
{
  const vec3 k = vec3(-0.8660254, 0.5, 0.57735);
  p = abs(p);
  p.xy -= 2.0*min(dot(k.xy, p.xy), 0.0)*k.xy;
  vec2 d = vec2(
       length(p.xy-vec2(clamp(p.x,-k.z*h.x,k.z*h.x), h.x))*sign(p.y-h.x),
       p.z-h.y );
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}""")

TriPrism3D = register_shader_module("""
@name TriPrism3D
@inputs pos, height
@outputs dist
@dependencies
float TriPrism3D( vec3 p, vec2 h )
{
  vec3 q = abs(p);
  return max(q.z-h.y,max(q.x*0.866025+p.y*0.5,-p.y)-h.x*0.5);
}""")

Capsule3D = register_shader_module("""
@name Capsule3D
@inputs pos, a, b, r
@outputs dist
@dependencies
float Capsule3D( vec3 p, vec3 a, vec3 b, float r )
{
  vec3 pa = p - a, ba = b - a;
  float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
  return length( pa - ba*h ) - r;
}""")

VerticalCapsule3D = register_shader_module("""
@name VerticalCapsule3D
@inputs pos, height, radius
@outputs dist
@dependencies
float VerticalCapsule3D( vec3 p, float h, float r )
{
  p.y -= clamp( p.y, 0.0, h );
  return length( p ) - r;
}""")

## THIS IS NOT IN GEOLIPI TORCH COMPUTE.
VerticalCappedCylinder3D = register_shader_module("""
@name VerticalCappedCylinder3D
@inputs pos, height, radius
@outputs dist
@dependencies
float VerticalCappedCylinder3D( vec3 p, float h, float r )
{
  vec2 d = abs(vec2(length(p.xz),p.y)) - vec2(r,h);
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}""")

CappedCylinder3D = register_shader_module("""
@name CappedCylinder3D
@inputs pos, height, radius
@outputs dist
@dependencies
float CappedCylinder3D( vec3 p, float h, float r )
{
  vec2 d = abs(vec2(length(p.xz),p.y)) - vec2(r,h);
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}""")

Cylinder3D = register_shader_module("""
@name Cylinder3D
@inputs pos, height, radius
@outputs dist
@dependencies
float Cylinder3D( vec3 p, float h, float r )
{
  vec2 d = abs(vec2(length(p.xz),p.y)) - vec2(r,h);
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}""")

ArbitraryCappedCylinder3D = register_shader_module("""
@name ArbitraryCappedCylinder3D
@inputs pos, a, b, radius
@outputs dist
@dependencies
float ArbitraryCappedCylinder3D( vec3 p, vec3 a, vec3 b, float r )
{
  vec3  ba = b - a;
  vec3  pa = p - a;
  float baba = dot(ba,ba);
  float paba = dot(pa,ba);
  float x = length(pa*baba-ba*paba) - r*baba;
  float y = abs(paba-baba*0.5)-baba*0.5;
  float x2 = x*x;
  float y2 = y*y*baba;
  float d = (max(x,y)<0.0)?-min(x2,y2):(((x>0.0)?x2:0.0)+((y>0.0)?y2:0.0));
  return sign(d)*sqrt(abs(d))/baba;
}""")

RoundedCylinder3D = register_shader_module("""
@name RoundedCylinder3D
@inputs pos, height, radius
@outputs dist
@dependencies
float RoundedCylinder3D( vec3 p, float ra, float rb, float h )
{
  vec2 d = vec2( length(p.xz)-2.0*ra+rb, abs(p.y) - h );
  return min(max(d.x,d.y),0.0) + length(max(d,0.0)) - rb;
}""")

CappedCone3D = register_shader_module("""
@name CappedCone3D
@inputs pos, height, radius
@outputs dist
@dependencies dot2
float CappedCone3D( vec3 p, float r1, float r2, float h)
{
  vec2 q = vec2( length(p.xz), p.y );
  vec2 k1 = vec2(r2,h);
  vec2 k2 = vec2(r2-r1,2.0*h);
  vec2 ca = vec2(q.x-min(q.x,(q.y<0.0)?r1:r2), abs(q.y)-h);
  vec2 cb = q - k1 + k2*clamp( dot(k1-q,k2)/dot2(k2), 0.0, 1.0 );
  float s = (cb.x<0.0 && ca.y<0.0) ? -1.0 : 1.0;
  return s*sqrt( min(dot2(ca),dot2(cb)) );
}""")

ArbitraryCappedCone3D = register_shader_module("""
@name ArbitraryCappedCone3D
@inputs pos, a, b, ra, rb
@outputs dist
@dependencies
float ArbitraryCappedCone3D( vec3 p, vec3 a, vec3 b, float ra, float rb )
{
  float rba  = rb-ra;
  float baba = dot(b-a,b-a);
  float papa = dot(p-a,p-a);
  float paba = dot(p-a,b-a)/baba;
  float x = sqrt( papa - paba*paba*baba );
  float cax = max(0.0,x-((paba<0.5)?ra:rb));
  float cay = abs(paba-0.5)-0.5;
  float k = rba*rba + baba;
  float f = clamp( (rba*(x-ra)+paba*baba)/k, 0.0, 1.0 );
  float cbx = x-ra - f*rba;
  float cby = paba - f;
  float s = (cbx<0.0 && cay<0.0) ? -1.0 : 1.0;
  return s*sqrt( min(cax*cax + cay*cay*baba,
                     cbx*cbx + cby*cby*baba) );
}""")

SolidAngle3D = register_shader_module("""
@name SolidAngle3D
@inputs pos, angle, radius
@outputs dist
@dependencies
float SolidAngle3D( vec3 p, float angle , float ra )
{
  // c is the sin/cos of the angle
  vec2 c = vec2(sin(angle), cos(angle));
  vec2 q = vec2( length(p.xz), p.y );
  float l = length(q) - ra;
  float m = length(q - c*clamp(dot(q,c),0.0,ra) );
  return max(l,m*sign(c.y*q.x-c.x*q.y));
}""")

CutSphere3D = register_shader_module("""
@name CutSphere3D
@inputs pos, radius, height
@outputs dist
@dependencies
float CutSphere3D( vec3 p, float r, float h )
{
  // sampling independent computations (only depend on shape)
  float w = sqrt(r*r-h*h);

  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  float s = max( (h-r)*q.x*q.x+w*w*(h+r-2.0*q.y), h*q.x-w*q.y );
  return (s<0.0) ? length(q)-r :
         (q.x<w) ? h - q.y     :
                   length(q-vec2(w,h));
}""")

CutHollowSphere = register_shader_module("""
@name CutHollowSphere
@inputs pos, radius, height, thickness
@outputs dist
@dependencies
float CutHollowSphere( vec3 p, float r, float h, float t )
{
  // sampling independent computations (only depend on shape)
  float w = sqrt(r*r-h*h);
  
  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  return ((h*q.x<w*q.y) ? length(q-vec2(w,h)) : 
                          abs(length(q)-r) ) - t;
}""")

DeathStar3D = register_shader_module("""
@name DeathStar3D
@inputs pos, ra, rb, d
@outputs dist
@dependencies
float DeathStar3D( vec3 p2, float ra, float rb, float d )
{
  // sampling independent computations (only depend on shape)
  float a = (ra*ra - rb*rb + d*d)/(2.0*d);
  float b = sqrt(max(ra*ra-a*a,0.0));
	
  // sampling dependant computations
  vec2 p = vec2( p2.x, length(p2.yz) );
  if( p.x*b-p.y*a > d*max(b-p.y,0.0) )
    return length(p-vec2(a,b));
  else
    return max( (length(p            )-ra),
               -(length(p-vec2(d,0.0))-rb));
}""")

RoundCone3D = register_shader_module("""
@name RoundCone3D
@inputs pos, height, radius
@outputs dist
@dependencies
float RoundCone3D( vec3 p, float r1, float r2, float h )
{
  // sampling independent computations (only depend on shape)
  float b = (r1-r2)/h;
  float a = sqrt(1.0-b*b);

  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  float k = dot(q,vec2(-b,a));
  if( k<0.0 ) return length(q) - r1;
  if( k>a*h ) return length(q-vec2(0.0,h)) - r2;
  return dot(q, vec2(a,b) ) - r1;
}""")

ArbitraryRoundCone3D = register_shader_module("""
@name ArbitraryRoundCone3D
@inputs pos, a, b, r1, r2
@outputs dist
@dependencies dot2
float ArbitraryRoundCone3D( vec3 p, vec3 a, vec3 b, float r1, float r2 )
{
  // sampling independent computations (only depend on shape)
  vec3  ba = b - a;
  float l2 = dot(ba,ba);
  float rr = r1 - r2;
  float a2 = l2 - rr*rr;
  float il2 = 1.0/l2;
    
  // sampling dependant computations
  vec3 pa = p - a;
  float y = dot(pa,ba);
  float z = y - l2;
  float x2 = dot2( pa*l2 - ba*y );
  float y2 = y*y*l2;
  float z2 = z*z*l2;

  // single square root!
  float k = sign(rr)*rr*rr*x2;
  if( sign(z)*a2*z2>k ) return  sqrt(x2 + z2)        *il2 - r2;
  if( sign(y)*a2*y2<k ) return  sqrt(x2 + y2)        *il2 - r1;
                        return (sqrt(x2*a2*il2)+y*rr)*il2 - r1;
}""")

InexactEllipsoid3D = register_shader_module("""
@name InexactEllipsoid3D
@inputs pos, radius
@outputs dist
@dependencies
float InexactEllipsoid3D( vec3 p, vec3 r )
{
  float k0 = length(p/r);
  float k1 = length(p/(r*r));
  return k0*(k0-1.0)/k1;
}""")

RevolvedVesica3D = register_shader_module("""
@name RevolvedVesica3D
@inputs pos, a, b, w
@outputs dist
@dependencies
float RevolvedVesica3D( vec3 p, vec3 a, vec3 b, float w )
{
    vec3  c = (a+b)*0.5;
    float l = length(b-a);
    vec3  v = (b-a)/l;
    float y = dot(p-c,v);
    vec2  q = vec2(length(p-c-y*v),abs(y));
    
    float r = 0.5*l;
    float d = 0.5*(r*r-w*w)/w;
    vec3  h = (r*q.x<d*(q.y-r)) ? vec3(0.0,r,0.0) : vec3(-d,0.0,d+w);
 
    return length(q-h.xy) - h.z;
}""")

Rhombus3D = register_shader_module("""
@name Rhombus3D
@inputs pos, la, lb, h, ra
@outputs dist
@dependencies ndot
float Rhombus3D( vec3 p, float la, float lb, float h, float ra )
{
  p = abs(p);
  vec2 b = vec2(la,lb);
  float f = clamp( (ndot(b,b-2.0*p.xz))/dot(b,b), -1.0, 1.0 );
  vec2 q = vec2(length(p.xz-0.5*b*vec2(1.0-f,1.0+f))*sign(p.x*b.y+p.z*b.x-b.x*b.y)-ra, p.y-h);
  return min(max(q.x,q.y),0.0) + length(max(q,0.0));
}""")

Octahedron3D = register_shader_module("""
@name Octahedron3D
@inputs pos, height
@outputs dist
@dependencies
float Octahedron3D( vec3 p, float s )
{
  p = abs(p);
  float m = p.x+p.y+p.z-s;
  vec3 q;
       if( 3.0*p.x < m ) q = p.xyz;
  else if( 3.0*p.y < m ) q = p.yzx;
  else if( 3.0*p.z < m ) q = p.zxy;
  else return m*0.57735027;
    
  float k = clamp(0.5*(q.z-q.y+s),0.0,s); 
  return length(vec3(q.x,q.y-s+k,q.z-k)); 
}""")

InexactOctahedron3D = register_shader_module("""
@name InexactOctahedron3D
@inputs pos, height
@outputs dist
@dependencies
float InexactOctahedron3D( vec3 p, float s)
{
  p = abs(p);
  return (p.x+p.y+p.z-s)*0.57735027;
}""")


Pyramid3D = register_shader_module("""
@name Pyramid3D
@inputs pos, height
@outputs dist
@dependencies
float Pyramid3D( vec3 p, float h )
{
  float m2 = h*h + 0.25;
    
  p.xz = abs(p.xz);
  p.xz = (p.z>p.x) ? p.zx : p.xz;
  p.xz -= 0.5;

  vec3 q = vec3( p.z, h*p.y - 0.5*p.x, h*p.x + 0.5*p.y);
   
  float s = max(-q.x,0.0);
  float t = clamp( (q.y-0.5*p.z)/(m2+0.25), 0.0, 1.0 );
    
  float a = m2*(q.x+s)*(q.x+s) + q.y*q.y;
  float b = m2*(q.x+0.5*t)*(q.x+0.5*t) + (q.y-m2*t)*(q.y-m2*t);
    
  float d2 = min(q.y,-q.x*m2-q.y*0.5) > 0.0 ? 0.0 : min(a,b);
    
  return sqrt( (d2+q.z*q.z)/m2 ) * sign(max(q.z,-p.y));
}""")

Triangle3D = register_shader_module("""
@name Triangle3D
@inputs pos, a, b, c
@outputs dist
@dependencies dot2
float Triangle3D( vec3 p, vec3 a, vec3 b, vec3 c )
{
  vec3 ba = b - a; vec3 pa = p - a;
  vec3 cb = c - b; vec3 pb = p - b;
  vec3 ac = a - c; vec3 pc = p - c;
  vec3 nor = cross( ba, ac );

  return sqrt(
    (sign(dot(cross(ba,nor),pa)) +
     sign(dot(cross(cb,nor),pb)) +
     sign(dot(cross(ac,nor),pc))<2.0)
     ?
     min( min(
     dot2(ba*clamp(dot(ba,pa)/dot2(ba),0.0,1.0)-pa),
     dot2(cb*clamp(dot(cb,pb)/dot2(cb),0.0,1.0)-pb) ),
     dot2(ac*clamp(dot(ac,pc)/dot2(ac),0.0,1.0)-pc) )
     :
     dot(nor,pa)*dot(nor,pa)/dot2(nor) );
}""")

Quadrilateral3D = register_shader_module("""
@name Quadrilateral3D
@inputs pos, a, b, c, d
@outputs dist
@dependencies dot2
float Quadrilateral3D( vec3 p, vec3 a, vec3 b, vec3 c, vec3 d )
{
  vec3 ba = b - a; vec3 pa = p - a;
  vec3 cb = c - b; vec3 pb = p - b;
  vec3 dc = d - c; vec3 pc = p - c;
  vec3 ad = a - d; vec3 pd = p - d;
  vec3 nor = cross( ba, ad );

  return sqrt(
    (sign(dot(cross(ba,nor),pa)) +
     sign(dot(cross(cb,nor),pb)) +
     sign(dot(cross(dc,nor),pc)) +
     sign(dot(cross(ad,nor),pd))<3.0)
     ?
     min( min( min(
     dot2(ba*clamp(dot(ba,pa)/dot2(ba),0.0,1.0)-pa),
     dot2(cb*clamp(dot(cb,pb)/dot2(cb),0.0,1.0)-pb) ),
     dot2(dc*clamp(dot(dc,pc)/dot2(dc),0.0,1.0)-pc) ),
     dot2(ad*clamp(dot(ad,pd)/dot2(ad),0.0,1.0)-pd) )
     :
     dot(nor,pa)*dot(nor,pa)/dot2(nor) );
}""")

NoParamCuboid3D = register_shader_module("""
@name NoParamCuboid3D
@inputs pos
@outputs dist
@dependencies
float NoParamCuboid3D( vec3 p )
{
  return length(max(abs(p)-vec3(0.5),0.0));
}""")

NoParamSphere3D = register_shader_module("""
@name NoParamSphere3D
@inputs pos
@outputs dist
@dependencies
float NoParamSphere3D( vec3 p )
{
  return length(p)-0.5;
}""")

NoParamCylinder3D = register_shader_module("""
@name NoParamCylinder3D
@inputs pos
@outputs dist
@dependencies
float NoParamCylinder3D( vec3 p )
{
  float r_val = length(p.xz) - 0.5;
  float h_val = abs(p.y) - 0.5;
  vec2 cval = vec2(r_val, h_val);
  return min(max(cval.x, cval.y), 0.0) + length(max(cval, 0.0));
}""")

InexactSuperQuadrics3D = register_shader_module("""
@name InexactSuperQuadrics3D
@inputs pos, a, b, c
@outputs dist
@dependencies
@vardeps EPSILON
float InexactSuperQuadrics3D( vec3 p, vec3 skew_vec, float epsilon_1, float epsilon_2 )
{
  vec3 q = abs(p);
  float out_1 = pow(q.x / skew_vec.x, 2.0 / (epsilon_2 + EPSILON));
  float out_2 = pow(q.y / skew_vec.y, 2.0 / (epsilon_2 + EPSILON));
  float out_3 = pow(q.z / skew_vec.z, 2.0 / (epsilon_1 + EPSILON));

  float inside_term = pow(abs(out_1 + out_2) + EPSILON, epsilon_2 / (epsilon_1 + EPSILON));
  float base_sdf = 1.0 - pow(abs(inside_term + out_3) + EPSILON, -epsilon_1 / 2.0);
  // scale the sdf by max skew?
  //float max_skew = max(skew_vec.x, max(skew_vec.y, skew_vec.z));
  //base_sdf *= 0.01;
  return base_sdf;
}""")

InexactAnisotropicGaussian3D = register_shader_module("""
@name InexactAnisotropicGaussian3D
@inputs pos, center, axial_radii, scale_constant
@outputs dist
@dependencies
float InexactAnisotropicGaussian3D(
    vec3 p,
    vec3 center,
    vec3 axial_radii,
    float scale_constant
) {
    vec3 d = p - center;
    vec3 q = -(d * d) / (2.0 * axial_radii * axial_radii);
    float base_sdf = scale_constant * exp(q.x + q.y + q.z);
    return base_sdf;
}""")

SimpleExtrusion3D = register_shader_module("""
@name SimpleExtrusion3D
@inputs pos, sdf2d, height
@outputs dist
@dependencies
float SimpleExtrusion3D( vec3 p, float sdf2d, float height )
{
  float h_val = abs(p.y) - height/2.0;
  vec2 cval = vec2(sdf2d, h_val);
  return min(max(cval.x, cval.y), 0.0) + length(max(cval, 0.0));
}""")


SimpleRevolution3D = register_shader_module("""
@name SimpleRevolution3D
@inputs pos, sdf2d, height
@outputs dist
@dependencies
vec2 SimpleRevolution3D( vec3 p, float o)
{
    vec2 q = vec2( length(p.xz) - o, p.y );
    return q;
}""")