import geolipi.symbolic as gls
from geolipi.symbolic import GLFunction
from geolipi.symbolic.registry import register_symbol


class MatSolidCombinator(gls.Combinator):
    ...

@register_symbol
class MatColorOnly(MatSolidCombinator):
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}}

@register_symbol
class MatSmoothColorOnly(MatSolidCombinator):
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}, "k": {"type": "float"}}

@register_symbol
class Repel(gls.Combinator):
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}}

@register_symbol
class Avoid(gls.Combinator):
    @classmethod
    def default_spec(cls):
        return {"expr_0": {"type": "Expr"}, "expr_1": {"type": "Expr"}}
