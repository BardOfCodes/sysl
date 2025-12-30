"""
Base symbolic classes for SySL - Material-Solid combinations.

This module defines the core MatSolid classes that combine SDF geometry 
with material properties for rendering.

Version Guide:
- V1: Simple index-based material lookup (fast, limited colors)
- V2: Direct RGB color assignment
- V3: PBR materials with per-material shader functions (flexible, heavier)
- V4: Simplified PBR with packed MRC (metallic, roughness, clearcoat) vector
"""

from geolipi.symbolic import GLFunction
import geolipi.symbolic as gls
from geolipi.symbolic.registry import register_symbol

# ============================================================================
# Shared spec templates
# ============================================================================

_MAT_SOLID_SPEC = {"solid": {"type": "Expr"}, "material": {"type": "Expr"}}


class MatSolid(GLFunction):
    """
    Base class for Material-Solid combinations.
    
    A MatSolid pairs an SDF geometry expression with a material expression,
    enabling rendering with appearance properties.
    """
    symbol_category = "sysl_base"


@register_symbol
class MatSolidV1(MatSolid):
    """
    Material-Solid using V1 renderer (index-based material lookup).
    
    Uses a simple color palette indexed by integer. Fast rendering but
    limited color control. Best for quick previews or stylized rendering.
    """
    @classmethod
    def default_spec(cls):
        return _MAT_SOLID_SPEC.copy()


@register_symbol
class MatSolidV2(MatSolid):
    """
    Material-Solid using V2 renderer (direct RGB colors).
    
    Each solid gets a direct RGB color. Simple and intuitive but no
    advanced material properties like metallic or roughness.
    """
    @classmethod
    def default_spec(cls):
        return _MAT_SOLID_SPEC.copy()


@register_symbol
class MatSolidV3(MatSolid):
    """
    Material-Solid using V3 renderer (full PBR with material functions).
    
    Supports per-material shader functions that can vary based on surface
    position and normal. Most flexible but heavier to render. Based on
    Matthieu Jaquemet's PBR implementation.
    """
    @classmethod
    def default_spec(cls):
        return _MAT_SOLID_SPEC.copy()


@register_symbol
class MatSolidV4(MatSolid):
    """
    Material-Solid using V4 renderer (simplified PBR).
    
    Uses packed MRC vector (metallic, roughness, clearcoat) for material
    properties. Good balance of quality and performance. Recommended for
    most use cases.
    """
    @classmethod
    def default_spec(cls):
        return _MAT_SOLID_SPEC.copy()


@register_symbol
class BoundedSolid(GLFunction):
    """
    A solid with an explicit bounding volume for optimization.
    
    The bounding expression is evaluated first; if the ray is outside
    the bound_threshold, the inner expression is skipped. Useful for
    complex geometry that benefits from spatial culling.
    """
    symbol_category = "sysl_base"
    
    @classmethod
    def default_spec(cls):
        return {
            "expr": {"type": "Expr"},
            "bounding": {"type": "Expr"},
            "bound_threshold": {"type": "float", "optional": True}
        }


@register_symbol
class GeomOnlySmoothUnion(gls.SmoothUnion):
    """
    Smooth union that blends geometry but keeps materials separate.
    
    Unlike regular SmoothUnion which also blends materials, this version
    smoothly blends the SDF values while selecting the material from
    whichever surface is closer. Useful when you want smooth geometry
    transitions but distinct material boundaries.
    """
    symbol_category = "sysl_base"
    
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}, "k": {"type": "float"}}
