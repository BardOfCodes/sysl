# Extend ZDATA to 300 targets. 
# Find 300 targets from Toy4k
from data_muncher.z_data_hepler import data_pipeline

ind = 0


asset_file = "/sensei-fs-3/users/aganeshan/data/zhiqin/objaverse_selected.txt"
asset_ids = open(asset_file, "r").read().splitlines()
for i in range(2000):
    ind = ind + 1
    print("==== cur ind", ind)
    asset_id = asset_ids[ind].split("/")[1]
    global_mesh = data_pipeline(asset_id)

print(f"Processing {ind} mesh from scratch")

# shape_file = "/sensei-fs-3/users/aganeshan/projects/mpspy/data/data/temp_toy_4k/mesh.obj"
# global_mesh = trimesh.load(shape_file)

# global_mesh = trimesh.load(os.path.join(source_dir, f"{ind}_shape.obj"))
# target_sdf = get_target_cubvh(global_mesh, sketcher_3d)
# target_sdf = target_cleanup(target_sdf, sketcher_3d)
# target_sdf = renorm_target_sdf(target_sdf, sketcher_3d)
# mesh = sdf_to_mesh(target_sdf, sketcher_3d)
# global_mesh.show()