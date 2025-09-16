# Goal geolipi. 

from geolipi.symbolic import GLFunction
import geolipi.symbolic as gls
from geolipi.symbolic.registry import register_symbol


# Noisy Normals.. with normal maps. 
# So need to consider how the UV is defined. 
class MatSolid(GLFunction):
    """
    Contains an SDF function and a material.
    """

@register_symbol
class MatSolidV1(MatSolid):
    ...
@register_symbol
class MatSolidV2(MatSolid):
    ...

@register_symbol
class MatSolidV3(MatSolid):
    ...


@register_symbol
class BoundedSolid(GLFunction):
    """
    Contains an SDF function and a material.
    """

@register_symbol
class GeomOnlySmoothUnion(gls.SmoothUnion):
    ...

@register_symbol
class EncodedSDFGrid3D(GLFunction):
    ...

@register_symbol
class LowPrecisionSDFGrid3D(GLFunction):
    ...

@register_symbol
class EncodedLowPrecisionSDFGrid3D(EncodedSDFGrid3D):
    ...
