import base64
import zlib
import torch as th
import numpy as np
import geolipi.symbolic as gls  
import sysl.symbolic as sls
import math
import sympy as sp

import torch.nn.functional as F
from geolipi.torch_compute import Sketcher

TEXTURE_DTYPE = "float32"
DEFAULT_BOUND_THRESHOLD = 0.02
LOW_PRECISION_RANGE = np.sqrt(0.5)
NBINS = 256

def extract_voxel_grid(sdf_grid, sketcher: Sketcher, dtype=None):
    data = sdf_grid#.cpu().numpy()
    res = sketcher.resolution
    target_shape = (-1, res, res, res)
    data = data.reshape(target_shape)
    data = data.permute(1, 2, 3, 0).contiguous()
    print(f"Compressed data shape: {data.shape}")
    data = data.cpu().numpy()
    if dtype is not None:
        data = data.astype(dtype)
    dtype = str(data.dtype)
    target_shape = data.shape
    compressed = zlib.compress(data.tobytes())
    b64_data = base64.b64encode(compressed).decode('utf-8')
    b64_data_symbol = sp.Symbol(b64_data)
    return b64_data_symbol, dtype, target_shape

def extract_voxel_grid_2d(sdf_grid, sketcher: Sketcher, dtype=None):
    data = sdf_grid#.cpu().numpy()
    if sdf_grid.ndim == 2:
        res = sketcher.resolution
        target_shape = (-1, res, res)
    else:
        target_shape = data.shape
    data = data.reshape(target_shape)
    data = data.permute(1, 2, 0).contiguous()
    print(f"Compressed data shape: {data.shape}")
    data = data.cpu().numpy()
    if dtype is not None:
        data = data.astype(dtype)
    dtype = str(data.dtype)
    target_shape = data.shape
    compressed = zlib.compress(data.tobytes())
    b64_data = base64.b64encode(compressed).decode('utf-8')
    b64_data_symbol = sp.Symbol(b64_data)
    return b64_data_symbol, dtype, target_shape

def encde_sdf_low_precision(sdf_grid, expr, sketcher, name, bound_threshold):
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
    new_expr = expr.__class__(coarse, name, bound_threshold)
    new_sdf_grid = new_expr.args[0]
    b64_data_symbol, dtype, target_shape = extract_voxel_grid(new_sdf_grid, new_expr, sketcher, target_dtype=np.uint8)
    encoded_expr = sls.EncodedLowPrecisionSDFGrid3D(name, b64_data_symbol, target_shape, dtype, bound_threshold)
    return encoded_expr


def encode_aabb(sdf_grid, master_expr, sketcher: Sketcher, bound_threshold, name, target_dtype=None, padding_factor=1.1):
    res = sketcher.resolution
    points = sketcher.get_base_coords()
    valid = points[sdf_grid <= bound_threshold]
    min_vals, max_vals = valid.min(dim=0)[0], valid.max(dim=0)[0]
    center = (min_vals + max_vals) / 2
    extent = (max_vals - min_vals) / 2
    center = tuple(center.cpu().numpy().tolist())
    extent = tuple(extent.cpu().numpy().tolist())

    # now accordingly select subset of grid after resizing.
    sdf_grid_reshaped = sdf_grid.reshape(res, res, res)
    valid_mask = (sdf_grid_reshaped <= bound_threshold)
    valid_indices = valid_mask.nonzero()
    min_indices = valid_indices.min(dim=0)[0]
    max_indices = valid_indices.max(dim=0)[0]
    # get min and max indices in each dimension.
    subset_grid = sdf_grid_reshaped[min_indices[0]:max_indices[0], min_indices[1]:max_indices[1], min_indices[2]:max_indices[2]]
    new_shape = subset_grid.shape
    new_shape = (-1, *new_shape)
    subset_data = subset_grid.reshape(new_shape)
    subset_data = subset_data.permute(1, 2, 3, 0).contiguous()
    # Calculate efficiency
    efficiency = (subset_data.numel() / (res ** 3))
    print(f"Compressed data shape: {subset_data.shape}, efficiency: {efficiency}")
    subset_data = subset_data.cpu().numpy()
    target_shape = subset_data.shape
    dtype = str(subset_data.dtype)

    compressed = zlib.compress(subset_data.tobytes())
    b64_subset_data = base64.b64encode(compressed).decode('utf-8')
    b64_subset_data_symbol = sp.Symbol(b64_subset_data)

    encoded_expr = sls.AABBEncodedSDFGrid3D(name, b64_subset_data_symbol, target_shape, dtype, bound_threshold, center, extent)

    return encoded_expr

    


