from .part_outline import PART_OUTLINE_SHADER
from .basic_third_pass import BASIC_THIRD_PASS_SHADER
from .selection_highlight import SELECTION_HIGHLIGHT_SHADER
from .part_outline_nobg import PART_OUTLINE_NOBG_SHADER
from .dither import DITHER_SHADER
from .all_outline import ALL_OUTLINE_NOBG_SHADER
from .fxaa import fxaa_shader
lookup_map = {
    "part_outline": PART_OUTLINE_SHADER,
    "basic_third_pass": BASIC_THIRD_PASS_SHADER,
    "selection_highlight": SELECTION_HIGHLIGHT_SHADER,
    "part_outline_nobg": PART_OUTLINE_NOBG_SHADER,
    "dither": DITHER_SHADER,
    "all_outline_nobg": ALL_OUTLINE_NOBG_SHADER,
}