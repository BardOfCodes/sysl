import numpy as np
import torch as th
from geolipi.torch_compute.common import EPSILON


def sdf_union(*args):
    """
    Computes the union of multiple SDFs. The union operation finds the minimum SDF value at each point.

    Parameters:
        *args (tuple of torch.Tensor): An arbitrary number of SDF tensors to be united.

    Returns:
        torch.Tensor: The resulting SDF representing the union of the input SDFs.
    """
    # Get sdf by using min and use index for the rest of the channels.
    # sdf = th.amin(th.stack(args, dim=-1), dim=-1)
    x0 = args[0]

    if x0.dim() == 1 or x0.shape[-1] == 1:
        # stack K tensors along a new last dim, then amin along it
        stacked = th.stack(args, dim=-1)            # shape (..., K)
        return th.amin(stacked, dim=-1)

    stacked = th.stack(args, dim=-2)               # shape (..., K, C)

    min_idx = stacked[..., :, 0].argmin(dim=-1)    # shape (...,)

    idx = min_idx.unsqueeze(-1).unsqueeze(-1)      # (..., 1, 1)
    idx = idx.expand(*stacked.shape[:-2], 1, stacked.shape[-1])  # (..., 1, C)
    selected = stacked.gather(dim=-2, index=idx).squeeze(-2)     # (..., C)
    return selected 


def sdf_intersection(*args):
    """
    Computes the intersection of multiple SDFs. The intersection operation finds the maximum SDF value at each point.

    Parameters:
        *args (tuple of torch.Tensor): An arbitrary number of SDF tensors to be intersected.

    Returns:
        torch.Tensor: The resulting SDF representing the intersection of the input SDFs.
    """
    # sdf = th.amax(th.stack(args, dim=-1), dim=-1)
    x0 = args[0]

    if x0.dim() == 1 or x0.shape[-1] == 1:
        # stack K tensors along a new last dim, then amin along it
        stacked = th.stack(args, dim=-1)            # shape (..., K)
        return th.amax(stacked, dim=-1)

    stacked = th.stack(args, dim=-2)               # shape (..., K, C)

    min_idx = stacked[..., :, 0].argmax(dim=-1)    # shape (...,)

    idx = min_idx.unsqueeze(-1).unsqueeze(-1)      # (..., 1, 1)
    idx = idx.expand(*stacked.shape[:-2], 1, stacked.shape[-1])  # (..., 1, C)
    selected = stacked.gather(dim=-2, index=idx).squeeze(-2)     # (..., C)
    return selected 


def sdf_difference(sdf_a, sdf_b):
    """
    Computes the difference between two SDFs (sdf_a - sdf_b).

    Parameters:
        sdf_a (torch.Tensor): The SDF from which the second SDF is subtracted.
        sdf_b (torch.Tensor): The SDF to be subtracted from the first SDF.

    Returns:
        torch.Tensor: The resulting SDF representing the difference between sdf_a and sdf_b.
    """
    # sdf = th.maximum(sdf_a, -sdf_b)
    x0 = sdf_a

    if x0.dim() == 1 or x0.shape[-1] == 1:
        # stack K tensors along a new last dim, then amin along it
        stacked = th.stack([sdf_a, -sdf_b], dim=-1)            # shape (..., K)
        return th.amax(stacked, dim=-1)

    stacked = th.stack([sdf_a, -sdf_b], dim=-2)               # shape (..., K, C)

    min_idx = stacked[..., :, 0].argmax(dim=-1)    # shape (...,)

    idx = min_idx.unsqueeze(-1).unsqueeze(-1)      # (..., 1, 1)
    idx = idx.expand(*stacked.shape[:-2], 1, stacked.shape[-1])  # (..., 1, C)
    selected = stacked.gather(dim=-2, index=idx).squeeze(-2)     # (..., C)
    return selected 


def sdf_switched_difference(sdf_a, sdf_b):
    """
    Computes the difference between two SDFs (sdf_b - sdf_a), opposite of sdf_difference.

    Parameters:
        sdf_a (torch.Tensor): The SDF to be subtracted from the second SDF.
        sdf_b (torch.Tensor): The SDF from which the first SDF is subtracted.

    Returns:
        torch.Tensor: The resulting SDF representing the difference between sdf_b and sdf_a.
    """
    # sdf = th.maximum(sdf_b, -sdf_a)
    output = sdf_difference(sdf_b, sdf_a)
    return output


def sdf_complement(sdf_a):
    """
    Computes the complement of an SDF.

    Parameters:
        sdf_a (torch.Tensor): The SDF for which the complement is calculated.

    Returns:
        torch.Tensor: The resulting SDF representing the complement of sdf_a.
    """

    # sdf = -sdf_a
    x0 = sdf_a

    if x0.dim() == 1 or x0.shape[-1] == 1:
        sdf = -sdf_a
    else:
        new_x = -sdf_a[..., 0:1]
        rest = sdf_a[..., 1:]
        sdf = th.cat([new_x, rest], dim=-1)
    return sdf

def mix(x, y, a):
    return x * (1 - a) + y * a

def sdf_smooth_union(sdf_a, sdf_b, k):
    """
    Computes a smooth union of two SDFs using a smoothing parameter k.

    Parameters:
        sdf_a (torch.Tensor): The first SDF.
        sdf_b (torch.Tensor): The second SDF.
        k (float): The smoothing parameter.

    Returns:
        torch.Tensor: The resulting SDF representing the smooth union of sdf_a and sdf_b.
    """
    # Mix everything smoothly. 
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        var_a, var_b = sdf_a, sdf_b
    else:
        var_a, var_b = sdf_a[..., :1], sdf_b[..., :1]
    h = th.clamp(0.5 + 0.5 * (var_b - var_a) / (k + EPSILON), min=0.0, max=1.0)
    sdf = mix(sdf_b, sdf_a, h) - k * h * (1 - h);
    return sdf