def recursive_encode_texture_tensor(expr: gls.GLFunction, 
                                    sketcher: Sketcher, 
                                    encoding_mode="aabb"):

    if isinstance(expr, gls.SDFGrid3D):

        res = sketcher.resolution
        args = expr.args
        sdf_grid = expr.get_arg(0)
        cur_shape = sdf_grid.shape
        assert cur_shape[-1] == res ** 3, "SDFGrid3D must be sketcher resolution^3"
        name = expr.get_arg(1).name
        bound_threshold = DEFAULT_BOUND_THRESHOLD
        if len(args) > 2:
            bound_threshold = expr.get_arg(2)
            if len(bound_threshold) == 1:
                bound_threshold = float(bound_threshold[0])

        if encoding_mode == "simple":
            b64_data_symbol, dtype, target_shape = extract_voxel_grid(sdf_grid, sketcher)
            encoded_expr = sls.EncodedSDFGrid3D(name, b64_data_symbol, target_shape, dtype, bound_threshold)
        elif encoding_mode == "low_precision":
            encoded_expr = encde_sdf_low_precision(sdf_grid, expr, sketcher, name, bound_threshold)
        elif encoding_mode == "aabb":
            encoded_expr = encode_aabb(sdf_grid, expr, sketcher, bound_threshold, name)
        elif encoding_mode == "obb":
            encoded_expr = encode_obb(sdf_grid, expr, sketcher, bound_threshold, name)
        else:
            raise ValueError(f"Unsupported encoding mode: {encoding_mode}")
        return encoded_expr
    elif isinstance(expr, sls.RGBGrid3D):
        args = expr.args
        rgb_grid = expr.get_arg(0)
        name = expr.get_arg(1).name
        metallic = expr.get_arg(2)
        roughness = expr.get_arg(3)
        bound_threshold = DEFAULT_BOUND_THRESHOLD   
        b64_data_symbol_rgb, dtype, target_shape = extract_voxel_grid(rgb_grid, sketcher, dtype=np.uint8)
        mrc = th.stack([metallic, roughness, th.zeros_like(metallic)], dim=0)
        return sls.EncodedRGBGrid3DV4(name, b64_data_symbol_rgb, target_shape, dtype, mrc, bound_threshold)
        # Process the sdf grid. 
    elif isinstance(expr, sls.SphericalRGBGrid3D):
        args = expr.args
        rgb_grid = expr.get_arg(0)
        name = expr.get_arg(1).name
        metallic = expr.get_arg(2)
        roughness = expr.get_arg(3)
        bound_threshold = DEFAULT_BOUND_THRESHOLD
        b64_data_symbol_rgb, dtype, target_shape = extract_voxel_grid_2d(rgb_grid, sketcher, dtype=np.uint8)
        mrc = th.stack([metallic, roughness, th.zeros_like(metallic)], dim=0)
        return sls.EncodedSphericalRGBGrid3DV4(name, b64_data_symbol_rgb, target_shape, dtype, mrc, bound_threshold)
    elif isinstance(expr, sls.EncodedSDFGrid3D):
        args = expr.args
        assert len(args) in [5], "EncodedSDFGrid3D should have 4 or 5 arguments"
        return expr
    elif isinstance(expr, sls.EncodedRGBGrid3D):
        args = expr.args
        assert len(args) in [7], "EncodedRGBGrid3D should have 6 or 7 arguments"
        return expr

    elif isinstance(expr, gls.GLFunction):
        new_args = []
        for i, arg in enumerate(expr.args):
            if isinstance(arg, gls.GLFunction):
                new_arg = recursive_encode_texture_tensor(arg, sketcher)
            else:
                new_arg = expr.get_arg(i)
            new_args.append(new_arg)
        return expr.__class__(*new_args)
    else:
        raise ValueError(f"Unsupported expression type: {type(expr)}")


