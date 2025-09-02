import base64
import zlib
import torch as th
import numpy as np
import geolipi.symbolic as gls  
import sysl.symbolic as sls
import sympy as sp
from geolipi.torch_compute import Sketcher

TEXTURE_DTYPE = "float32"
DEFAULT_BOUND_THRESHOLD = 0.02
LOW_PRECISION_RANGE = np.sqrt(0.5)
NBINS = 256

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
        if len(args) > 2:
            bound_threshold = args[2]
        else:
            bound_threshold = DEFAULT_BOUND_THRESHOLD
        b64_data_symbol, dtype, target_shape = extract_voxel_grid(sdf_grid, expr, sketcher)

        return sls.EncodedSDFGrid3D(name, b64_data_symbol, target_shape, dtype, bound_threshold)
    elif isinstance(expr, sls.RGBGrid3D):
        args = expr.args
        rgb_grid = args[0]
        name = args[1].name
        metallic = args[2]
        roughness = args[3]
        if len(args) > 4:
            bound_threshold = args[4]
        else:
            bound_threshold = DEFAULT_BOUND_THRESHOLD   
        b64_data_symbol_rgb, dtype, target_shape = extract_voxel_grid(rgb_grid, expr, sketcher, target_dtype=np.uint8)
        return sls.EncodedRGBGrid3D(name, b64_data_symbol_rgb, target_shape, dtype, metallic, roughness, bound_threshold)
    elif isinstance(expr, sls.LowPrecisionSDFGrid3D):
        args = expr.args
        sdf_grid = args[0]
        name = args[1].name
        if len(args) > 2:
            bound_threshold = args[2]
        else:
            bound_threshold = DEFAULT_BOUND_THRESHOLD
        
        # Process the sdf grid. 
        if isinstance(sdf_grid, sp.Symbol):
            if sdf_grid in expr.lookup_table:
                data = expr.lookup_table[sdf_grid]

                # Original: (N, N, N) float tensor in [-sqrt(3), sqrt(3)]
                data = expr.lookup_table[sdf_grid]
                data = th.clip(data, -LOW_PRECISION_RANGE, LOW_PRECISION_RANGE)
                data_norm = (data + LOW_PRECISION_RANGE) / (2 * LOW_PRECISION_RANGE)  # in [0, 1]

                # Coarse bin (0–255)
                coarse = th.round(data_norm * NBINS).clamp(0, NBINS - 1).to(th.uint8)

                # Fine bin within each coarse bin (0–255)
                bin_size = 1.0 / NBINS
                bin_start = coarse.float() * bin_size
                fine = ((data_norm - bin_start) / bin_size * NBINS).clamp(0, NBINS - 1)
                fine = fine.to(th.uint8)

                # Stack into shape (2, N, N, N) or (2, -1)
                packed = th.stack([coarse, fine], dim=0)  # shape: (2, N, N, N)
                # data = th.clip(data, -LOW_PRECISION_RANGE, LOW_PRECISION_RANGE) / LOW_PRECISION_RANGE
                # data = (data + 1) / 2 * 255
                # data = data.to(th.uint8)
                expr = expr.__class__(coarse, name, bound_threshold)
                sdf_grid = expr.args[0]
                # b64_data_symbol, dtype, target_shape = extract_voxel_grid(data, expr, sketcher, target_dtype=np.uint8)
                # return sls.EncodedLowPrecisionSDFGrid3D(name, b64_data_symbol, target_shape, dtype, bound_threshold)
            else:
                raise ValueError(f"Texture argument of LowPrecisionSDFGrid3D must be a tensor, got {type(sdf_grid)}")
        else:
            raise ValueError(f"Texture argument of LowPrecisionSDFGrid3D must be a tensor, got {type(sdf_grid)}")

        b64_data_symbol, dtype, target_shape = extract_voxel_grid(sdf_grid, expr, sketcher, target_dtype=np.uint8)
        return sls.EncodedLowPrecisionSDFGrid3D(name, b64_data_symbol, target_shape, dtype, bound_threshold)

    elif isinstance(expr, sls.EncodedSDFGrid3D):
        args = expr.args
        assert len(args) in [5], "EncodedSDFGrid3D should have 4 or 5 arguments"
        return expr
    elif isinstance(expr, sls.EncodedRGBGrid3D):
        args = expr.args
        assert len(args) in [7], "EncodedRGBGrid3D should have 6 or 7 arguments"
        return expr
    elif isinstance(expr, sls.EncodedLowPrecisionRGBGrid3D):
        args = expr.args
        assert len(args) in [5], "EncodedLowPrecisionRGBGrid3D should have 4 or 5 arguments"
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
