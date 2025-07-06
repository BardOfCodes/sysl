import geolipi.symbolic as gls
from geolipi.symbolic import GLFunction
from geolipi.symbolic.registry import register_symbol


class MatSolidCombinator(gls.Combinator):
    ...

@register_symbol
class MatColorOnly(MatSolidCombinator):
    ...

@register_symbol
class MatSmoothColorOnly(MatSolidCombinator):
    ...

@register_symbol
class Repel(gls.Combinator):
    ...

@register_symbol
class Avoid(gls.Combinator):
    ...
