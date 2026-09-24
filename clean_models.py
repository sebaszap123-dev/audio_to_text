#!/usr/bin/env python3
"""Elimina modelos Whisper descargados en cache para liberar espacio."""
import shutil
from pathlib import Path

CACHE_DIRS = {
    "openai-whisper": Path.home() / ".cache" / "whisper",
    "faster-whisper (HuggingFace)": Path.home() / ".cache" / "huggingface" / "hub",
}


def human_size(path: Path) -> str:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    for unit in ("B", "KB", "MB", "GB"):
        if total < 1024:
            return f"{total:.1f} {unit}"
        total /= 1024
    return f"{total:.1f} TB"


def main():
    found = {name: p for name, p in CACHE_DIRS.items() if p.exists()}

    if not found:
        print("No se encontraron caches de modelos.")
        return

    print("Caches encontrados:\n")
    for name, path in found.items():
        print(f"  [{name}]  {path}  ({human_size(path)})")

    print("\n¿Eliminar todos? (s/N): ", end="")
    resp = input().strip().lower()
    if resp != "s":
        print("Cancelado.")
        return

    for name, path in found.items():
        shutil.rmtree(path)
        print(f"  Eliminado: {path}")

    print("\nListo.")


if __name__ == "__main__":
    main()
