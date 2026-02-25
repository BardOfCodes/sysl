# SySL: Symbolic Scene Language

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyPI - Version](https://img.shields.io/pypi/v/sysl.svg)](https://pypi.org/project/sysl/)

**SySL** extends [GeoLiPI](https://github.com/bardofcodes/geolipi) by adding material-related symbols to geometric expressions. It provides an shader evaluation pipeline that converts symbolic scene expressions into GLSL shader code, enabling sphere-traced rendering and real-time interactive WebGL visualization.

<p align="center">
  <img src="assets/hero.jpg" alt="SySL Rendering Examples">
</p>

## Applications

### 1. Paper-Ready Renders
Generate high-quality renders of primitive assemblies without mesh conversion. I used this system for rendering primitive assemblies for paper figures in a recent work [Residual Primitive Fitting of 3D Shapes with SuperFrusta](https://arxiv.org/abs/2512.09201). 

<p align="center">
  <img src="assets/paper_fig.jpg" alt="Primitive Assembly Render">
</p>

### 2. Interactive Web Visualization
Create standalone HTML files for interactive 3D visualization. Useful for debugging, or stand alone apps. 

<p align="center">
  <img src="assets/interaction.gif" alt="Interactive Demo" width="400">
</p>

### 3. Interactive Assembly editor. 

Create an standalone app for editing *textured* (deployable) primitive assemblies. 

<p align="center">
  <img src="assets/editing.gif" alt="Editing Demo" width="400">
</p>

### 4. Animation Sequences
Generate frame-by-frame renders for animations.

<p align="center">
  <img src="assets/animation.gif" alt="Editing Demo" width="400">
</p>

## Features

- **Material Expressions**: Define materials with albedo, metallic, roughness, emissive properties
- **Multiple Render Modes**: From simple Inigo-style to PBR-quality Matthieu-style rendering
- **Shader Code Generation**: Convert symbolic expressions to optimized GLSL
- **Interactive Visualization**: Generate standalone HTML files with WebGL rendering
- **Jupyter Integration**: Inline visualization in notebooks
- **Offline Rendering**: Headless rendering via ModernGL (optional)
- **Image Effects (IMFX)**: Post-processing effects like outlines, dithering, anti-aliasing
## Installation

### From PyPI (recommended)

SySL is published on PyPI. For most users this is the easiest way to get started:

```bash
pip install sysl
```

You will also need [GeoLiPI](https://github.com/bardofcodes/geolipi), which provides the
geometric expression system that SySL builds on:

```bash
pip install geolipi
```

### From source

```bash
git clone https://github.com/bardofcodes/sysl.git
cd sysl

# Install dependencies
pip install -r requirements.txt

# Editable install for development
pip install -e .
```

## Quick Start

### Basic example

```python
import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader import DEFAULT_SETTINGS, RenderMode, evaluate_to_shader
from sysl.shader_runtime import create_shader_html

# Create simple geometry
geometry = gls.Sphere3D((1.0,))

# Define a basic V4 material (albedo, emissive, mrc)
material = sls.MaterialV4(
    (1.0, 0.2, 0.1),  # albedo
    (0.0, 0.0, 0.0),  # emissive
    (0.5, 0.3, 0.0),  # metallic / roughness / clearcoat
)
scene = sls.MatSolidV4(geometry, material)

# Choose a render mode and settings
settings = dict(DEFAULT_SETTINGS)
settings["render_mode"] = RenderMode.V4

# Generate shader
shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)

# Generate HTML viewer
html_code = create_shader_html(
    shader_code,
    uniforms,
    textures,
    show_controls=True,
)

# Save to a file and serve via a simple HTTP server
with open("sysl_example.html", "w") as f:
    f.write(html_code)
```

### Jupyter Notebook

```python
from IPython.display import HTML, display
from sysl.shader_runtime.generate_shader_html import make_jupyter_compatible_html

wrapped = make_jupyter_compatible_html(html_code)
display(HTML(wrapped))
```

### Jupyter Notebook

See `notebooks/` for examples.

## Render Modes

SySL supports multiple rendering pipelines, each with different visual characteristics:

| Mode | Description | Use Case | Source|
|------|-------------|----------|----------|
| **V1** | Simple Inigo-style | Fast preview, basic shading |[ShaderToy](https://www.shadertoy.com/view/Xds3zN)|
| **V2** | Inigo + Color | Simple colored renders | [ShaderToy](https://www.shadertoy.com/view/Xds3zN)|
| **V3** | J. Matthieu-style | Material functions with (p, n) |[ShaderToy](https://www.shadertoy.com/view/3tKfDG)|
| **V4** | Adapted Matthieu | Local materials + mixing (default) |[ShaderToy](https://www.shadertoy.com/view/3tKfDG)|
| **V5** | Toon Shader | NPR stylized rendering |[ShaderToy](https://www.shadertoy.com/view/ll33Wn)|
| **V6** | Dithered Shader | V2 + Dithering + outline |[ShaderToy](https://www.shadertoy.com/view/33BXW3)|

### Selecting a render mode

You can select different render modes via the `RenderMode` enum:

```python
from sysl.shader import DEFAULT_SETTINGS, RenderMode, evaluate_to_shader

settings = dict(DEFAULT_SETTINGS)
settings["render_mode"] = RenderMode.V4  # v1–v6

shader_code, uniforms, textures = evaluate_to_shader(expression, settings=settings)
```

## API overview

The main entry points most users interact with are:

- `sysl.evaluate_to_shader(expression, mode=\"singlepass\" | \"multipass\", settings=None)`
- `sysl.create_shader_html(shader_code, uniforms, textures, show_controls=False, ...)`
- `sysl.symbolic` – symbolic building blocks (materials, combinators, fields, etc.)

See the examples in `examples/` and `notebooks/` for more complete workflows.

## Image Effects (IMFX)

Post-processing effects available in multi-pass rendering:

- **Outlines**: Edge detection for shape boundaries

- **Selection Highlight**: Highlight specific primitives (used in editing mode)
- **Dithering**: Stylized dither patterns

- **FXAA**: Fast approximate anti-aliasing

## Project Structure

```
sysl/
├── sysl/
│   ├── symbolic/        # Material symbols and MatSolid definitions
│   ├── shader/          # Expression → GLSL shader conversion
│   │   ├── shader_templates/  # GLSL template modules
│   │   └── utils/       # UBO packing, texture encoding
│   ├── shader_runtime/  # HTML generation, offline rendering
│   └── torch_compute/   # PyTorch-based evaluation (optional)
├── scripts/             # Example scripts
├── notebooks/           # Jupyter notebook examples
├── tests/               # Pytest-based test suite
└── assets/              # Images for documentation
```

## Acknowledgments

This project builds heavily on the excellent work from the ShaderToy community:

- **Inigo Quilez** ([iquilezles.org](https://iquilezles.org/)) - SDF primitives, combinators, and basic sphere tracing / rendering techniques
- **Matthieu Jacquemet** ([ShaderToy](https://www.shadertoy.com/view/3tKfDG)) - A material system + alternate rendering system.

> **Important License Note**: The MIT license applies to the Python code in this repository. The GLSL shader templates are derived from ShaderToy contributions and retain their original authors' licensing terms. Please respect the original authors' licenses when using generated shader code.

## Citation

If you use SySL in your research, please cite:

```bibtex
@misc{ganeshan2025superfit,
  title={Residual Primitive Fitting of 3D Shapes with SuperFrusta}, 
  author={Aditya Ganeshan and Matheus Gadelha and Thibault Groueix and Zhiqin Chen and Siddhartha Chaudhuri and Vladimir Kim and Wang Yifan and Daniel Ritchie},
  year={2025},
  eprint={2512.09201},
  archivePrefix={arXiv},
  primaryClass={cs.GR},
  url={https://arxiv.org/abs/2512.09201}, 
}

@article{ganeshan2025migumi,
  author = {Ganeshan, Aditya and Fleischer, Kurt and Jakob, Wenzel and Shamir, Ariel and Ritchie, Daniel and Igarashi, Takeo and Larsson, Maria},
  title = {MiGumi: Making Tightly Coupled Integral Joints Millable},
  year = {2025},
  publisher = {Association for Computing Machinery},
  volume = {44},
  number = {6},
  url = {https://doi.org/10.1145/3763304},
  doi = {10.1145/3763304},
  journal = {ACM Trans. Graph.},
  articleno = {193},
}
```

## Known Limitations & Future Work

- **Code Duplication**: Shader templates have some duplication that could be refactored
- **Complex Scenes**: Very complex scenes may benefit from cone tracing (not yet implemented)
- **WebGPU**: Currently WebGL only; WGPU support planned
- **Configuration Persistence**: Saving/loading editor configurations not yet supported

See `sysl/shader/shader_templates/future_shaders.md` for planned shader additions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note**: Shader templates derived from ShaderToy retain their original licensing.

## Maintenance & contributions

SySL is currently **solo-maintained**. Releases, versioning, and roadmap decisions are
made by the maintainer and may evolve as the surrounding research/software does.

At this time the project has a **closed contribution policy**:

- External pull requests are not accepted by default.
- Bug reports and feature requests are still welcome via GitHub issues.

If this policy changes in the future, the README and `CONTRIBUTING.md` will be updated
to reflect the new contribution model.

## Contact

- **Issues**: [GitHub Issues](https://github.com/bardofcodes/sysl/issues)
- **Email**: [adityaganeshan@gmail.com](mailto:adityaganeshan@gmail.com)

---

*This project is under active development. APIs may change between versions.*