def sdf_geom_only_smooth_union(sdf_a, sdf_b, k):
    """
    Computes a geometric only smooth union of two SDFs using a smoothing parameter k.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        var_a, var_b = sdf_a, sdf_b
        h = th.clamp(0.5 + 0.5 * (var_b - var_a) / (k + EPSILON), min=0.0, max=1.0)
        out = mix(var_b, var_a, h) - k * h * (1 - h);
        
    else:
        var_a, var_b = sdf_a[..., :1], sdf_b[..., :1]
        rest_a = sdf_a[..., 1:]
        rest_b = sdf_b[..., 1:]
        h = th.clamp(0.5 + 0.5 * (var_b - var_a) / (k + EPSILON), min=0.0, max=1.0)
        sdf = mix(var_b, var_a, h) - k * h * (1 - h);
        rest_out = th.where(var_a < var_b, rest_a, rest_b)
        out = th.cat([sdf, rest_out], dim=-1)
    return out

def sdf_smooth_intersection(sdf_a, sdf_b, k):
    """
    Computes a smooth intersection of two SDFs using a smoothing parameter k.

    Parameters:
        sdf_a (torch.Tensor): The first SDF.
        sdf_b (torch.Tensor): The second SDF.
        k (float): The smoothing parameter.

    Returns:
        torch.Tensor: The resulting SDF representing the smooth intersection of sdf_a and sdf_b.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        var_a, var_b = sdf_a, sdf_b
    else:
        var_a, var_b = sdf_a[..., :1], sdf_b[..., :1]
    h = th.clamp(0.5 - 0.5 * (var_b - var_a) / (k + EPSILON), min=0.0, max=1.0)
    sdf = mix(sdf_b, sdf_a, h) + k * h * (1 - h);
    return sdf


def sdf_smooth_difference(sdf_a, sdf_b, k):
    """
    Computes a smooth difference between two SDFs using a smoothing parameter k.

    Parameters:
        sdf_a (torch.Tensor): The first SDF.
        sdf_b (torch.Tensor): The second SDF.
        k (float): The smoothing parameter.

    Returns:
        torch.Tensor: The resulting SDF representing the smooth difference of sdf_a and sdf_b.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        var_a, var_b = sdf_a, sdf_b
    else:
        var_a, var_b = sdf_a[..., :1], sdf_b[..., :1]
    h = th.clamp(0.5 - 0.5 * (var_b - var_a) / (k + EPSILON), min=0.0, max=1.0)
    sdf = mix(sdf_a, -sdf_b, h) + k * h * (1 - h);
    return sdf


def sdf_dilate(sdf_a, k):
    """
    Dilates an SDF by a factor k.

    Parameters:
        sdf_a (torch.Tensor): The SDF to be dilated.
        k (float): The dilation factor.

    Returns:
        torch.Tensor: The resulting SDF after dilation.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        out = sdf_a - k
    else:
        sdf = sdf_a[..., :1] - k
        rest = sdf_a[..., 1:]
        out = th.cat([sdf, rest], dim=-1)
    return out


def sdf_erode(sdf_a, k):
    """
    Erodes an SDF by a factor k.

    Parameters:
        sdf_a (torch.Tensor): The SDF to be eroded.
        k (float): The erosion factor.

    Returns:
        torch.Tensor: The resulting SDF after erosion.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        out = sdf_a + k
    else:
        sdf = sdf_a[..., :1] + k
        rest = sdf_a[..., 1:]
        out = th.cat([sdf, rest], dim=-1)
    return out


def sdf_neg_only_onion(sdf_a, k):
    """
    Creates an "onion" effect on an SDF by subtracting a constant k from the absolute value of the SDF.

    Parameters:
        sdf_a (torch.Tensor): The SDF to be transformed.
        k (float): The onion factor.

    Returns:
        torch.Tensor: The resulting SDF after applying the onion effect.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        alternate = th.abs(sdf_a) - k
        out = th.where(sdf_a <=0, alternate, sdf_a)
    else:
        alternate = th.abs(sdf_a[..., :1]) - k
        out = th.where(sdf_a[..., :1] <=0, alternate, sdf_a)
        rest = sdf_a[..., 1:]
        out = th.cat([out, rest], dim=-1)
    return out


def sdf_onion(sdf_a, k):
    """
    Creates an "onion" effect on an SDF by subtracting a constant k from the absolute value of the SDF.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        out = th.abs(sdf_a) - k
    else:
        out = th.abs(sdf_a[..., :1]) - k
        rest = sdf_a[..., 1:]
        out = th.cat([out, rest], dim=-1)
    return out
    

def sdf_null_op(points):
    """
    A null operation for SDFs.

    Parameters:
        points (torch.Tensor): A tensor representing points in space.

    Returns:
        torch.Tensor: A tensor of zeros with a shape matching the first dimension of the input points.
    """
    return th.zeros_like(points[..., 0]) + EPSILON

def sdf_xor(sdf_a, sdf_b):
    """
    Computes the XOR of two SDFs.
    """
    x0 = sdf_a
    if x0.dim() == 1 or x0.shape[-1] == 1:
        return th.maximum(th.minimum(sdf_a, sdf_b), -th.maximum(sdf_a, sdf_b))
    else:
        out_1 = sdf_union(sdf_a, sdf_b)
        out_2 = sdf_intersection(sdf_a, sdf_b)
        xor = sdf_difference(out_1, out_2)
        return xor