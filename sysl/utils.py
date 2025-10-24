import numpy as np

from geolipi.symbolic.symbol_types import PRIM_TYPE
import sysl.symbolic as sls
import geolipi.symbolic as gls

def recursive_gls_to_sysl(gls_expr, ind=0, version="v4"):
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
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV4(gls_expr, 
                sls.MaterialV4(color, (0.0, 0.0,0.0), (0.1, 0.9, 0.0,)))
            else:
                raise ValueError(f"Invalid version: {version}")
            ind += 1
            return new_expr, ind
        else:
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr, ind = recursive_gls_to_sysl(arg, ind, version=version)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args), ind
    else:
        return gls_expr, ind