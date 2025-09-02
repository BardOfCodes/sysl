import re
from string import Template
from typing import Dict, Callable, List, Any

SMMap: Dict[object, Callable[[], 'ShaderModule']] = {}

class ShaderModule:
    def __init__(self, name, code, dependencies=None, vardeps=None,
                inputs=None, outputs=None, **properties):
        self.name = name
        self.code = code
        self.dependencies = dependencies or []
        self.vardeps = vardeps or []  # Variable dependencies
        self.inputs = inputs
        self.outputs = outputs
        self.properties = properties
        self.hit_count = 0

    def emit_code(self):
        return self.code

    def set_config(self, *args, **kwargs):
        """In Basic Module there is no config to set."""
        self.register_hit(*args, **kwargs)

    def register_hit(self, *args, **kwargs):
        """Register a hit on this shader module and increment the hit count."""
        self.hit_count += 1
        # You can extend this method to handle additional logic with args/kwargs if needed
        # For example, tracking specific usage patterns or parameters

    def __repr__(self):
        return f"<ShaderModule {self.name}>"


def register_shader_module(spec: str) -> Callable[[], ShaderModule]:
    lines = sanitize_lines(spec)
    props = parse_properties(lines)
    code = "\n".join(line for line in lines if not line.startswith("@"))

    name = props.pop("name", None)
    if not name:
        raise ValueError("Shader spec must have @name property")
    name = name[0]
    # Extract specific properties
    dependencies = props.pop("dependencies", [])
    vardeps = props.pop("vardeps", [])
    inputs = props.pop("inputs", None)
    outputs = props.pop("outputs", None)

    def factory():
        return ShaderModule(
            name=name, 
            code=code, 
            dependencies=dependencies,
            vardeps=vardeps,
            inputs=inputs,
            outputs=outputs,
            **props,
        )
    SMMap[name] = factory
    return factory

def sanitize_lines(spec: str) -> List[str]:
    """Removes comments, trims lines, and skips empty ones."""
    lines = []
    for line in spec.strip().splitlines():
        new_line = line.strip()
        if not new_line:
            continue
        if new_line.startswith("//"):
            continue
        lines.append(line)
    return lines

def parse_properties(lines: List[str]) -> Dict[str, Any]:
    props = {}
    for line in lines:
        if not line.startswith("@"):
            continue
        match = re.match(r"@(\w+)\s*(.*)", line)
        if match:
            key, value = match.group(1), match.group(2).strip()
            if not value:  # Handle empty values like @dependencies
                props[key] = []
            elif "," in value:
                if key in props:
                    props[key].extend([v.strip() for v in value.split(",") if v.strip()])
                else:
                    props[key] = [v.strip() for v in value.split(",") if v.strip()]
            else:
                if key in props:    
                    props[key].extend([value])
                else:
                    props[key] = [value]
                
    return props

