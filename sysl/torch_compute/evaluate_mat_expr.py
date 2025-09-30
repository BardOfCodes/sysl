# Ideal its the same as evaluate expression - except for Combinators and for material operators. 

import sys
import sympy as sp
import torch as th
from typing import Optional, Union, Callable, Any, TypeVar

if sys.version_info >= (3, 11):
    from functools import singledispatch
else:
    from geolipi.torch_compute.patched_functools import singledispatch

from geolipi.symbolic.base import GLExpr, GLFunction
import geolipi.symbolic as gls
from geolipi.symbolic.resolve import resolve_macros
from geolipi.symbolic import Revolution3D
from geolipi.symbolic.symbol_types import (
    MACRO_TYPE,
    MOD_TYPE,
    PRIM_TYPE,
    COMBINATOR_TYPE,
    TRANSFORM_TYPE,
    POSITIONALMOD_TYPE,
    SDFMOD_TYPE,
    HIGHER_PRIM_TYPE,
    EXPR_TYPE,
    SUPERSET_TYPE
)
from geolipi.torch_compute.sketcher import Sketcher
from geolipi.torch_compute.maps import PRIMITIVE_MAP
from geolipi.torch_compute.constants import EPSILON
from geolipi.torch_compute.sympy_to_torch import SYMPY_TO_TORCH, TEXT_TO_SYMPY
from geolipi.torch_compute.evaluate_expression import _parse_param_from_expr
### Create a Evaluate wrapper -> This will create the coords and may be different in different derivative languages.
import sysl.symbolic as sls
from .maps import MATERIAL_MAP, COMBINATOR_MAP, MODIFIER_MAP

def recursive_evaluate_mat_expr(expression: SUPERSET_TYPE, sketcher: Sketcher, 
             secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None, 
             *args, **kwargs) -> th.Tensor:
    """
    Evaluates a GeoLIPI expression using the provided sketcher and coordinates.
    
    Parameters:
        expression (SUPERSET_TYPE): The GeoLIPI expression to evaluate.
        sketcher (Sketcher): The sketcher object used for evaluation.
        secondary_sketcher (Sketcher, optional): A secondary sketcher for higher-order primitives.
        coords (th.Tensor, optional): Coordinates for evaluation. If None, generated from sketcher.
        
    Returns:
        th.Tensor: The result of evaluating the expression.
    """
    if coords is None:
        coords = sketcher.get_homogenous_coords()
    else:
        coords_dim = coords.shape[-1]
        if coords_dim == sketcher.n_dims:
            coords = sketcher.make_homogenous_coords(coords)
        elif coords_dim == sketcher.n_dims + 1:
            pass
        else:
            raise ValueError("Coordinates must have n_dims or n_dims - 1 dimensions.")
    return rec_eval_mat_expr(
        expression,
        sketcher,
        secondary_sketcher=secondary_sketcher,
        coords=coords,
        *args, **kwargs
    )

@singledispatch
def rec_eval_mat_expr(expression: SUPERSET_TYPE, sketcher: Sketcher,
             secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
             *args, **kwargs) -> th.Tensor:
    raise NotImplementedError(
        f"Expression type {type(expression)} is not supported for recursive evaluation."
    )

@rec_eval_mat_expr.register
def eval_mod(expression: MOD_TYPE, sketcher: Sketcher, 
             secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
             *args, **kwargs) -> th.Tensor:
    sub_expr = expression.args[0]
    params = expression.args[1:]
    params = _parse_param_from_expr(expression, params, sketcher)
    # This is a hack unclear how to deal with other types)
    if isinstance(expression, TRANSFORM_TYPE):
        identity_mat = sketcher.get_affine_identity()
        new_transform = MODIFIER_MAP[type(expression)](identity_mat, *params)
        coords = th.einsum("ij,mj->mi", new_transform, coords)
        return rec_eval_mat_expr(sub_expr, sketcher,secondary_sketcher,coords,
                        *args, **kwargs)
    elif isinstance(expression, POSITIONALMOD_TYPE):
        # instantiate positions and send that as input with affine set to None
        coords = MODIFIER_MAP[type(expression)](coords, *params)
        return rec_eval_mat_expr(sub_expr, sketcher, secondary_sketcher, coords,
                        *args, **kwargs)
    elif isinstance(expression, SDFMOD_TYPE):
        # calculate sdf then create change before returning.
        sdf_estimate = rec_eval_mat_expr(sub_expr, sketcher, secondary_sketcher, coords,
                                *args, **kwargs)
        updated_sdf = MODIFIER_MAP[type(expression)](sdf_estimate, *params)
        return updated_sdf
    else:
        raise NotImplementedError(f"Modifier {expression} not implemented")
    
@rec_eval_mat_expr.register
def eval_prim(expression: PRIM_TYPE, sketcher: Sketcher,
              secondary_sketcher: Optional[Sketcher] = None, coords: th.Tensor = None,
              *args, **kwargs) -> th.Tensor:
    
    if isinstance(expression, HIGERPRIM_TYPE):
        raise NotImplementedError(f"Higher order primitive {expression} not implemented")
    else:
        params = expression.args

    params = _parse_param_from_expr(expression, params, sketcher)
    n_dims = sketcher.n_dims
    coords = coords[..., :n_dims] / (coords[..., n_dims : n_dims + 1] + EPSILON)
    sdf = PRIMITIVE_MAP[type(expression)](coords, *params)
    return sdf

