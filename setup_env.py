#!/usr/bin/env python3
"""
SySL Environment Setup Script (Python version)
This script sets up the PYTHONPATH with all required dependencies
"""

import os
import sys

def setup_sysl_environment():
    """Set up the SySL development environment by configuring PYTHONPATH."""
    
    print("🔧 Setting up SySL development environment...")
    
    # Define all required paths
    required_paths = [
        "/sensei-fs-3/users/aganeshan/projects/mpspy/data_munch",
        "/home/colligo/projects/coref", 
        "/home/colligo/projects/mpspy/mpspy",
        "/home/colligo/projects/vsic_mps",
        "/sensei-fs-3/users/aganeshan/projects/geolipi",
        "/home/colligo/projects/mpspy/sysl"
    ]
    
    # Add paths to Python path
    for path in required_paths:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Also set PYTHONPATH environment variable
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    new_paths = [path for path in required_paths if path not in current_pythonpath]
    
    if new_paths:
        if current_pythonpath:
            os.environ['PYTHONPATH'] = current_pythonpath + ':' + ':'.join(new_paths)
        else:
            os.environ['PYTHONPATH'] = ':'.join(new_paths)
    
    print("✅ PYTHONPATH configured with dependencies:")
    for i, path in enumerate(required_paths, 1):
        path_name = path.split('/')[-1]
        print(f"   {i}. {path_name}: {path}")
    
    print("")
    print("🚀 Environment ready! You can now:")
    print("   - Import SySL modules: import sysl.symbolic as sls")
    print("   - Run SySL scripts and examples")
    print("   - Use the shader generation pipeline")
    print("")
    
    # Test imports
    try:
        import sysl.symbolic
        print("✅ SySL symbolic module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SySL symbolic module: {e}")
        return False
        
    try:
        import sysl.shader
        print("✅ SySL shader module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SySL shader module: {e}")
        return False
    
    print("")
    print("🎉 All SySL modules loaded successfully!")
    return True

if __name__ == "__main__":
    success = setup_sysl_environment()
    if not success:
        sys.exit(1)
    
    print("")
    print("💡 To use this setup in your Python scripts, add:")
    print("   import sys")
    print("   sys.path.append('/sensei-fs-3/users/aganeshan/projects/mpspy/sysl')")
    print("   from setup_env import setup_sysl_environment")
    print("   setup_sysl_environment()")

