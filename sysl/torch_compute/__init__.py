"""
Torch-based computation module for SySL.

This module provides PyTorch implementations for evaluating SySL expressions,
including material-aware SDF combinators and material functions.

Main entry point:
    recursive_evaluate_mat_expr: Evaluate a SySL expression to a tensor
"""

from .evaluate_mat_expr import recursive_evaluate_mat_expr
from .maps import MATERIAL_MAP, COMBINATOR_MAP, MODIFIER_MAP

__all__ = [
    "recursive_evaluate_mat_expr",
    "MATERIAL_MAP",
    "COMBINATOR_MAP", 
    "MODIFIER_MAP",
]

