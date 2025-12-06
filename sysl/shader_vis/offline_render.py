"""
Offline Renderer for SySL Shaders using ModernGL.

Provides two main functions:
1. render_single_pass() - Renders output from evaluate_to_shader()
2. render_multipass() - Renders output from evaluate_to_multipass_shader()
"""

import re
import os
import base64
import zlib
import numpy as np
from typing import Dict, Any, Tuple, List, Optional
from PIL import Image

# Environment setup for headless rendering (must be before moderngl import)
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
os.environ.setdefault("MESA_GL_VERSION_OVERRIDE", "3.3")
os.environ.setdefault("MESA_GLSL_VERSION_OVERRIDE", "330")

import moderngl

# =============================================================================
# GLSL Conversion Utilities
# =============================================================================

def convert_es_to_desktop(shader_code: str) -> str:
    """
    Convert GLSL ES 3.0 shader to GLSL 3.30 core for desktop OpenGL.
    
    Changes:
    - #version 300 es -> #version 330 core
    - Removes precision qualifiers (not needed in desktop GL)
    """
    # Replace version directive
    code = shader_code.replace("#version 300 es", "#version 330 core")
    
    # Remove precision statements
    code = re.sub(r'precision\s+\w+\s+\w+;\s*\n?', '', code)
    
    return code


# =============================================================================
# Texture Utilities
# =============================================================================

def decode_texture_data(texture_info: Dict[str, Any]) -> np.ndarray:
    """
    Decode base64+zlib compressed texture data to numpy array.
    
    Args:
        texture_info: Dict with keys:
            - data_b64: base64-encoded zlib-compressed data
            - shape: tuple/list of dimensions
            - dtype: 'float32' or 'uint8'
    
    Returns:
        numpy array with the texture data
    """
    b64_data = texture_info['data_b64']
    shape = tuple(texture_info['shape'])
    dtype = texture_info['dtype']
    
    # Decode base64 -> decompress zlib -> convert to numpy
    compressed = base64.b64decode(b64_data)
    raw_bytes = zlib.decompress(compressed)
    data = np.frombuffer(raw_bytes, dtype=dtype)
    
    return data.reshape(shape)


def create_texture(ctx: moderngl.Context, 
                   texture_info: Dict[str, Any]) -> moderngl.Texture:
    """
    Create a ModernGL texture from texture info dict.
    
    Args:
        ctx: ModernGL context
        texture_info: Dict with name, data_b64, shape, dtype
        
    Returns:
        ModernGL Texture object (2D or 3D based on shape)
    """
    data = decode_texture_data(texture_info)
    shape = data.shape
    dtype = texture_info['dtype']
    
    # Determine texture type based on shape dimensions
    if len(shape) == 3:
        # 2D texture: (H, W, C)
        return _create_texture_2d(ctx, data, dtype)
    elif len(shape) == 4:
        # 3D texture: (D, H, W, C)
        return _create_texture_3d(ctx, data, dtype)
    else:
        raise ValueError(f"Unsupported texture shape: {shape}")


def _create_texture_2d(ctx: moderngl.Context, 
                       data: np.ndarray, 
                       dtype: str) -> moderngl.Texture:
    """Create a 2D texture from numpy data (H, W, C)."""
    H, W, C = data.shape
    
    # Ensure contiguous and correct dtype
    if dtype == 'uint8':
        data = np.ascontiguousarray(data, dtype=np.uint8)
        components = C
        texture = ctx.texture((W, H), components, data.tobytes(), dtype='f1')
    elif dtype == 'float32':
        data = np.ascontiguousarray(data, dtype=np.float32)
        components = C
        texture = ctx.texture((W, H), components, data.tobytes(), dtype='f4')
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
    
    # Set texture parameters
    texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
    texture.repeat_x = True
    texture.repeat_y = True
    
    return texture


