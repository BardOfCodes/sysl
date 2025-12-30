import geolipi.symbolic as gls
import sysl.symbolic as sls

solid_map = {
    "v1": sls.MatSolidV1,
    "v2": sls.MatSolidV2,
    "v3": sls.MatSolidV3,
    "v4": sls.MatSolidV4,
    "v5": sls.MatSolidV4,
    "v6": sls.MatSolidV2,
}
def convert_solid_types(expression, version="v1"):
    if isinstance(expression, sls.MatSolid):
        args = expression.get_args()
        new_args = []
        for arg in args:
            new_arg = convert_solid_types(arg, version)
            new_args.append(new_arg)
        return solid_map[version](*new_args)
    elif isinstance(expression, gls.GLFunction):
        args = expression.get_args()
        new_args = []
        for arg in args:
            new_arg = convert_solid_types(arg, version)
            new_args.append(new_arg)
        return expression.__class__(*new_args)
    else:
        return expression