# SySL: Symbolic Scene Language

## Oct 18: 
What should SYSL contain?

GeoLIPI is about all things just plain geometry based. 
    Contains the symbolic defs and the python implementation. 

SySL 
* Contains the code to map these expressions to Shader code templates -> Making it feasible to create "Scene Expressions"
* Introduces Material Expressions that can be used to specify materials for different parts. 
    Scene 

* Contains code wrappers to render the scene expressions


# Applications: 

1. Render your implicits without going to meshes for paper ready quality renders. 
2. Check SDF field more easily by slicing the expression online with planes. 
3. Render target Voxels with grid lines cleanly. 
4. Create dynamic scenes for the web simply. 
5. Record optimization and replay. 

## TODO

1. OBB SDF and RGBMR. 
2. OBB 2D Texture Lookup. 
3. Custom SDF function, material function.
4. New shader to have two passes. 
2. New Shader - material based on local position.
3. Split Shader -> Find point + index, and only run the material function in the end. 
4. 

## TODO Oct 15

1. Add the SDF Viewer with AABB and OBB

2. Add Custom SDF function. 

3. Add time uniform variable. 
2. Add a few more important Shader Viewer (edge, transparent Material)
    3. Good Shading with proper light transport (Denoise later)
    4. NPR rendering. 
    5. BG viewer? 

3. Create Some compelling Examples. 

4. Add Readme with Gifs. 

5. Make the



## TODO:



1. Impove the local shader context manager - Currently its all over the place. 

2. Provide the Uint8 encoding option for field. 

3. Stracer4 with local coordinate frame strcuts. 

4. Stracer5 with transparency / translucency. 

6. Add a Tool shading / edges only version.


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Python library for constructing Implicit Scenes with Symbolic Expressions, featuring [TBD] ray-traced rendering and real-time visualization capabilities. 

1. Use [Geolipi]() to describe the 3D Shape. 
2. Use **SySL** to add materials to 3D shapes / general Shader for visuals.
3. Use **SySL** to generate shader code and visualize the output.

## Features

- **Symbolic Expression System**: Define complex 3D scenes using mathematical expressions
- **SDF (Signed Distance Fields) Support**: Built-in support for various primitive shapes and operations
- **Material-Aware Operations**: Advanced material handling with physically-based rendering
- **Real-time Visualization**: Interactive preview of implicit scenes
- **TBD - High-Quality Rendering**: Ray-traced output for production-quality results
- **TBD - Headless Offline Rendiner**: Using Modern GL.
- **Jupyter Notebook Integration**: Interactive development and visualization

## Installation

### From Source

```bash
git clone https://github.com/bardofcodes/sysl.git
cd sysl
pip install -e .
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

```python
import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader_vis.generate_shader_html import create_shader_html, make_jupyter_compatible_html
from IPython.display import display, HTML

# Create basic shapes
sphere = gls.Sphere3D((1.0,))
box = gls.Cuboid3D((2, 0.1, 2,))

# Combine with operations
scene = gls.Translate3D(
    gls.Union(sphere, box),
    (0.5, 0.5, 0)
)

# Assign materials
material = sls.NonEmissiveMaterialV3(
    (1.0, 0.0, 0.0), 
    (1.0,), (1.0,), (0.3,)
)

scene_with_material = sls.MatSolidV3(scene, material)

# Render
shader_code, uniforms = evaluate_to_shader(scene_with_material)

# TO visualize in a browser:
html_code = create_shader_html(shader_code, uniforms, show_controls=True)
with open("test.html", "w") as f:
    f.write(html_code)

# To visualize inline in jupyter notebook:
jupy_wrapper_html = make_jupyter_compatible_html(html_code)
display(HTML(jupy_wrapper_html))
```

## Project Structure

```
sysl/
├── sysl/
│   ├── symbolic/          # Symbolic expression system
│   ├── shader/           # Rendering and shader utilities
│   └── shader_vis/       # Visualization components
├── scripts/
│   └── basic.py          # Basic usage scripts
├── notebooks/
│   └── test.ipynb        # Example notebooks
└── README.md
```

## Documentation

### Core Concepts

1. **Signed Distance Fields (SDFs)**: Mathematical representations of 3D shapes expressions from geolipi.
2. **Symbolic Expressions**: Store shapes as expressions in python, merge and reuse them like variables.
3. **Material-Aware Operations**: Advanced material blending and assignment.
4. **TODO: Ray-Traced Rendering**: High-quality output with realistic lighting

### Examples

Check out the `notebooks/` directory for interactive examples:
- `test.ipynb`: Basic usage and visualization examples

### API Reference

[Coming Soon] - Detailed API documentation

## Goals

1. **Quick Visualization**: Rapidly prototype and visualize complex 3D scenes
2. **High-Quality Rendering**: Generate production-ready ray-traced images
3. **Flexible Material System**: Support for physically-based materials and custom shaders
4. **Performance**: Efficient evaluation of complex implicit functions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- A lot of the code here is derived from Inigo Quilez's work. 
- The real-material shader is derived from Jacquemet Matthieu's code.

## Roadmap

- [ ] Export to standard 3D formats
- [ ] ASMBLR-integration -> Interactive web-based editor
- [ ] Torch-compute head -> Differentiable Rendering pipeline. 

## Support

- **Issues**: [GitHub Issues](https://github.com/bardofcodes/sysl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bardofcodes/sysl/discussions)
- **Email**: [your.email@example.com](mailto:adityaganeshan@gmail.com)

---

**Note**: This project is under active development. APIs may change between versions.
