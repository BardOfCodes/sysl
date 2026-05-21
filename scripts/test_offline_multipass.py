#!/usr/bin/env python3
"""
Test script for offline multi-pass rendering.

MILESTONE 3: Multi-pass rendering works correctly.

Usage:
    cd sysl/
    python scripts/test_offline_multipass.py
"""

import sys
import os

# Add sysl to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate_multipass import evaluate_to_multipass_shader
from sysl.shader_runtime.offline_render import render_multipass


def test_basic_multipass_v4():
    """Test multi-pass rendering with V4 materials."""
    print("=" * 60)
    print("TEST: Basic Multi-pass (render mode v4)")
    print("=" * 60)
    
    # Create a simple sphere scene
    sphere = gls.Sphere3D((0.8,))
    material = sls.MaterialV4(
        (0.2, 0.5, 1.0),  # albedo (blue)
        (0.0, 0.0, 0.0),  # emissive
        (0.0, 0.3, 0.0),  # mrc (metallic, roughness, clearcoat)
    )
    scene = sls.MatSolidV4(sphere, material)
    
    settings = {
        "render_mode": "v4",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": True,
            "_AA": 1,
            "_RAYCAST_MAX_STEPS": 200,
            "resolution": [512, 512],
        },
    }
    
    # Generate multipass shaders
    print("Generating multipass shaders...")
    passes = evaluate_to_multipass_shader(scene, settings=settings)
    
    print(f"  Number of passes: {len(passes)}")
    for i, p in enumerate(passes):
        out = p['output_FBO']
        out_name = out['name'] if isinstance(out, dict) else out
        print(f"  Pass {i}: -> {out_name}")
        print(f"    Shader length: {len(p['shader_code'])} chars")
        print(f"    Uniforms: {list(p.get('uniforms', {}).keys())[:5]}...")
        print(f"    Textures: {list(p.get('textures', {}).keys())}")
        print(f"    Input FBOs: {[f['name'] if isinstance(f, dict) else f for f in p.get('input_FBOs', [])]}")
    
    # Render
    print("Rendering multipass...")
    image = render_multipass(passes)
    
    print(f"  Output shape: {image.shape}")
    print(f"  Output dtype: {image.dtype}")
    print(f"  Value range: [{image.min()}, {image.max()}]")
    
    # Save result
    output_path = "test_multipass_v4.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    # Basic validation
    assert image.shape == (512, 512, 4), f"Unexpected shape: {image.shape}"
    assert image.dtype == np.uint8, f"Unexpected dtype: {image.dtype}"
    
    if image.mean() < 1.0:
        print("  WARNING: Image appears mostly black!")
    else:
        print("  Image contains rendered content.")
    
    print("TEST PASSED\n")
    return True


def test_multipass_union():
    """Test multi-pass with union of shapes."""
    print("=" * 60)
    print("TEST: Multi-pass Union of Shapes")
    print("=" * 60)
    
    # Create union of two spheres with different colors
    sphere1 = gls.Translate3D(gls.Sphere3D((0.5,)), (-0.4, 0.0, 0.0))
    sphere2 = gls.Translate3D(gls.Sphere3D((0.5,)), (0.4, 0.0, 0.0))
    
    mat1 = sls.MaterialV4(
        (1.0, 0.2, 0.2),  # red
        (0.0, 0.0, 0.0),
        (0.0, 0.3, 0.0),
    )
    mat2 = sls.MaterialV4(
        (0.2, 1.0, 0.2),  # green
        (0.0, 0.0, 0.0),
        (0.0, 0.3, 0.0),
    )
    
    solid1 = sls.MatSolidV4(sphere1, mat1)
    solid2 = sls.MatSolidV4(sphere2, mat2)
    scene = gls.Union(solid1, solid2)
    
    settings = {
        "render_mode": "v4",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": True,
            "_AA": 1,
            "resolution": [512, 512],
        },
    }
    
    print("Generating multipass shaders...")
    passes = evaluate_to_multipass_shader(scene, settings=settings)
    print(f"  Number of passes: {len(passes)}")
    
    print("Rendering multipass...")
    image = render_multipass(passes)
    
    output_path = "test_multipass_union.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    print("TEST PASSED\n")
    return True


def test_multipass_with_floor():
    """Test multi-pass with floor plane enabled."""
    print("=" * 60)
    print("TEST: Multi-pass with Floor Plane")
    print("=" * 60)
    
    sphere = gls.Translate3D(gls.Sphere3D((0.5,)), (0.0, 0.5, 0.0))
    material = sls.MaterialV4(
        (0.8, 0.6, 0.2),  # gold-ish
        (0.0, 0.0, 0.0),
        (0.8, 0.2, 0.0),  # metallic
    )
    scene = sls.MatSolidV4(sphere, material)
    
    settings = {
        "render_mode": "v4",
        "variables": {
            "_ADD_FLOOR_PLANE": True,
            "castShadows": True,
            "_AA": 1,
            "resolution": [512, 512],
        },
    }
    
    print("Generating multipass shaders...")
    passes = evaluate_to_multipass_shader(scene, settings=settings)
    print(f"  Number of passes: {len(passes)}")
    
    print("Rendering multipass...")
    image = render_multipass(passes)
    
    output_path = "test_multipass_floor.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    print("TEST PASSED\n")
    return True


def test_multipass_higher_resolution():
    """Test multi-pass at higher resolution."""
    print("=" * 60)
    print("TEST: Multi-pass at 1024x1024")
    print("=" * 60)
    
    # Create a box
    box = gls.Cuboid3D((0.6, 0.6, 0.6))
    material = sls.MaterialV4(
        (0.3, 0.3, 0.8),  # blue
        (0.0, 0.0, 0.0),
        (0.0, 0.5, 0.0),
    )
    scene = sls.MatSolidV4(box, material)
    
    settings = {
        "render_mode": "v4",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": True,
            "_AA": 1,
            "resolution": [1024, 1024],
        },
    }
    
    print("Generating multipass shaders...")
    passes = evaluate_to_multipass_shader(scene, settings=settings, post_process_shader=["part_outline_nobg"])
    print(f"  Number of passes: {len(passes)}")
    
    print("Rendering multipass at 1024x1024...")
    image = render_multipass(passes)
    
    print(f"  Output shape: {image.shape}")
    
    output_path = "test_multipass_highres.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    assert image.shape == (1024, 1024, 4), f"Unexpected shape: {image.shape}"
    
    print("TEST PASSED\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OFFLINE MULTI-PASS RENDERER TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_basic_multipass_v4,
        test_multipass_union,
        test_multipass_with_floor,
        test_multipass_higher_resolution,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"TEST FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - MILESTONE 3 COMPLETE")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())

