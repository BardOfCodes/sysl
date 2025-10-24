# Goal geolipi. 

from geolipi.symbolic import GLFunction
import geolipi.symbolic as gls
from geolipi.symbolic.registry import register_symbol
from .materials import MaterialV3, MaterialV4

SDFGrid3D = gls.SDFGrid3D

@register_symbol
class RGBGrid3D(GLFunction):
    @classmethod
    def default_spec(cls):
        return {
            "rbg_grid": {"type": "Tensor[float,(D,H,W,3)]"},
            "name": {"type": "string"},
            "metallic": {"type": "Tensor[float,(D,H,W)]"},
            "roughness": {"type": "Tensor[float,(D,H,W)]"},
            "bound_threshold": {"type": "float", "optional": True}
        }
    
@register_symbol
class SphericalRGBGrid3D(GLFunction):
    @classmethod
    def default_spec(cls):
        return {
            "rbg_grid": {"type": "Tensor[float,(H,W,3)]"},
            "name": {"type": "string"},
            "metallic": {"type": "Tensor[float,(H,W)]"},
            "roughness": {"type": "Tensor[float,(H,W)]"},
            "bound_threshold": {"type": "float", "optional": True}
        }
# ===== Encoded SDF Grid 3D =====

@register_symbol
class EncodedSDFGrid3D(GLFunction):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "bound_threshold": {"type": "float", "optional": True}
        }
            


@register_symbol
class EncodedLowPrecisionSDFGrid3D(EncodedSDFGrid3D):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class AABBEncodedSDFGrid3D(EncodedSDFGrid3D):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class OBBEncodedSDFGrid3D(EncodedSDFGrid3D):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class EncodedRGBGrid3D(MaterialV3):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "metallic": {"type": "Tensor[float,(D,H,W)]"},
            "roughness": {"type": "Tensor[float,(D,H,W)]"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class EncodedRGBGrid3DV4(MaterialV4):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[4]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "mrc": {"type": "Vector[3]"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class EncodedSphericalRGBGrid3DV4(MaterialV4):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[3]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "mrc": {"type": "Vector[3]"},
            "bound_threshold": {"type": "float", "optional": True}
        }

@register_symbol
class ESRGB3DShifted(EncodedSphericalRGBGrid3DV4):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "data": {"type": "string", "description": "Data in Encoded Format"},
            "shape": {"type": "Vector[3]", },
            "type": {"type": "string", "description": "Type of the SDF Grid"},
            "mrc": {"type": "Vector[3]"},
            "bound_threshold": {"type": "float", "optional": True},
            "shift": {"type": "Vector[2]"},
            "scale": {"type": "Vector[2]"},
        }

@register_symbol
class ESRGB3DShiftedDummy(EncodedSphericalRGBGrid3DV4):
    @classmethod
    def default_spec(cls):
        return {
            "name": {"type": "string"},
            "mrc": {"type": "Vector[3]"},
            "bound_threshold": {"type": "float", "optional": True},
            "shift": {"type": "Vector[2]"},
            "scale": {"type": "Vector[2]"},
        }