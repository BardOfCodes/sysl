# CISL: Constructive Implicit Scene Language

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
2. Use **CISL** to add materials to 3D shapes.
3. Use **CISL** to generate shader code and visualize the output.

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
git clone https://github.com/bardofcodes/cisl.git
cd cisl
pip install -e .
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

```python
import geolipi.symbolic as gls
import cisl.symbolic as cls
from cisl.shader.evaluate import evaluate_to_shader
from cisl.shader_vis.generate_shader_html import create_shader_html, make_jupyter_compatible_html
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
material = cls.NonEmissiveMaterialV3(
    (1.0, 0.0, 0.0), 
    (1.0,), (1.0,), (0.3,)
)

scene_with_material = cls.MatSolidV3(scene, material)

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
cisl/
├── cisl/
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

- **Issues**: [GitHub Issues](https://github.com/bardofcodes/cisl/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bardofcodes/cisl/discussions)
- **Email**: [your.email@example.com](mailto:adityaganeshan@gmail.com)

---

**Note**: This project is under active development. APIs may change between versions.
