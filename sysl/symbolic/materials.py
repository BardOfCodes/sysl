from geolipi.symbolic import GLFunction
from geolipi.symbolic.registry import register_symbol


class Material(GLFunction):
    ...

@register_symbol
class SMPLMaterial(Material):
    """
    Apply the height field to the current height.
    """
    ...

@register_symbol
class RGBMaterial(Material):
    """
    Apply the height field to the current height.
    """
    ...

@register_symbol
class MaterialV3(Material):
    ...

@register_symbol
class NonEmissiveMaterialV3(MaterialV3):
    ...


@register_symbol
class MatReference(MaterialV3):
    """
    Apply the height field to the current height.
    """
    ...

@register_symbol
class RegisterMaterial(GLFunction):
    """
    Apply the height field to the current height.
    """
    ...


@register_symbol
class RGBGrid3D(GLFunction):
    ...

@register_symbol
class EncodedRGBGrid3D(MaterialV3):
    ...
