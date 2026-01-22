# Primitive Editing System

## Overview

The primitive editing system allows interactive manipulation of 3D primitives in a shader-based renderer by dynamically updating shader `#define` statements. When a primitive is selected, its parameters are mapped to shader uniforms, enabling real-time editing through UI controls and keyboard shortcuts.

## Architecture

### Data Flow

```
Python Backend (editing.py)
    ↓
Auxiliary Data Structure
    ↓
JavaScript Frontend (primitive_editing.js.html.j2)
    ↓
Shader #define Updates
    ↓
Real-time Rendering
```

### Key Components

#### 1. Auxiliary Data Structure

The Python backend (`superfit/superfit/utils/editing.py`) generates an auxiliary data structure containing:

- **`primitive_map`** (primitive_parameter_bundles): Maps primitive IDs to arrays of variable names
  - Example: `{0: ['var_5', 'var_6', ...], 1: ['var_8', 'var_9', ...]}`
  - Each array contains variable names at specific indices that correspond to primitive parameters

- **`uniform_map`**: Maps array indices to uniform names
  - Example: `{0: 'size', 1: 'round_dilate_taper_bend', 12: 'axis_angle', 13: 'translate', ...}`
  - Indices correspond to positions in `primitive_parameter_bundles[i]`
  - `None` values indicate parameters that don't map to uniforms

- **`var_map`**: Maps variable names to their default values
  - Example: `{'var_5': [1.0, 1.0, 1.0], 'var_9': [0.0, 0.0, 0.0, 0.0], ...}`

- **`uniforms`**: Uniform definitions with min/max/default values for UI controls

#### 2. Mapping Logic

The core mapping works as follows:

1. When primitive `i` is selected, use `primitive_parameter_bundles[i]` (accessed as `primitiveMap[i]` in JavaScript)
2. For each index `j` in the bundle:
   - Get variable name: `varName = primitive_parameter_bundles[i][j]`
   - Get uniform name: `uniformName = uniform_map[j]`
   - If `uniform_map[j]` is not `None`, create mapping: `varName → uniformName`

**Example:**
```
primitive_parameter_bundles[1] = ['var_5', 'var_6', ..., 'var_8', 'var_9', 'var_10']
uniform_map = {0: 'size', 1: 'round_dilate_taper_bend', ..., 12: 'axis_angle', 13: 'translate'}

Result:
- var_9 (index 12) → 'axis_angle' uniform
- var_10 (index 13) → 'translate' uniform
```

#### 3. Shader Define Generation

When a primitive is selected, the system generates `#define` statements:

- **For mapped variables**: `#define varName uniformName`
  - Example: `#define var_9 axis_angle`
  - The shader uses the uniform value directly

- **For unmapped variables**: `#define varName value`
  - Example: `#define var_8 vec3(1.0, 2.0, 3.0)`
  - Uses the hardcoded value from `var_map`

#### 4. State Management

**Primitive Selection:**
- `currentEditingPrimitive`: Tracks which primitive is currently being edited
- When switching primitives:
  1. Save current uniform values to `var_map` for the previous primitive
  2. Update shader `#define` blocks for the new primitive
  3. Load uniform values from `var_map` for the new primitive

**Uniform Synchronization:**
- `uniformValues`: Runtime uniform values (updated by UI sliders)
- `varMap`: Persistent variable values (saved/loaded per primitive)
- When editing:
  - UI changes → `uniformValues` → shader uniforms (real-time)
  - On primitive switch: `uniformValues` → `varMap` (save)
  - On primitive switch: `varMap` → `uniformValues` (load)

## Editing Modes

### Keyboard Shortcuts

- **G**: Translate mode
- **S**: Scale mode  
- **R**: Rotate mode
- **X/Y/Z**: Constrain to axis (after mode selection)
- **ESC**: Cancel editing
- **Left-click**: Confirm edit
- **Right-click**: Cancel edit

### Axis Editing

The system supports three editing modes:

1. **Translate (G)**: Move primitives
   - Free mode: Move in camera plane (default)
   - Axis mode: Constrain to X/Y/Z axis

2. **Scale (S)**: Resize primitives
   - Uniform mode: Scale all axes equally (default)
   - Axis mode: Scale individual axes

3. **Rotate (R)**: Rotate primitives
   - Requires axis selection (X/Y/Z)
   - Modifies angle component of `axis_angle` uniform

### Camera Integration

Editing uses camera-space calculations for intuitive manipulation:
- Free translation uses camera right/up vectors
- Sensitivity scales with camera distance
- Camera controls are disabled during editing

## Functions

### Core Mapping Functions

- **`getUniformName(index)`**: Gets uniform name for a given bundle index
- **`generateDefineBlock(selectedPrimitive)`**: Generates `#define` block for selected primitive
- **`saveUniformsToVarMap()`**: Saves current uniform values to `var_map`
- **`loadUniformsFromVarMap(primitiveId)`**: Loads uniform values from `var_map` for a primitive
- **`updateShadersForPrimitive(selectedPrimitive)`**: Updates shader code with new `#define` block

### Editing Functions

- **`onPrimitiveSelectedForEditing(primitiveId)`**: Handles primitive selection
- **`startAxisEdit(mode)`**: Enters axis editing mode
- **`handleAxisMouseMove(event)`**: Processes mouse movement during editing
- **`confirmAxisEdit()`**: Saves edit and exits mode
- **`cancelAxisEdit()`**: Discards edit and exits mode

### UI Functions

- **`updateUIForUniform(uniformName, value)`**: Updates slider UI elements
- **`exportVarMap()`**: Exports current `var_map` as JSON

## Data Structures

### `axisEditState`
Tracks current editing session:
```javascript
{
  mode: 'translate' | 'scale' | 'rotate' | null,
  axis: 'x' | 'y' | 'z' | 'free' | 'uniform' | null,
  isActive: boolean,
  isEditing: boolean,
  uniformName: string | null,
  startValue: array | null,
  startMouseX: number,
  startMouseY: number,
  axisIndex: number  // 0=x, 1=y, 2=z
}
```

## Workflow Example

1. **User selects primitive 1**:
   - `onPrimitiveSelectedForEditing(1)` called
   - Previous primitive's uniforms saved to `var_map`
   - `generateDefineBlock(1)` creates new `#define` statements
   - Shader code updated with `#define var_9 axis_angle`, etc.
   - `loadUniformsFromVarMap(1)` loads saved values into `uniformValues`

2. **User presses 'G' (translate)**:
   - `startAxisEdit('translate')` enters translate mode
   - Finds 'translate' uniform via `uniform_map`
   - Camera controls disabled
   - UI indicator shown

3. **User moves mouse**:
   - `handleAxisMouseMove()` calculates new position
   - Updates `uniformValues['translate']` in real-time
   - Shader renders with new position

4. **User left-clicks**:
   - `confirmAxisEdit()` saves to `var_map`
   - Exits editing mode
   - Camera controls restored

## Implementation Notes

- **Key Access**: The system handles both string and numeric keys for `uniform_map` (JSON serialization may convert keys to strings)
- **Shader Updates**: Both shader passes (0 and 1) are updated simultaneously
- **Value Formatting**: Array values are formatted as `vecN(...)` for shader `#define` statements
- **Event Handling**: Mouse events use capture phase to intercept before camera controls

## File Locations

- **Backend**: `superfit/superfit/utils/editing.py`
- **Frontend**: `sysl/sysl/shader_runtime/templates/primitive_editing.js.html.j2`
- **Template**: Jinja2 template that gets rendered with auxiliary data
