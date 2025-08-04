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

def extract_voxel_grid(grid_expr, master_expr, sketcher: Sketcher, target_dtype=None):
    res = sketcher.resolution
    target_shape = (-1, res, res, res)
    if isinstance(grid_expr, sp.Symbol):
        if grid_expr in master_expr.lookup_table:
            data = master_expr.lookup_table[grid_expr]
            data = data.cpu().numpy()
        else:
            # It is already encoded? 
            raise ValueError(f"Texture argument must be a tensor or tuple, got {type(grid_expr)}")
    elif isinstance(grid_expr, sp.Tuple):
        # convert to np array
        # Convert nested tuple back to nested list, then to numpy array
        nested_list = from_nested_tuple(grid_expr)
        data = np.array(nested_list)
    else:
        raise ValueError(f"Texture argument must be a tensor or tuple, got {type(grid_expr)}")
    if target_dtype is not None:
        data = data.astype(target_dtype)
    dtype = str(data.dtype)
    cur_shape = data.shape
    assert cur_shape[-1] == res ** 3, "SDFGrid3D must be sketcher resolution^3"
    data = data.reshape(target_shape)
    data = np.transpose(data, (1, 2, 3, 0))
    target_shape = data.shape
    print(f"Compressed data shape: {data.shape}, dtype: {dtype}")
    compressed = zlib.compress(data.tobytes())
    b64_data = base64.b64encode(compressed).decode('utf-8')
    b64_data_symbol = sp.Symbol(b64_data)
    return b64_data_symbol, dtype, target_shape


def recursive_encode_texture_tensor(expr: gls.GLFunction, sketcher: Sketcher, default_dtype=TEXTURE_DTYPE):

    if isinstance(expr, gls.SDFGrid3D):
        args = expr.args
        sdf_grid = args[0]
        name = args[1].name
        b64_data_symbol, dtype, target_shape = extract_voxel_grid(sdf_grid, expr, sketcher)

        return csls.EncodedSDFGrid3D(name, b64_data_symbol, target_shape, dtype)
    elif isinstance(expr, csls.EncodedSDFGrid3D):
        args = expr.args
        assert len(args) in [4, 5], "EncodedSDFGrid3D should have 4 or 5 arguments"
        return expr
    elif isinstance(expr, csls.RGBGrid3D):
        args = expr.args
        rgb_grid = args[0]
        name = args[1].name
        metallic = args[2]
        roughness = args[3]
        b64_data_symbol_rgb, dtype, target_shape = extract_voxel_grid(rgb_grid, expr, sketcher, target_dtype=np.uint8)
        return csls.EncodedRGBGrid3D(name, b64_data_symbol_rgb, target_shape, dtype, metallic, roughness)
    elif isinstance(expr, csls.EncodedRGBGrid3D):
        args = expr.args
        assert len(args) in [6, 7], "EncodedRGBGrid3D should have 6 or 7 arguments"
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
