"""
Material evaluation functions for torch-based SDF computation.

These functions create material property tensors that are broadcast
across all evaluation points.
"""

import torch as th
import math


def material_v1(points, idx):
    """Create index-based material tensor for V1 renderer."""
    materials = th.ones_like(points[:, 0:1], dtype=th.int32) * idx
    return materials


def material_v3(points, albedo, roughness, emissive, clearcoat, metallic):
    """Create full PBR material tensor for V3 renderer."""
    materials = th.cat([albedo, roughness, emissive, clearcoat, metallic], dim=-1).unsqueeze(0)
    materials = materials.repeat(points.shape[0], 1)
    return materials


def material_v4(points, albedo, emissive, mrc):
    """Create simplified PBR material tensor for V4 renderer."""
    materials = th.cat([albedo, mrc[..., :2]], dim=-1).unsqueeze(0)
    materials = materials.repeat(points.shape[0], 1)
    return materials


def smpl_material_v4(points, albedo, mr):
    """Create simple V4 material with albedo and metallic/roughness."""
    materials = th.cat([albedo, mr], dim=-1).unsqueeze(0)
    materials = materials.repeat(points.shape[0], 1)
    return materials


def non_emissive_material_v3(points, albedo, roughness, clearcoat, metallic):
    """Create non-emissive PBR material tensor for V3 renderer."""
    materials = th.cat([albedo, roughness, clearcoat, metallic], dim=-1).unsqueeze(0)
    materials = materials.repeat(points.shape[0], 1)
    return materials


def spherical_rgb_grid_3d(points, colors, texture_name, metallic, roughness):
    """
    Sample RGB colors from a 2D texture using spherical UV mapping.
    
    Converts 3D point positions to spherical coordinates (theta, phi)
    and uses them to sample from a 2D texture.
    
    Args:
        points: (N, 3+) tensor of evaluation points
        colors: (H, W, 3) texture tensor
        texture_name: Name identifier for the texture (unused in computation)
        metallic: Metallic value
        roughness: Roughness value
        
    Returns:
        (N, 5) tensor of [R, G, B, metallic, roughness] per point
    """
    # Use xyz only
    p = points[:, :3]  # (N, 3)

    # Convert to spherical coords
    r = th.linalg.norm(p, dim=-1, keepdim=True)  # (N, 1)
    dir = p / (r + 1e-8)  # normalize

    # θ = atan(z, x), φ = acos(y)
    theta = th.atan2(dir[:, 2], dir[:, 0])  # [-π, π]
    phi = th.acos(th.clamp(dir[:, 1], -1.0, 1.0))  # [0, π]

    # Normalize to [0,1]
    u = theta / (2 * math.pi) + 0.5
    v = phi / math.pi

    # Stack and clamp
    uv = th.stack([u, v], dim=-1).clamp(0, 1)  # (N, 2)

    # Sample the 2D texture
    H, W, _ = colors.shape

    # Convert uv to pixel indices
    x = (uv[:, 0] * (W - 1)).long()
    y = (uv[:, 1] * (H - 1)).long()

    # Gather RGB values
    rgb = colors[y, x]  # (N, 3)

    # Stack with metallic & roughness
    mrc = th.cat([metallic, roughness]).unsqueeze(0).repeat(rgb.shape[0], 1)
    materials = th.cat([rgb, mrc], dim=-1)  # (N, 5)
    return materials
