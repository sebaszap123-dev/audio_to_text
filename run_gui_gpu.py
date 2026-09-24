#!/usr/bin/env python3
"""Entry point for the PySide6 GUI using openai-whisper + ROCm/CUDA GPU backend."""
import os
import sys

# RX 6700 XT (gfx1031) not in PyTorch ROCm build targets; override to use gfx1030 kernels
if "HSA_OVERRIDE_GFX_VERSION" not in os.environ:
    os.environ["HSA_OVERRIDE_GFX_VERSION"] = "10.3.0"

from dotenv import load_dotenv
load_dotenv()

# Swap the core backend before the GUI imports it
import app.core_gpu as _gpu_core
sys.modules["app.core"] = _gpu_core

from app.gui import main
main()
