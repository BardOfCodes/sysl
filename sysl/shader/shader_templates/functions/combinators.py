"""
Combinator shader module factory functions.

This module provides factory functions for creating combinator shader modules
using the template definitions and shader module classes.
"""

from ...shader_module import SMMap
from ...shader_module_classes import NAryShaderModule, FixedArityShaderModule
from .combinator_templates import (
    DIFF_ARITY_MAP,
    SWITCHED_DIFF_ARITY_MAP,
    COMPLEMENT_ARITY_MAP,
    SMOOTH_UNION_ARITY_MAP,
    GEOM_ONLY_SMOOTH_UNION_ARITY_MAP,
    SMOOTH_INTERSECTION_ARITY_MAP,
    SMOOTH_DIFFERENCE_ARITY_MAP,
    DILATE_ARITY_MAP,
    ERODE_ARITY_MAP,
    ONION_ARITY_MAP,
    NEG_ONLY_ONION_ARITY_MAP
)


def union_factory():
    """Create a Union shader module."""
    name = "Union"
    module = NAryShaderModule(name)
    return module


def intersection_factory():
    """Create an Intersection shader module."""
    name = "Intersection"
    module = NAryShaderModule(name)
    return module


def diff_factory():
    """Create a Difference shader module."""
    name = "Difference"
    module = FixedArityShaderModule(name, DIFF_ARITY_MAP)
    return module


def switched_diff_factory():
    """Create a SwitchedDifference shader module."""
    name = "SwitchedDifference"
    module = FixedArityShaderModule(name, SWITCHED_DIFF_ARITY_MAP)
    return module


def complement_factory():
    """Create a Complement shader module."""
    name = "Complement"
    module = FixedArityShaderModule(name, COMPLEMENT_ARITY_MAP)
    return module


def smooth_union_factory():
    """Create a SmoothUnion shader module."""
    name = "SmoothUnion"
    module = FixedArityShaderModule(name, SMOOTH_UNION_ARITY_MAP)
    return module


def geom_only_smooth_union_factory():
    """Create a GeomOnlySmoothUnion shader module."""
    name = "GeomOnlySmoothUnion"
    module = FixedArityShaderModule(name, GEOM_ONLY_SMOOTH_UNION_ARITY_MAP)
    return module


def smooth_intersection_factory():
    """Create a SmoothIntersection shader module."""
    name = "SmoothIntersection"
    module = FixedArityShaderModule(name, SMOOTH_INTERSECTION_ARITY_MAP)
    return module


def smooth_difference_factory():
    """Create a SmoothDifference shader module."""
    name = "SmoothDifference"
    module = FixedArityShaderModule(name, SMOOTH_DIFFERENCE_ARITY_MAP)
    return module


def dilate_factory():
    """Create a Dilate3D shader module."""
    name = "Dilate3D"
    module = FixedArityShaderModule(name, DILATE_ARITY_MAP)
    return module


def erode_factory():
    """Create an Erode3D shader module."""
    name = "Erode3D"
    module = FixedArityShaderModule(name, ERODE_ARITY_MAP)
    return module


def onion_factory():
    """Create an Onion3D shader module."""
    name = "Onion3D"
    module = FixedArityShaderModule(name, ONION_ARITY_MAP)
    return module


def neg_only_onion_factory():
    """Create a NegOnlyOnion3D shader module."""
    name = "NegOnlyOnion3D"
    module = FixedArityShaderModule(name, NEG_ONLY_ONION_ARITY_MAP)
    return module


# Register all factory functions in the shader module map
SMMap["Union"] = union_factory
SMMap["Intersection"] = intersection_factory
SMMap["Difference"] = diff_factory
SMMap["SwitchedDifference"] = switched_diff_factory
SMMap["Complement"] = complement_factory
SMMap["SmoothUnion"] = smooth_union_factory
SMMap["GeomOnlySmoothUnion"] = geom_only_smooth_union_factory
SMMap["SmoothIntersection"] = smooth_intersection_factory
SMMap["SmoothDifference"] = smooth_difference_factory
SMMap["Dilate3D"] = dilate_factory
SMMap["Erode3D"] = erode_factory
SMMap["Onion3D"] = onion_factory
SMMap["NegOnlyOnion3D"] = neg_only_onion_factory