def _create_texture_3d(ctx: moderngl.Context, 
                       data: np.ndarray, 
                       dtype: str) -> moderngl.Texture3D:
    """Create a 3D texture from numpy data (D, H, W, C)."""
    D, H, W, C = data.shape
    
    # Ensure contiguous and correct dtype
    if dtype == 'uint8':
        data = np.ascontiguousarray(data, dtype=np.uint8)
        texture = ctx.texture3d((W, H, D), C, data.tobytes(), dtype='f1')
    elif dtype == 'float32':
        data = np.ascontiguousarray(data, dtype=np.float32)
        texture = ctx.texture3d((W, H, D), C, data.tobytes(), dtype='f4')
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
    
    # Set texture parameters
    texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
    texture.repeat_x = True
    texture.repeat_y = True
    texture.repeat_z = True
    
    return texture


# =============================================================================
# Uniform Utilities
# =============================================================================

def set_uniform(prog: moderngl.Program, 
                name: str, 
                info: Dict[str, Any]) -> bool:
    """
    Set a uniform value in the shader program.
    
    Args:
        prog: ModernGL program
        name: Uniform name
        info: Dict with 'type' and 'init_value'
        
    Returns:
        True if uniform was set, False if not found or failed
    """
    if name not in prog:
        return False
    
    uniform = prog[name]
    if not isinstance(uniform, moderngl.Uniform):
        return False
    
    val = info.get("init_value")
    if val is None:
        return False
    
    utype = info.get("type", "float")
    
    try:
        if utype == "float":
            uniform.value = float(val) if not isinstance(val, (list, tuple)) else float(val[0]) if len(val) == 1 else float(val)
        elif utype == "int":
            uniform.value = int(val) if not isinstance(val, (list, tuple)) else int(val[0])
        elif utype == "bool":
            if isinstance(val, str):
                uniform.value = val.lower() == "true"
            else:
                uniform.value = bool(val)
        elif utype == "vec2":
            uniform.value = tuple(float(x) for x in val[:2])
        elif utype == "vec3":
            uniform.value = tuple(float(x) for x in val[:3])
        elif utype == "vec4":
            uniform.value = tuple(float(x) for x in val[:4])
        elif utype == "mat4":
            uniform.write(np.array(val, dtype='f4').tobytes())
        elif utype == "uniform_buffer":
            # Skip UBOs in regular uniform setting
            return False
        else:
            return False
        return True
    except Exception:
        return False


# =============================================================================
# Vertex Shader (shared)
# =============================================================================

VERTEX_SHADER = """
#version 330 core
in vec2 position;
void main() {
    gl_Position = vec4(position, 0.0, 1.0);
}
"""

# Fullscreen quad vertices (triangle strip)
FULLSCREEN_QUAD = np.array([
    -1.0, -1.0,  # bottom-left
     1.0, -1.0,  # bottom-right
    -1.0,  1.0,  # top-left
     1.0,  1.0,  # top-right
], dtype=np.float32)


# =============================================================================
# Single-Pass Renderer
# =============================================================================