def convert_to_atlased_encoded(expression, sketcher):
    # 1 gather all the textures. 
    # assert they are the desired sizes. 
    texture_list = gather_textures(expression)
    texture_list = th.stack(texture_list, dim=0)
    if len(texture_list.shape) == 3:
        mid_shape = texture_list.shape[2]
        b = texture_list.shape[0]
        sqrt_shape = int(math.sqrt(mid_shape))
        assert sqrt_shape ** 2 == mid_shape, "Mid shape must be a perfect square"
        texture_list = texture_list.reshape(b, -1, sqrt_shape, sqrt_shape)
        texture_list = texture_list.permute(0, 2, 3, 1)
    elif len(texture_list) == 4:
        pass
    else: 
        raise ValueError(f"Unsupported shape of textures: {len(texture_list)}")

    atlas, shifts, scales = make_texture_atlas(texture_list)

    # 2. Create the atlased expression.
    new_expression, _, _, _ = _convert_to_atlas_texture(expression, sketcher, atlas, shifts, scales)
    # 3. Return the new expression.
    return new_expression

def gather_textures(expression, texture_list=None):
    if texture_list is None:
        texture_list = []

    if isinstance(expression, gls.GLFunction):
        for arg in expression.args:
            new_texture_list = gather_textures(arg)
            texture_list.extend(new_texture_list)
    if isinstance(expression, sls.SphericalRGBGrid3D):
        texture = expression.get_arg(0)
        texture_list.append(texture)
    return texture_list

def _convert_to_atlas_texture(expr: gls.GLFunction, sketcher,
                                    atlas, shifts, scales, first_pass=True):

    if isinstance(expr, gls.GLFunction):
        new_args = []
        for i, arg in enumerate(expr.args):
            if isinstance(arg, gls.GLFunction):
                new_arg, shifts, scales, first_pass = _convert_to_atlas_texture(arg, sketcher,atlas, shifts, scales, first_pass=first_pass)
            else:
                new_arg = expr.get_arg(i)
            new_args.append(new_arg)
        expr_class = expr.__class__
    if isinstance(expr, sls.SphericalRGBGrid3D):
        args = expr.args
        rgb_grid = expr.get_arg(0)
        name = "texture_atlas_mod" # expr.get_arg(1).name
        metallic = expr.get_arg(2)
        roughness = expr.get_arg(3)
        mrc = th.stack([metallic, roughness, th.zeros_like(metallic)], dim=0)
        bound_threshold = DEFAULT_BOUND_THRESHOLD
        cur_shift = shifts.pop(0)
        cur_scale = scales.pop(0)
        if first_pass:
            rgb_grid = atlas
            expr_class = sls.ESRGB3DShifted
            b64_data_symbol_rgb, dtype, target_shape = extract_voxel_grid_2d(rgb_grid, sketcher, dtype=np.uint8)
            new_args = name, b64_data_symbol_rgb, target_shape, dtype, mrc, bound_threshold, cur_shift, cur_scale
            first_pass = False
        else:
            b64_data_symbol_rgb = "dummy"
            target_shape = (1, 1, 1)
            dtype = "uint8"
            expr_class = sls.ESRGB3DShiftedDummy    
            new_args = name, b64_data_symbol_rgb, target_shape, dtype, mrc, bound_threshold, cur_shift, cur_scale

    return expr_class(*new_args), shifts, scales, first_pass

