import base64
import zlib
import torch as th
import numpy as np
import geolipi.symbolic as gls  
import cisl.symbolic as csls
import sympy as sp
from geolipi.torch_compute import Sketcher

TEXTURE_DTYPE = "float32"

def from_nested_tuple(obj):
    """Recursively convert nested tuples back to nested lists."""
    if isinstance(obj, tuple):
        return [from_nested_tuple(x) for x in obj]
    else:
        # If it's not a tuple, it's typically a scalar (int/float)
        return obj
def recursive_encode_texture_tensor(expr: gls.GLFunction, sketcher: Sketcher, dtype=TEXTURE_DTYPE):

    if isinstance(expr, gls.SDFGrid3D):
        args = expr.args
        texture_arg = args[0]
        name = args[1].name
        res = sketcher.resolution
        target_shape = (res, res, res)

        if isinstance(texture_arg, sp.Symbol):
            if texture_arg in expr.lookup_table:
                data = expr.lookup_table[texture_arg]
                data = data.cpu().numpy().astype(dtype)
                # shape assumption:
                cur_shape = data.shape
                assert len(cur_shape) == 1, "SDFGrid3D should have 1 dimension"
                assert cur_shape[0] == res ** 3, "SDFGrid3D must be resolution^3"
                data = data.reshape(-1, res, res, res)
                compressed = zlib.compress(data.tobytes())
                b64_data = base64.b64encode(compressed).decode('utf-8')
                b64_data_symbol = sp.Symbol(b64_data)
            else:
                b64_data_symbol = texture_arg
        elif isinstance(texture_arg, sp.Tuple):
            # convert to np array
            # Convert nested tuple back to nested list, then to numpy array
            nested_list = from_nested_tuple(texture_arg)
            data = np.array(nested_list, dtype=dtype)
            cur_shape = data.shape
            assert len(cur_shape) == 1, "SDFGrid3D should have 1 dimension"
            assert cur_shape[0] == res ** 3, "SDFGrid3D must be sketcher resolution^3"
            data = data.reshape(-1, res, res, res)
            compressed = zlib.compress(data.tobytes())
            b64_data = base64.b64encode(compressed).decode('utf-8')
            b64_data_symbol = sp.Symbol(b64_data)
        else:
            raise ValueError(f"Texture argument must be a tensor, got {type(texture_arg)}")

        return csls.EncodedSDFGrid3D(name, b64_data_symbol, target_shape, dtype)
    elif isinstance(expr, csls.EncodedSDFGrid3D):
        args = expr.args
        assert len(args) == 4, "EncodedSDFGrid3D should have 4 arguments"
        return expr
    elif isinstance(expr, gls.GLFunction):
        new_args = []
        for arg in expr.args:
            if isinstance(arg, gls.GLFunction):
                new_arg = recursive_encode_texture_tensor(arg, sketcher)
            else:
                new_arg = arg
            new_args.append(new_arg)
        return expr.__class__(*new_args)
    else:
        raise ValueError(f"Unsupported expression type: {type(expr)}")
