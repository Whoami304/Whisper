"""The Whisper GUI package, and the one place import paths are set up.

The engine modules under Whisper/ import each other by bare name --
`from AESCipher import AESCipher`, not `from Whisper.AESCipher import ...`
-- so importing the engine only works if that directory is itself on
sys.path. Every GUI module used to rediscover this, and the two windows
did it differently: one wrapped its imports in a try/except that printed
an error and carried on with the names undefined, so a path problem
surfaced later as a NameError in a button handler rather than at startup.

Importing anything from this package now puts both the project root and
the engine directory on sys.path, once, so the windows can simply import
what they need and fail loudly at startup if something is genuinely
missing.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(PROJECT_ROOT, "Whisper")

for _path in (PROJECT_ROOT, ENGINE_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
