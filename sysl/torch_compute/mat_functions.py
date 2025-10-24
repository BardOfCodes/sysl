import torch as th
import math
def material_v3(points, albedo, roughness, emissive, clearcoat, metallic):
    # ADD here. 
    materials = th.cat([albedo, roughness, emissive, clearcoat, metallic], dim=-1).unsqueeze(0)
    # repeat over the points
    materials = materials.repeat(points.shape[0], 1)
    return materials

def material_v4(points, albedo, emissive, mrc):
    # ADD here. 
    materials = th.cat([albedo, mrc[..., :2]], dim=-1).unsqueeze(0)
    # repeat over the points
    materials = materials.repeat(points.shape[0], 1)
    return materials



def non_emissive_material_v3(points, albedo, roughness, clearcoat, metallic):
    # ADD here. 
    materials = th.cat([albedo, roughness, clearcoat, metallic], dim=-1).unsqueeze(0)
    # repeat over the points
    materials = materials.repeat(points.shape[0], 1)
    return materials


def spherical_rgb_grid_3d(points, colors, texture_name, metallic, roughness):
    # ADD here. 
    
    # Use xyz only
    p = points[:, :3]  # (N, 3)

    # ---- convert to spherical coords ----
    r = th.linalg.norm(p, dim=-1, keepdim=True)  # (N, 1)
    dir = p / (r + 1e-8)                         # normalize

    # θ = atan(z, x), φ = acos(y)
    theta = th.atan2(dir[:, 2], dir[:, 0])       # [-π, π]
    phi = th.acos(th.clamp(dir[:, 1], -1.0, 1.0)) # [0, π]

    # normalize to [0,1]
    u = theta / (2 * math.pi) + 0.5
    v = phi / math.pi

    # stack and clamp
    uv = th.stack([u, v], dim=-1).clamp(0, 1)  # (N, 2)

    # ---- sample the 2D texture ----
    H, W, _ = colors.shape

    # Convert uv to pixel indices
    x = (uv[:, 0] * (W - 1)).long()
    y = (uv[:, 1] * (H - 1)).long()

    # Gather RGB values
    rgb = colors[y, x]  # (N, 3)

    # ---- stack with metallic & roughness ----
    mrc = th.cat([metallic, roughness]).unsqueeze(0).repeat(rgb.shape[0], 1)
    materials = th.cat([rgb, mrc], dim=-1)  # (N, 5)
    return materials