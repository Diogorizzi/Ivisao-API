import sys
import os

print(f"Python version: {sys.version}")
print(f"Prefix: {sys.prefix}")
print(f"Path: {sys.path}")

try:
    from ddgs import DDGS
    print("SUCCESS: from ddgs import DDGS")
except ImportError as e:
    print(f"FAILURE: {e}")
    
try:
    from duckduckgo_search import DDGS
    print("SUCCESS: from duckduckgo_search import DDGS")
except ImportError as e:
    print(f"FAILURE: {e}")
