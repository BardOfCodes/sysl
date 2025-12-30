"""
Material definitions for SySL rendering system.

Materials define the appearance properties of surfaces. Different material
versions correspond to different renderer capabilities:

- V1/V2: Simple materials (index or RGB color)
- V3: Full PBR with separate material shader functions
- V4: Simplified PBR with packed material properties
"""

from geolipi.symbolic import GLFunction
from geolipi.symbolic.registry import register_symbol


class Material(GLFunction):
    """Base class for all material types in SySL."""
    symbol_category = "sysl_materials"


# ============================================================================
# V1/V2 Materials - Simple color assignment
# ============================================================================

@register_symbol
class MaterialV1(Material):
    """
    Index-based material for V1 renderer.
    
    References a color from a predefined palette by integer index.
    Fast but limited flexibility.
    """
    @classmethod
    def default_spec(cls):
        return {"smpl_index": {"type": "int"}}


@register_symbol
class MaterialV2(Material):
    """
    Direct RGB color material for V2 renderer.
    
    Specifies surface color directly as RGB values [0-1].
    Simple and intuitive for basic coloring.
    """
    @classmethod
    def default_spec(cls):
        return {"rgb": {"type": "Vector[3]"}}


# ============================================================================
# V3 Materials - Full PBR with material functions
# ============================================================================

@register_symbol
class MaterialV3(Material):
    """
    Full PBR material for V3 renderer.
    
    Supports complete physically-based rendering properties including
    emissive surfaces. Used with per-material shader functions.
    
    Properties:
        albedo: Base color RGB [0-1]
        emissive: Emission color RGB (can exceed 1 for HDR)
        roughness: Surface roughness [0=smooth, 1=rough]
        clearcoat: Clear coat layer intensity [0-1]
        metallic: Metallic vs dielectric [0=dielectric, 1=metal]
    """
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
    """
    PBR material without emission for V3 renderer.
    
    Same as MaterialV3 but without emissive property. Use when surfaces
    don't need to emit light (most common case).
    """
    @classmethod
    def default_spec(cls):
        return {
            "albedo": {"type": "Vector[3]"},
            "roughness": {"type": "float"},
            "clearcoat": {"type": "float"},
            "metallic": {"type": "float"}
        }


@register_symbol
class MatRefV3(MaterialV3):
    """
    Reference to a named material definition for V3 renderer.
    
    Instead of inline material properties, references a material
    registered elsewhere by name. Useful for reusing materials.
    """
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}}


@register_symbol
class RegisterMaterial(GLFunction):
    """
    Register a named material for later reference.
    
    Creates a reusable material definition that can be referenced
    by MatRefV3 or MatRefV4 using its name.
    """
    symbol_category = "sysl_materials"
    
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}, "material": {"type": "Expr"}}


# ============================================================================
# V4 Materials - Simplified PBR with packed properties
# ============================================================================

@register_symbol
class MaterialV4(Material):
    """
    Simplified PBR material for V4 renderer.
    
    Packs material properties into vectors for efficient GPU transfer.
    Recommended for most production use cases.
    
    Properties:
        albedo: Base color RGB [0-1]
        emissive: Emission color RGB
        mrc: Packed vector of (metallic, roughness, clearcoat)
    """
    @classmethod
    def default_spec(cls):
        return {
            "albedo": {"type": "Vector[3]"},
            "emissive": {"type": "Vector[3]"},
            "mrc": {"type": "Vector[3]"},
        }


@register_symbol
class MaterialV1V4(MaterialV4):
    """
    Simple V4 material with just albedo and metallic/roughness.
    
    Minimal material for cases where clearcoat and emission aren't needed.
    
    Properties:
        albedo: Base color RGB [0-1]
        mr: Packed vector of (metallic, roughness)
    """
    @classmethod
    def default_spec(cls):
        return {
            "albedo": {"type": "Vector[3]"},
            "mr": {"type": "Vector[2]"},
        }


@register_symbol
class MatRefV4(MaterialV4):
    """
    Reference to a named material definition for V4 renderer.
    
    Note: Not yet fully supported. Use inline materials for now.
    """
    @classmethod
    def default_spec(cls):
        return {"name": {"type": "str"}}


@register_symbol
class MatMixV4(MaterialV4):
    """
    Linear interpolation between two V4 materials.
    
    Blends between two materials based on parameter t.
    Result = expr_a * (1-t) + expr_b * t
    
    Properties:
        expr_a: First material expression
        expr_b: Second material expression
        t: Blend factor [0=fully A, 1=fully B]
    """
    @classmethod
    def default_spec(cls):
        return {
            "expr_a": {"type": "Expr"},
            "expr_b": {"type": "Expr"},
            "t": {"type": "float"},
        }
