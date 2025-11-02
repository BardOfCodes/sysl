
import sysl.symbolic as sls
import geolipi.symbolic as gls
import sysl.torch_compute.mat_combinators as mat_comb
import geolipi.torch_compute.transforms as transform_bank
import sysl.torch_compute.mat_functions as mat_func
import geolipi.symbolic.transforms_3d as sym_t3d
import geolipi.symbolic.transforms_2d as sym_t2d
import geolipi.symbolic.combinators as sym_comb



MODIFIER_MAP = {
    # 2D
    sym_t2d.Translate2D: transform_bank.get_affine_translate_2D,
    sym_t2d.EulerRotate2D: transform_bank.get_affine_rotate_2D,
    sym_t2d.Scale2D: transform_bank.get_affine_scale_2D,
    sym_t2d.Shear2D: transform_bank.get_affine_shear_2D,
    sym_t2d.Affine2D: transform_bank.get_affine_matrix_2D,
    sym_t2d.Distort2D: transform_bank.position_distort,
    sym_t2d.ReflectCoords2D: transform_bank.get_affine_reflection_2D,
    sym_t2d.Dilate2D: mat_comb.sdf_dilate,
    sym_t2d.Erode2D: mat_comb.sdf_erode,
    sym_t2d.Onion2D: mat_comb.sdf_onion,
    # 3D
    sym_t3d.Translate3D: transform_bank.get_affine_translate_3D,
    sym_t3d.EulerRotate3D: transform_bank.get_affine_rotate_euler_3D,
    sym_t3d.AxisAngleRotate3D: transform_bank.get_affine_rotate_axis_angle_3D,
    sym_t3d.RotateMatrix3D: transform_bank.get_affine_rotate_matrix_3D,
    sym_t3d.Scale3D: transform_bank.get_affine_scale_3D,
    sym_t3d.Shear3D: transform_bank.get_affine_shear_3D,
    sym_t3d.Distort3D: transform_bank.position_distort,
    sym_t3d.Twist3D: transform_bank.position_twist,
    sym_t3d.Bend3D: transform_bank.position_cheap_bend,
    sym_t3d.ReflectCoords3D: transform_bank.get_affine_reflection_3D,
    sym_t3d.Dilate3D: mat_comb.sdf_dilate,
    sym_t3d.Erode3D: mat_comb.sdf_erode,
    sym_t3d.Onion3D: mat_comb.sdf_onion,
    sym_t3d.NegOnlyOnion3D: mat_comb.sdf_neg_only_onion,
}


COMBINATOR_MAP = {
    sym_comb.Union: mat_comb.sdf_union,
    sym_comb.Intersection: mat_comb.sdf_intersection,
    sym_comb.Complement: mat_comb.sdf_complement,
    sym_comb.Difference: mat_comb.sdf_difference,
    sym_comb.SwitchedDifference: mat_comb.sdf_switched_difference,
    sym_comb.SmoothUnion: mat_comb.sdf_smooth_union,
    sym_comb.SmoothIntersection: mat_comb.sdf_smooth_intersection,
    sym_comb.SmoothDifference: mat_comb.sdf_smooth_difference,
    sls.GeomOnlySmoothUnion: mat_comb.sdf_geom_only_smooth_union,
    sym_comb.XOR: mat_comb.sdf_xor,
}

MATERIAL_MAP = {
    sls.MaterialV3: mat_func.material_v3,
    sls.MaterialV4: mat_func.material_v4,
    sls.SMPLMaterialV4: mat_func.smpl_material_v4,
    sls.NonEmissiveMaterialV3: mat_func.non_emissive_material_v3,
    sls.SphericalRGBGrid3D: mat_func.spherical_rgb_grid_3d,
}