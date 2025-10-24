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
    symbol_category = "sysl_base"

@register_symbol
class MatSolidV1(MatSolid):
    @classmethod
    def default_spec(cls):
        return {"solid": {"type": "Expr"}, "material": {"type": "Expr"}}
@register_symbol
class MatSolidV2(MatSolid):
    @classmethod
    def default_spec(cls):
        return {"solid": {"type": "Expr"}, "material": {"type": "Expr"}}

@register_symbol
class MatSolidV3(MatSolid):
    @classmethod
    def default_spec(cls):
        return {"solid": {"type": "Expr"}, "material": {"type": "Expr"}}

@register_symbol
class MatSolidV4(MatSolid):
    @classmethod
    def default_spec(cls):
        return {"solid": {"type": "Expr"}, "material": {"type": "Expr"}}

@register_symbol
class BoundedSolid(GLFunction):
    """
    Contains an SDF function and a material.
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
    symbol_category = "sysl_base"
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}, "k": {"type": "float"}}
