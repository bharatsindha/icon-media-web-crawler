#!/usr/bin/env python3
"""Diagnostic script to test brotli support."""
import sys

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}\n")

# Test 1: Check if brotli is installed
try:
    import brotli
    print(f"✓ Brotli installed: {brotli.__version__}")
except ImportError:
    print("✗ Brotli NOT installed - Run: pip3 install --break-system-packages brotli")
    sys.exit(1)

# Test 2: Check if requests can decompress brotli
try:
    import requests
    response = requests.get('https://harthickman.com', headers={
        'User-Agent': 'Mozilla/5.0',
        'Accept-Encoding': 'gzip, deflate, br'
    })
    print(f"✓ Requests working")
    print(f"  Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
    print(f"  Content length: {len(response.content):,} bytes")
    print(f"  Text length: {len(response.text):,} chars")
    print(f"  Text readable: {'Services' in response.text}")

    if 'Services' in response.text:
        print("\n✓ SUCCESS: Brotli decompression is working!")
    else:
        print("\n✗ FAIL: HTML is garbled - brotli decompression failed")

except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
