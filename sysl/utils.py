import numpy as np
import geolipi.symbolic as gls
import sysl.symbolic as sls
from geolipi.symbolic.symbol_types import PRIM_TYPE


def recursive_gls_to_sysl(gls_expr, ind=0, version="v4", mode="complex", colors=None):
    if isinstance(gls_expr, gls.GLBase):
        if isinstance(gls_expr, PRIM_TYPE):
            if version == "v1":
                new_expr = sls.MatSolidV1(gls_expr, 
                sls.MaterialV1((float(ind),))
                )
            elif version == "v2":
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV2(gls_expr, 
                sls.MaterialV2(color))
            elif version == "v3":
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV3(gls_expr, 
                sls.NonEmissiveMaterialV3(color, (0.0,), (0.9,), (0.9,)))
            elif version == "v4":
                if colors is None:
                    color = tuple(np.random.rand(3).tolist())
                else:
                    color = colors[ind]
                if mode == "simple":
                    mat_expr = sls.MaterialV1V4(color, (0.0, 1.9))
                else:
                    mat_expr = sls.MaterialV4(color, (0.0, 0.0,0.0), (0.5, 0.2, 0.8,))
                new_expr = sls.MatSolidV4(gls_expr, mat_expr)
            else:
                raise ValueError(f"Invalid version: {version}")
            ind += 1
            return new_expr, ind
        else:
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr, ind = recursive_gls_to_sysl(arg, ind, 
                            version=version, mode=mode, colors=colors)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args), ind
    else:
        return gls_expr, ind

def recursive_sm_to_smg(gls_expr):
    if isinstance(gls_expr, gls.SmoothUnion):
        new_args = []
        old_args = gls_expr.get_args()
        arg_1 = recursive_sm_to_smg(old_args[0])
        arg_2 = recursive_sm_to_smg(old_args[1])
        new_args.append(arg_1)
        new_args.append(arg_2)
        dilation_factor = old_args[2]
        new_args.append(dilation_factor)
        new_expr = sls.GeomOnlySmoothUnion(*new_args)
        return new_expr
    else:
        if isinstance(gls_expr, gls.GLFunction):
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr = recursive_sm_to_smg(arg)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args)
        else:
            return gls_expr


def recursive_smg_to_sm(gls_expr):
    if isinstance(gls_expr, sls.GeomOnlySmoothUnion):
        new_args = []
        old_args = gls_expr.get_args()
        arg_1 = recursive_smg_to_sm(old_args[0])
        arg_2 = recursive_smg_to_sm(old_args[1])
        new_args.append(arg_1)
        new_args.append(arg_2)
        dilation_factor = old_args[2]
        new_args.append(dilation_factor)
        new_expr = gls.SmoothUnion(*new_args)
        return new_expr
    else:
        if isinstance(gls_expr, gls.GLFunction):
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr = recursive_smg_to_sm(arg)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args)
        else:
            return gls_expr

def remove_material_from_expression(expression):
    if isinstance(expression, sls.MatSolid):
        return expression.args[0]
    elif isinstance(expression, gls.GLFunction):
        new_args = expression.get_args()
        out_args = []
        for arg in new_args:
            if isinstance(expression, gls.GLFunction):
                out_args.append(remove_material_from_expression(arg))
            else:
                out_args.append(arg)
        return expression.__class__(*out_args)
    else:
        return expression