def make_texture_atlas(textures, gutter=1):
    """
    textures: (B, 128, 128, 3) float tensor in [0,1]
    gutter:   how many toroidal pixels to pad on each side

    Returns:
        atlas (3, K, K)
        shifts (B, 2)
        scales (B, 2)
    """
    B, H, W, C = textures.shape

    # 1️⃣ Toroidal padding
    tex_pad = F.pad(
        textures.permute(0, 3, 1, 2),  # (B,3,H,W)
        (gutter, gutter, gutter, gutter),
        mode="circular",
    )  # -> (B,3,H+2g,W+2g)
    tile = H + 2 * gutter

    # 2️⃣ Grid size (square-ish)
    n_cols = math.ceil(math.sqrt(B))
    n_rows = math.ceil(B / n_cols)
    K = n_cols * tile

    # Prepare empty atlas
    atlas = th.zeros((3, n_rows * tile, n_cols * tile), dtype=tex_pad.dtype).to(tex_pad.device)

    # 3️⃣ Insert tiles + record UV shifts/scales
    shifts = []
    scales = []
    scale_x = W / (n_cols * tile)
    scale_y = H / (n_rows * tile)

    for i in range(B):
        row = i // n_cols
        col = i % n_cols
        y0 = row * tile
        x0 = col * tile
        atlas[:, y0:y0+tile, x0:x0+tile] = tex_pad[i]

        # in normalized [0,1] atlas space
        shift_x = x0 / (n_cols * tile)
        shift_y = y0 / (n_rows * tile)

        shifts.append(th.tensor([shift_x, shift_y]).to(atlas.device))
        scales.append(th.tensor([scale_x, scale_y]).to(atlas.device))

    # shifts = th.tensor(shifts).to(atlas.device)   # (B,2)
    # scales = th.tensor(scales).to(atlas.device)   # (B,2)

    return atlas, shifts, scales

def make_variable_texture_atlas(textures, gutter=2):
    """
    Build a single square atlas from arbitrary-square textures.

    Args:
        textures: list of (C, H, W) tensors, float in [0,1].
        gutter:   int, pixels of toroidal padding on each side.

    Returns:
        atlas: (C, K, K) tensor
        shifts: (N, 2) tensor, per-tile UV offsets in [0,1]
        scales: (N, 2) tensor, per-tile UV scales in [0,1]
    """
    # ------------------------------------------------------------
    # 1. Sort textures largest → smallest (greedy bin pack)
    # ------------------------------------------------------------
    tex_list = [(i, tex) for i, tex in enumerate(textures)]
    tex_list.sort(key=lambda x: x[1].shape[1], reverse=True)
    C = tex_list[0][1].shape[0]

    # Add toroidal padding
    tex_padded = []
    sizes = []
    for _, tex in tex_list:
        tex_pad = F.pad(tex.unsqueeze(0), (gutter, gutter, gutter, gutter), mode="circular")[0]
        tex_padded.append(tex_pad)
        sizes.append(tex_pad.shape[1])  # width==height
    sizes = th.tensor(sizes).to(tex_padded[0].device)

    # ------------------------------------------------------------
    # 2. Simple skyline packer
    # ------------------------------------------------------------
    N = len(tex_padded)
    # start with a conservative atlas size: sum of areas, rounded up to next power of two
    total_area = float(sum(s * s for s in sizes))
    init_size = 2 ** math.ceil(math.log2(math.sqrt(total_area)))
    atlas_size = init_size
    placed = []
    while True:
        atlas = th.zeros((C, atlas_size, atlas_size), dtype=tex_padded[0].dtype)
        skyline = [(0, 0, atlas_size)]  # (x,y,width)
        ok = True
        positions = []

        for i, (tex, s) in enumerate(zip(tex_padded, sizes)):
            # find lowest y where it fits
            placed_ = False
            for j, (x, y, avail_w) in enumerate(skyline):
                if s <= avail_w and y + s <= atlas_size:
                    # place here
                    positions.append((x, y))
                    # update skyline
                    skyline[j] = (x + s, y, avail_w - s)
                    skyline.append((x, y + s, s))
                    placed_ = True
                    break
            if not placed_:
                ok = False
                break
        if ok:
            break
        else:
            atlas_size *= 2  # double and retry

    # ------------------------------------------------------------
    # 3. Paste textures
    # ------------------------------------------------------------
    for (i, (tex, s)), (x, y) in zip(enumerate(tex_padded), positions):
        atlas[:, y:y+s, x:x+s] = tex

    # ------------------------------------------------------------
    # 4. Compute UV transforms
    # ------------------------------------------------------------
    shifts = []
    scales = []
    for (x, y), s in zip(positions, sizes):
        shift_x = x / atlas_size
        shift_y = y / atlas_size
        scale_x = (s - 2 * gutter) / atlas_size
        scale_y = (s - 2 * gutter) / atlas_size
        shifts.append(th.tensor([shift_x + gutter / atlas_size, shift_y + gutter / atlas_size]).to(atlas.device))
        scales.append(th.tensor([scale_x, scale_y]).to(atlas.device))

    # Restore original order

    return atlas, shifts, scales