def render_single_pass(
    shader_code: str,
    uniforms: Dict[str, Dict[str, Any]],
    textures: Dict[str, Dict[str, Any]],
    size: Tuple[int, int] = (512, 512)
) -> np.ndarray:
    """
    Render a single-pass shader to an image.
    
    This function takes the output of evaluate_to_shader() and renders it.
    
    Args:
        shader_code: Fragment shader code (GLSL ES 3.0 format)
        uniforms: Dict of uniform name -> {type, init_value, ...}
        textures: Dict of texture name -> {data_b64, shape, dtype, ...}
        size: Output image size (width, height)
        
    Returns:
        numpy array of shape (H, W, 3) with RGB image data (uint8)
    """
    W, H = size
    
    # Create context
    ctx = _create_context()
    
    try:
        # Convert shader to desktop GLSL
        frag_shader = convert_es_to_desktop(shader_code)
        
        # Compile program
        prog = ctx.program(
            vertex_shader=VERTEX_SHADER,
            fragment_shader=frag_shader
        )
        
        # Create vertex buffer and VAO
        vbo = ctx.buffer(FULLSCREEN_QUAD)
        vao = ctx.vertex_array(prog, [(vbo, '2f', 'position')])
        
        # Set uniforms
        for name, info in uniforms.items():
            set_uniform(prog, name, info)
        
        # Override resolution to match our output size
        if 'resolution' in prog:
            prog['resolution'].value = (float(W), float(H))
        
        # Create and bind textures
        texture_units = {}
        unit_idx = 0
        for tex_name, tex_info in textures.items():
            if tex_name in prog:
                tex = create_texture(ctx, tex_info)
                tex.use(location=unit_idx)
                prog[tex_name].value = unit_idx
                texture_units[tex_name] = (tex, unit_idx)
                unit_idx += 1
        
        # Create framebuffer
        fbo = ctx.simple_framebuffer((W, H))
        fbo.use()
        
        # Setup viewport and clear
        ctx.viewport = (0, 0, W, H)
        ctx.enable_only(moderngl.NOTHING)
        ctx.clear(0.0, 0.0, 0.0, 1.0)
        
        # Render
        vao.render(mode=moderngl.TRIANGLE_STRIP)
        
        # Read result
        ctx.finish()
        data = fbo.read(components=3, alignment=1)
        
        # Convert to numpy and flip Y
        img = Image.frombytes('RGB', (W, H), data)
        img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        return np.asarray(img)
        
    finally:
        ctx.release()


# =============================================================================
# Multi-Pass Renderer
# =============================================================================

