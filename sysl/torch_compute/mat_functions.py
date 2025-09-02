import torch as th
def material_v3(points, albedo, roughness, emissive, clearcoat, metallic):
    # ADD here. 
    materials = th.cat([albedo, roughness, emissive, clearcoat, metallic], dim=-1).unsqueeze(0)
    # repeat over the points
    materials = materials.repeat(points.shape[0], 1)
    return materials


def non_emissive_material_v3(points, albedo, roughness, clearcoat, metallic):
    # ADD here. 
    materials = th.cat([albedo, roughness, clearcoat, metallic], dim=-1).unsqueeze(0)
    # repeat over the points
    materials = materials.repeat(points.shape[0], 1)
    return materials