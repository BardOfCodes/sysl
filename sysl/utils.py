import numpy as np

from geolipi.symbolic.symbol_types import PRIM_TYPE
import sysl.symbolic as sls
import geolipi.symbolic as gls
from PIL import Image
from typing import List, Literal

def recursive_gls_to_sysl(gls_expr, ind=0, version="v4", mode="complex", colors=None):
    if isinstance(gls_expr, gls.GLBase):
        if isinstance(gls_expr, PRIM_TYPE):
            if version == "v1":
                new_expr = sls.MatSolidV1(gls_expr, 
                sls.MaterialV1((float(ind),))
                )
            elif version == "v2":
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV2(gls_expr, 
                sls.MaterialV2(color))
            elif version == "v3":
                color = tuple(np.random.rand(3).tolist())
                new_expr = sls.MatSolidV3(gls_expr, 
                sls.NonEmissiveMaterialV3(color, (0.0,), (0.9,), (0.9,)))
            elif version == "v4":
                if colors is None:
                    color = tuple(np.random.rand(3).tolist())
                else:
                    color = colors[ind]
                if mode == "simple":
                    mat_expr = sls.MaterialV1V4(color, (0.0, 1.9))
                else:
                    mat_expr = sls.MaterialV4(color, (0.0, 0.0,0.0), (0.5, 0.2, 0.8,))
                new_expr = sls.MatSolidV4(gls_expr, mat_expr)
            else:
                raise ValueError(f"Invalid version: {version}")
            ind += 1
            return new_expr, ind
        else:
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr, ind = recursive_gls_to_sysl(arg, ind, 
                            version=version, mode=mode, colors=colors)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args), ind
    else:
        return gls_expr, ind

def recursive_sm_to_smg(gls_expr):
    if isinstance(gls_expr, gls.SmoothUnion):
        new_args = []
        arg_1 = recursive_sm_to_smg(gls_expr.args[0])
        arg_2 = recursive_sm_to_smg(gls_expr.args[1])
        new_args.append(arg_1)
        new_args.append(arg_2)
        dilation_factor = gls_expr.args[2]
        new_args.append(dilation_factor)
        new_expr = sls.GeomOnlySmoothUnion(*new_args)
        return new_expr
    else:
        if isinstance(gls_expr, gls.GLFunction):
            new_args = []
            for arg in gls_expr.args:
                if isinstance(arg, gls.GLBase):
                    out_expr = recursive_sm_to_smg(arg)
                    new_args.append(out_expr)
                else:
                    new_args.append(arg)
            return gls_expr.__class__(*new_args)
        else:
            return gls_expr


def frames_to_animation(
    frames: List[Image.Image],
    output_path: str,
    fps: int = 10,
    format: Literal['gif', 'webp', 'mp4'] = 'gif',
    mp4_quality: Literal['lossless', 'high', 'medium'] = 'high',
) -> str:
    """
    Takes a sequence of PIL Image frames and saves them as an animated GIF, WebP, or MP4.

    Parameters:
    - frames (List[Image.Image]): List of PIL Image frames.
    - output_path (str): Path where the animation file will be saved.
    - fps (int): Frames per second for the animation. Default is 10.
    - format (str): Output format: 'gif', 'webp', or 'mp4'. Default is 'gif'.
    - mp4_quality (str): Quality for MP4 encoding. Only used when format='mp4'.
        - 'lossless': No compression (CRF 0, very large files)
        - 'high': Visually lossless (CRF 17, recommended for quality)
        - 'medium': Good quality with smaller file size (CRF 23)

    Returns:
    - str: The path to the saved animation file.
    """
    if not frames:
        raise ValueError("No frames provided")
    
    # Ensure all frames have the same size (resize to first frame's size)
    base_size = frames[0].size
    frames = [f.resize(base_size, Image.Resampling.LANCZOS) if f.size != base_size else f 
              for f in frames]
    
    # Calculate duration in milliseconds
    duration_ms = int(1000 / fps)
    
    # Ensure correct file extension
    if not output_path.lower().endswith(f'.{format}'):
        output_path = f"{output_path}.{format}"
    
    # Save animation
    if format == 'gif':
        # Convert RGBA to P mode for better GIF support
        frames_p = [f.convert('P', palette=Image.Palette.ADAPTIVE, colors=256) for f in frames]
        frames_p[0].save(
            output_path,
            save_all=True,
            append_images=frames_p[1:],
            duration=duration_ms,
            loop=0,  # 0 = infinite loop
            optimize=True
        )
    elif format == 'webp':
        frames[0].save(
            output_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            lossless=True
        )
    elif format == 'mp4':
        import imageio.v3 as iio
        import numpy as np
        
        # CRF values: 0 = lossless, 17 = visually lossless, 23 = default
        crf_map = {'lossless': 0, 'high': 17, 'medium': 23}
        crf = crf_map.get(mp4_quality, 17)
        
        # Convert PIL Images to numpy arrays (RGB, not RGBA for MP4)
        frame_arrays = [np.array(f.convert('RGB')) for f in frames]
        
        # Build ffmpeg output parameters for high quality
        if mp4_quality == 'lossless':
            # Use FFV1 codec for truly lossless, or x264 with crf=0
            codec = 'libx264'
            output_params = [
                '-crf', '0',
                '-preset', 'veryslow',
                '-pix_fmt', 'yuv444p',  # No chroma subsampling for lossless
            ]
        else:
            codec = 'libx264'
            output_params = [
                '-crf', str(crf),
                '-preset', 'slow',  # Better compression at cost of encoding time
                '-pix_fmt', 'yuv420p',  # Standard compatibility
                '-profile:v', 'high',
                '-level', '4.2',
            ]
        
        iio.imwrite(
            output_path,
            frame_arrays,
            fps=fps,
            codec=codec,
            output_params=output_params,
        )
    
    return output_path