def render_multipass(
    passes: List[Dict[str, Any]],
    size: Optional[Tuple[int, int]] = None
) -> np.ndarray:
    """
    Render a multi-pass shader pipeline to an image.
    
    This function takes the output of evaluate_to_multipass_shader() and renders it.
    
    Args:
        passes: List of pass definitions, each containing:
            - shader_code: Fragment shader code
            - uniforms: Dict of uniforms
            - textures: Dict of textures
            - input_FBOs: List of input FBO specs
            - output_FBO: Output FBO spec or dict with 'name': 'image'
        size: Optional output size override. If None, uses FBO sizes from passes.
        
    Returns:
        numpy array of shape (H, W, 3) with RGB image data (uint8)
    """
    # Create context
    ctx = _create_context()
    
    try:
        # Determine final output size
        if size is None:
            # Find the pass that outputs to 'image' and use its output size
            for p in reversed(passes):
                out = p['output_FBO']
                if isinstance(out, dict) and out.get('name') == 'image':
                    size = (out['width'], out['height'])
                    break
            if size is None:
                size = (512, 512)
        
        W, H = size
        
        # Create VBO for fullscreen quad (shared across all passes)
        vbo = ctx.buffer(FULLSCREEN_QUAD)
        
        # FBO registry: name -> (texture, fbo)
        fbo_registry: Dict[str, Tuple[moderngl.Texture, moderngl.Framebuffer]] = {}
        
        # Texture registry for user textures (from shader)
        user_textures: Dict[str, moderngl.Texture] = {}
        
        # Process each pass
        final_image = None
        
        for pass_idx, pass_def in enumerate(passes):
            shader_code = pass_def['shader_code']
            uniforms = pass_def.get('uniforms', {})
            textures = pass_def.get('textures', {})
            input_fbos = pass_def.get('input_FBOs', [])
            output_fbo = pass_def['output_FBO']
            
            # Convert shader to desktop GLSL
            frag_shader = convert_es_to_desktop(shader_code)
            
            # Compile program for this pass
            prog = ctx.program(
                vertex_shader=VERTEX_SHADER,
                fragment_shader=frag_shader
            )
            
            # Create VAO for this pass
            vao = ctx.vertex_array(prog, [(vbo, '2f', 'position')])
            
            # Set uniforms
            for name, info in uniforms.items():
                set_uniform(prog, name, info)
            
            # Determine output size for this pass
            if isinstance(output_fbo, dict):
                out_w = output_fbo.get('width', W)
                out_h = output_fbo.get('height', H)
                out_name = output_fbo.get('name', 'image')
            else:
                out_w, out_h = W, H
                out_name = 'image'
            
            # Override resolution uniform if present
            if 'resolution' in prog:
                prog['resolution'].value = (float(out_w), float(out_h))
            
            # Bind input FBOs as textures
            texture_unit = 0
            for input_spec in input_fbos:
                if isinstance(input_spec, dict):
                    fbo_name = input_spec['name']
                else:
                    fbo_name = input_spec
                
                if fbo_name in fbo_registry:
                    tex, _ = fbo_registry[fbo_name]
                    if fbo_name in prog:
                        tex.use(location=texture_unit)
                        prog[fbo_name].value = texture_unit
                        texture_unit += 1
            
            # Bind user textures
            for tex_name, tex_info in textures.items():
                if tex_name not in user_textures:
                    user_textures[tex_name] = create_texture(ctx, tex_info)
                if tex_name in prog:
                    user_textures[tex_name].use(location=texture_unit)
                    prog[tex_name].value = texture_unit
                    texture_unit += 1
            
            # Create or get output FBO
            if out_name == 'image':
                # Render to final framebuffer
                fbo = ctx.simple_framebuffer((out_w, out_h))
            else:
                # Create intermediate FBO if not exists
                if out_name not in fbo_registry:
                    fbo_type = output_fbo.get('type', 'vec4') if isinstance(output_fbo, dict) else 'vec4'
                    tex, fbo = _create_fbo(ctx, out_w, out_h, fbo_type)
                    fbo_registry[out_name] = (tex, fbo)
                else:
                    _, fbo = fbo_registry[out_name]
            
            # Render this pass
            fbo.use()
            ctx.viewport = (0, 0, out_w, out_h)
            ctx.enable_only(moderngl.NOTHING)
            ctx.clear(0.0, 0.0, 0.0, 1.0)
            vao.render(mode=moderngl.TRIANGLE_STRIP)
            
            # If this is final pass, save reference
            if out_name == 'image':
                ctx.finish()
                data = fbo.read(components=3, alignment=1)
                img = Image.frombytes('RGB', (out_w, out_h), data)
                img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                final_image = np.asarray(img)
        
        if final_image is None:
            raise RuntimeError("No pass outputs to 'image'")
        
        return final_image
        
    finally:
        ctx.release()


# =============================================================================
# Helper Functions
# =============================================================================

def _create_context() -> moderngl.Context:
    """Create a ModernGL standalone context with fallbacks."""
    try:
        return moderngl.create_standalone_context(require=330)
    except Exception:
        try:
            return moderngl.create_standalone_context()
        except Exception as e:
            raise RuntimeError(f"Failed to create OpenGL context: {e}")


def _create_fbo(ctx: moderngl.Context, 
                width: int, 
                height: int, 
                fbo_type: str) -> Tuple[moderngl.Texture, moderngl.Framebuffer]:
    """
    Create an FBO with appropriate format.
    
    Args:
        ctx: ModernGL context
        width: FBO width
        height: FBO height
        fbo_type: 'float', 'vec2', 'vec3', or 'vec4'
        
    Returns:
        Tuple of (texture, framebuffer)
    """
    type_to_components = {
        'float': 1,
        'vec2': 2,
        'vec3': 3,
        'vec4': 4,
    }
    
    components = type_to_components.get(fbo_type, 4)
    
    # Create floating-point texture
    texture = ctx.texture((width, height), components, dtype='f4')
    texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
    
    # Create framebuffer
    fbo = ctx.framebuffer(color_attachments=[texture])
    
    return texture, fbo
