import numpy as np
from typing import Dict, Any, Tuple
from PIL import Image
import os

# Set up environment for headless rendering
os.environ["PYOPENGL_PLATFORM"] = "egl"
os.environ["MESA_GL_VERSION_OVERRIDE"] = "3.3"
os.environ["MESA_GLSL_VERSION_OVERRIDE"] = "330"
os.environ["GALLIUM_DRIVER"] = "llvmpipe"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

def render_cisl_shader_to_numpy(
    frag_shader_code: str,
    uniforms: Dict[str, Dict[str, Any]],
    size: Tuple[int, int] = (512, 512)
) -> np.ndarray:
    import moderngl
    
    W, H = size
    print(f"Creating framebuffer with size: {W}x{H}")

    # Create moderngl context with fallback options
    try:
        ctx = moderngl.create_standalone_context()
        print("Created standalone context successfully")
    except Exception as e:
        print(f"Failed to create standalone context: {e}")
        # Try with different settings
        try:
            ctx = moderngl.create_standalone_context(require=330)
            print("Created context with OpenGL 3.3 successfully")
        except Exception as e2:
            print(f"Failed to create OpenGL 3.3 context: {e2}")
            # Last resort - try with lower OpenGL version
            try:
                ctx = moderngl.create_standalone_context(require=300)
                print("Created context with OpenGL 3.0 successfully")
            except Exception as e3:
                print(f"Failed to create OpenGL 3.0 context: {e3}")
                raise RuntimeError("Unable to create any OpenGL context")
    
    # Print OpenGL info for debugging
    print(f"OpenGL Version: {ctx.info['GL_VERSION']}")
    print(f"OpenGL Vendor: {ctx.info['GL_VENDOR']}")
    print(f"OpenGL Renderer: {ctx.info['GL_RENDERER']}")

    # Fullscreen quad vertices for triangle strip
    # Triangle strip order: bottom-left, bottom-right, top-left, top-right
    # This creates two triangles covering the entire screen
    vertices = np.array([
        -1.0, -1.0,  # bottom-left
         1.0, -1.0,  # bottom-right
        -1.0,  1.0,  # top-left
         1.0,  1.0,  # top-right
    ], dtype=np.float32)
    vbo = ctx.buffer(vertices)

    # Compile shader program - matching the generated fragment shader
    try:
        prog = ctx.program(
            vertex_shader="""
            #version 300 es
            precision mediump float;
            in vec2 position;
            void main() {
                gl_Position = vec4(position, 0.0, 1.0);
            }
            """,
            fragment_shader=frag_shader_code,
        )
        print("Shader program compiled successfully")
    except Exception as e:
        print(f"Shader compilation error: {e}")
        print("Fragment shader source (first 20 lines):")
        for i, line in enumerate(frag_shader_code.split('\n')[:20]):
            print(f"{i+1:3d}: {line}")
        raise

    # Create vertex array with correct format
    vao = ctx.vertex_array(prog, [(vbo, '2f', 'position')])

    # Set up proper OpenGL state for raymarching
    ctx.enable_only(moderngl.NOTHING)  # Disable all OpenGL features
    ctx.viewport = (0, 0, W, H)  # Ensure viewport matches framebuffer size
    
    print(f"Viewport set to: {ctx.viewport}")

    # Assign uniforms
    uniform_count = 0
    for name, info in uniforms.items():
        if name not in prog:
            print(f"Warning: Uniform '{name}' not found in program")
            continue
        uniform_obj = prog[name]
        if not isinstance(uniform_obj, moderngl.Uniform):
            print(f"Warning: '{name}' is not a Uniform object")
            continue
            
        val = info.get("init_value")
        if val is None:
            print(f"Warning: Uniform '{name}' has no init_value")
            continue
            
        utype = info.get("type")
        print(f"Setting uniform {name} ({utype}) = {val}")

        try:
            if utype == "float":
                uniform_obj.value = float(val)
            elif utype == "int":
                uniform_obj.value = int(val)
            elif utype == "bool":
                uniform_obj.value = bool(val)
            elif utype in ("vec2", "ivec2", "bvec2"):
                uniform_obj.value = tuple(val[:2])
            elif utype in ("vec3", "ivec3", "bvec3"):
                uniform_obj.value = tuple(val[:3])
            elif utype in ("vec4", "ivec4", "bvec4"):
                uniform_obj.value = tuple(val[:4])
            elif utype == "mat4":
                uniform_obj.write(np.array(val, dtype='f4').tobytes())
            uniform_count += 1
        except Exception as e:
            print(f"Error setting uniform {name}: {e}")
    
    print(f"Successfully set {uniform_count} uniforms")
    
    # Ensure resolution uniform matches our framebuffer size
    if 'resolution' in prog:
        try:
            resolution_uniform = prog['resolution']
            if isinstance(resolution_uniform, moderngl.Uniform):
                resolution_uniform.value = (float(W), float(H))
                print(f"Set resolution uniform to ({W}, {H})")
        except Exception as e:
            print(f"Warning: Failed to set resolution uniform: {e}")
    else:
        print("Warning: No resolution uniform found in program")

    # Create framebuffer
    fbo = ctx.simple_framebuffer((W, H))
    fbo.use()
    
    # Ensure viewport is set correctly after framebuffer bind
    ctx.viewport = (0, 0, W, H)
    
    # Clear with black background
    ctx.clear(0.0, 0.0, 0.0, 1.0)
    print("Framebuffer cleared")

    # Render the fullscreen quad
    print("Rendering...")
    vao.render(mode=moderngl.TRIANGLE_STRIP)
    print("Render call completed")

    # Ensure all GPU operations complete
    try:
        ctx.memory_barrier()
        ctx.finish()
        print("GPU synchronization completed")
    except Exception as e:
        print(f"Warning: GPU synchronization failed: {e}")
    
    # Read the framebuffer
    print("Reading framebuffer...")
    data = fbo.read(components=3, alignment=1)
    print(f"Read {len(data)} bytes from framebuffer")
    
    # Convert to PIL Image and flip vertically
    img = Image.frombytes('RGB', (W, H), data).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    print("Converted to PIL Image")
    
    return np.asarray(img)