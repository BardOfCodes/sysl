from geolipi.symbolic import GLFunction
from geolipi.symbolic.registry import register_symbol


class Material(GLFunction):
    ...

@register_symbol
class SMPLMaterial(Material):
    """
    Apply the height field to the current height.
    """
    @classmethod
    def default_spec(cls):
        return {"smpl_index": {"type": "int"}}

@register_symbol
class RGBMaterial(Material):
    """
    Apply the height field to the current height.
    """
    @classmethod
    def default_spec(cls):
        return {"rgb": {"type": "Vector[3]"}}

@register_symbol
class MaterialV3(Material):
    @classmethod
    def default_spec(cls):
        return {
            "albedo": {"type": "Vector[3]"},
            "emissive": {"type": "Vector[3]"},
            "roughness": {"type": "float"},
            "clearcoat": {"type": "float"},
            "metallic": {"type": "float"}
        }
@register_symbol
class NonEmissiveMaterialV3(MaterialV3):
    @classmethod
    def default_spec(cls):
        return {
            "albedo": {"type": "Vector[3]"},
            "roughness": {"type": "float"},
            "clearcoat": {"type": "float"},
            "metallic": {"type": "float"}
        }


@register_symbol
class MatReference(MaterialV3):
    """
    Apply the height field to the current height.
    """
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}}

@register_symbol
class RegisterMaterial(GLFunction):
    """
    Apply the height field to the current height.
    """
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}, "material": {"type": "Node[Material]"}}


@register_symbol
class RGBGrid3D(GLFunction):
    @classmethod
    def default_spec(cls):
        return {"data": {"type": "Tensor[float,(D,H,W,3)]"}}
    
@register_symbol
class EncodedRGBGrid3D(MaterialV3):
    @classmethod
    def default_spec(cls):
        return {"data": {"type": "Tensor[float,(D,H,W,3)]"}}