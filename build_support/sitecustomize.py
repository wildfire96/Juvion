"""Apply exclusions to PyInstaller's isolated dependency import probes.

Windows DLL discovery imports packages outside the analyzed module graph.
Thinc may otherwise load an old, unused PyTorch installation while examining
spaCy, even when torch is excluded from the application bundle.
This directory is added to PYTHONPATH only by the build specification.
"""
import os
import sys

if os.environ.get("JUVION_BUILD_NO_TORCH") == "1":
    for module in ("torch", "torchaudio", "torchvision"):
        sys.modules[module] = None