@rec_eval_mat_expr.register
def eval_mat_solid(expression: sls.MatSolid, sketcher: Sketcher,
                   secondary_sketcher: Optional[Sketcher] = None, coords: th.Tensor = None,
                   *args, **kwargs) -> th.Tensor:
    
    sdf_expr = expression.args[0]
    material_expr = expression.args[1]
    sdf_eval = rec_eval_mat_expr(sdf_expr, sketcher, secondary_sketcher, coords, *args, **kwargs)
    material_eval = rec_eval_mat_expr(material_expr, sketcher, secondary_sketcher, coords, *args, **kwargs)
    if sdf_eval.dim() == 2:
        out = th.cat([sdf_eval[..., :1], material_eval], dim=-1)
    else:
        out = th.cat([sdf_eval.unsqueeze(-1), material_eval], dim=-1)
    return out

@rec_eval_mat_expr.register
def eval_material(expression: sls.Material, sketcher: Sketcher,
                   secondary_sketcher: Optional[Sketcher] = None, coords: th.Tensor = None,
                   *args, **kwargs) -> th.Tensor:
    params = expression.args
    params = _parse_param_from_expr(expression, params, sketcher)
    sdf_material_stack = MATERIAL_MAP[type(expression)](coords, *params)
    return sdf_material_stack

@rec_eval_mat_expr.register
def eval_comb(expression: COMBINATOR_TYPE, sketcher: Sketcher,
              secondary_sketcher: Optional[Sketcher] = None, coords: th.Tensor = None,
              *args, **kwargs) -> th.Tensor:
    
    tree_branches, param_list = [], []
    for arg in expression.args:
        if arg in expression.lookup_table:
            assert isinstance(arg, sp.Symbol), "Argument must be a symbol"
            param_list.append(expression.lookup_table[arg])
        else:
            tree_branches.append(arg)
    sdf_list = []
    for child in tree_branches:
        cur_sdf = rec_eval_mat_expr(child, sketcher, secondary_sketcher, coords=coords.clone(),
                           *args, **kwargs)
        sdf_list.append(cur_sdf)
    # This changes -> We need to use channel aware way of doing it. 
    new_sdf = COMBINATOR_MAP[type(expression)](*sdf_list, *param_list)
    # Here. 
    return new_sdf



@rec_eval_mat_expr.register
def eval_gl_expr(expression: EXPR_TYPE, sketcher: Sketcher,
                 secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
                 *args, **kwargs) -> th.Tensor:
    
    evaluated_args = []
    # print("expr args", expr.args)
    for arg in expression.args:
        if isinstance(arg, (GLFunction, GLExpr)):
            output = rec_eval_mat_expr(arg, sketcher, secondary_sketcher, coords, *args, **kwargs)
            evaluated_args.append(output)
            # just use tensor symbols here
        elif isinstance(arg, (sp.Float, sp.Integer)):
            new_value = float(arg)
            evaluated_args.append(new_value)
        else:
            print(type(arg))
            raise NotImplementedError(f"Params for{expression} not implemented")
    op = SYMPY_TO_TORCH[expression.func]
    output = op(*evaluated_args)
    return output

@rec_eval_mat_expr.register
def eval_gl_param(expression: gls.Param, sketcher: Sketcher,
                 secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
                 *args, **kwargs) -> th.Tensor:
    assert isinstance(expression.args[0], sp.Symbol), "Argument must be a symbol"
    return expression.lookup_table[expression.args[0]]

@rec_eval_mat_expr.register
def eval_gl_op(expression: gls.Operator, sketcher: Sketcher,
               secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
               *args, **kwargs) -> th.Tensor:
    if isinstance(expression, (gls.UnaryOperator, gls.BinaryOperator)):
        outputs = []
        args = expression.args[:-1]
        for arg in args:
            eval = rec_eval_mat_expr(arg, sketcher, secondary_sketcher, coords, *args, **kwargs)
            outputs.append(eval)
        op_arg = expression.args[-1]
        assert isinstance(op_arg, sp.Symbol), "Operator argument must be a string"
        op = SYMPY_TO_TORCH[TEXT_TO_SYMPY[op_arg.name]]
        output = op(*outputs)
        return output
    elif isinstance(expression, gls.VectorOperator):
        raise NotImplementedError(f"Vector Operator {expression} not implemented")
    else:
        raise NotImplementedError(f"Operator {expression} not implemented")

@rec_eval_mat_expr.register
def eval_gl_var(expression: gls.Variable, sketcher: Sketcher,
                secondary_sketcher: Optional[Sketcher] = None, coords: Optional[th.Tensor] = None,
                *args, **kwargs) -> th.Tensor:
    raise NotImplementedError(f"Variable {expression} not supported in GeoLIPI. It is supported in derivatives")
