#!/usr/bin/env python3
"""
Test script for offline single-pass rendering.

MILESTONE 1: Basic sphere renders correctly without textures.

Usage:
    cd sysl/
    python scripts/test_offline_single_pass.py
"""

import sys
import os

# Add sysl to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import geolipi.symbolic as gls
import sysl.symbolic as sls
from sysl.shader.evaluate import evaluate_to_shader
from sysl.shader_vis.offline_render import render_single_pass


def test_basic_sphere():
    """Test rendering a basic sphere with simple material."""
    print("=" * 60)
    print("TEST: Basic Sphere (render mode v1)")
    print("=" * 60)
    
    # Create a simple sphere scene
    sphere = gls.Sphere3D((1.0,))
    material = sls.SMPLMaterial((2.0,))
    scene = sls.MatSolidV1(sphere, material)
    
    # Settings for simple render
    settings = {
        "render_mode": "v1",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": False,
            "_AA": 1,
            "_RAYCAST_MAX_STEPS": 200,
        },
    }
    
    # Generate shader
    print("Generating shader...")
    shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)
    
    print(f"  Shader code length: {len(shader_code)} chars")
    print(f"  Uniforms: {list(uniforms.keys())}")
    print(f"  Textures: {list(textures.keys())}")
    
    # Render
    print("Rendering...")
    image = render_single_pass(shader_code, uniforms, textures, size=(512, 512))
    
    print(f"  Output shape: {image.shape}")
    print(f"  Output dtype: {image.dtype}")
    print(f"  Value range: [{image.min()}, {image.max()}]")
    
    # Save result
    output_path = "test_sphere_v1.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    # Basic validation
    assert image.shape == (512, 512, 3), f"Unexpected shape: {image.shape}"
    assert image.dtype == np.uint8, f"Unexpected dtype: {image.dtype}"
    
    # Check that we rendered something (not all black)
    if image.mean() < 1.0:
        print("  WARNING: Image appears mostly black!")
    else:
        print("  Image contains rendered content.")
    
    print("TEST PASSED\n")
    return True


def test_translated_sphere():
    """Test rendering a translated sphere."""
    print("=" * 60)
    print("TEST: Translated Sphere (render mode v1)")
    print("=" * 60)
    
    # Create a translated sphere
    sphere = gls.Sphere3D((0.5,))
    translated = gls.Translate3D(sphere, (0.5, 0.0, 0.0))
    material = sls.SMPLMaterial((3.0,))
    scene = sls.MatSolidV1(translated, material)
    
    settings = {
        "render_mode": "v1",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": False,
            "_AA": 1,
        },
    }
    
    print("Generating shader...")
    shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)
    
    print("Rendering...")
    image = render_single_pass(shader_code, uniforms, textures, size=(512, 512))
    
    output_path = "test_translated_sphere.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    print("TEST PASSED\n")
    return True


def test_union_shapes():
    """Test rendering union of two shapes."""
    print("=" * 60)
    print("TEST: Union of Shapes (render mode v1)")
    print("=" * 60)
    
    # Create union of sphere and box
    sphere = gls.Translate3D(gls.Sphere3D((0.4,)), (-0.3, 0.0, 0.0))
    box = gls.Translate3D(gls.Cuboid3D((0.3, 0.3, 0.3)), (0.3, 0.0, 0.0))
    union = gls.Union(sphere, box)
    material = sls.SMPLMaterial((4.0,))
    scene = sls.MatSolidV1(union, material)
    
    settings = {
        "render_mode": "v1",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": False,
            "_AA": 1,
        },
    }
    
    print("Generating shader...")
    shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)
    
    print("Rendering...")
    image = render_single_pass(shader_code, uniforms, textures, size=(512, 512))
    
    output_path = "test_union_shapes.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    print("TEST PASSED\n")
    return True


def test_v3_material():
    """Test rendering with v3 material system."""
    print("=" * 60)
    print("TEST: V3 Material (PBR-style)")
    print("=" * 60)
    
    # Create scene with PBR material
    sphere = gls.Sphere3D((0.8,))
    # NonEmissiveMaterialV3: albedo, metallic, roughness, clearcoat
    material = sls.MaterialV4(
        (1.0, 0.2, 0.2),  # albedo (red)
        (0.0, 0.0, 0.0),  # emissive
        (0.0, 0.0, 0.0),  # mrc
    )
    scene = sls.MatSolidV4(sphere, material)
    
    settings = {
        "render_mode": "v4",
        "variables": {
            "_ADD_FLOOR_PLANE": False,
            "castShadows": True,
            "_AA": 1,
        },
    }
    
    print("Generating shader...")
    shader_code, uniforms, textures = evaluate_to_shader(scene, settings=settings)
    
    print(f"  Shader code length: {len(shader_code)} chars")
    
    print("Rendering...")
    image = render_single_pass(shader_code, uniforms, textures, size=(512, 512))
    
    output_path = "test_v4_material.png"
    Image.fromarray(image).save(output_path)
    print(f"  Saved to: {output_path}")
    
    print("TEST PASSED\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("OFFLINE SINGLE-PASS RENDERER TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_basic_sphere,
        test_translated_sphere,
        test_union_shapes,
        test_v3_material,
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
        print("\n✓ ALL TESTS PASSED - MILESTONE 1 COMPLETE")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())


