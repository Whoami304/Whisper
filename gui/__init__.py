"""The Whisper GUI package, and the one place import paths are set up.

The engine modules under Whisper/ import each other by bare name
(`import engine`, `from legacy import ...`), so that directory must be on
sys.path. Importing anything from this package puts both the project root
and the engine directory there, once.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(PROJECT_ROOT, "Whisper")

for _path in (PROJECT_ROOT, ENGINE_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
