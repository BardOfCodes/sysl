import numpy as np

from geolipi.symbolic.symbol_types import PRIM_TYPE
import sysl.symbolic as sls
import geolipi.symbolic as gls

def recursive_gls_to_sysl(gls_expr, ind=0, version="v4", mode="complex", colors=None):
    if isinstance(gls_expr, gls.GLBase):
        if isinstance(gls_expr, PRIM_TYPE):
            if version == "v1":
                new_expr = sls.MatSolidV1(gls_expr, 
                sls.SMPLMaterial((float(ind),))
                )
            elif version == "v2":
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV2(gls_expr, 
                sls.RGBMaterial(color))
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
                    mat_expr = sls.SMPLMaterialV4(color, (0.0, 1.9))
                else:
                    mat_expr = sls.MaterialV4(color, (0.0, 0.0,0.0), (0.1, 0.9, 0.0,))
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


def recursive_sysl_to_gls(sysl_expr):
    if isinstance(sysl_expr, gls.GLBase):
        if isinstance(sysl_expr, sls.Material):
            return sysl_expr.args[0]
        else:
            new_args = []
            for arg in sysl_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr = recursive_sysl_to_gls(arg)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return sysl_expr.__class__(*new_args)
    else:
        return sysl_expr



def recursive_sm_to_smg(gls_expr):
    if isinstance(gls_expr, gls.SmoothUnion):
        new_args = []
        arg_1 = recursive_sm_to_smg(gls_expr.args[0])
        arg_2 = recursive_sm_to_smg(gls_expr.args[1])
        new_args.append(arg_1)
        new_args.append(arg_2)
        dilation_factor = gls_expr.args[2]
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