#!/usr/bin/env python3
import os
import sys
import shutil
import argparse
from pathlib import Path

SUPPORTED_FORMATS = {".opus", ".mp3", ".wav"}
AUDIOS_DIR = Path("audios")
OUTPUT_PROCESSED_DIR = Path("output/processed")
OUTPUT_STT_DIR = Path("output/stt")


def load_model(model_size: str):
    from faster_whisper import WhisperModel
    print(f"Cargando modelo '{model_size}'...")
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe(model, audio_path: Path) -> str:
    segments, _ = model.transcribe(str(audio_path))
    return " ".join(seg.text for seg in segments).strip()


def setup_dirs():
    for d in [AUDIOS_DIR, OUTPUT_PROCESSED_DIR, OUTPUT_STT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_audio_files() -> list[Path]:
    return [
        f for f in AUDIOS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    ]


def process(model_size: str):
    setup_dirs()

    audio_files = get_audio_files()
    if not audio_files:
        print(f"No se encontraron archivos de audio en '{AUDIOS_DIR}/'.")
        return

    model = load_model(model_size)

    total = len(audio_files)
    print(f"\nArchivos encontrados: {total}\n")

    for i, audio_path in enumerate(audio_files, 1):
        print(f"[{i}/{total}] Transcribiendo: {audio_path.name}")
        try:
            text = transcribe(model, audio_path)
        except Exception as e:
            print(f"  ERROR al transcribir '{audio_path.name}': {e}")
            continue

        txt_name = audio_path.stem + ".txt"
        txt_path = OUTPUT_STT_DIR / txt_name
        txt_path.write_text(text, encoding="utf-8")
        print(f"  -> Texto guardado en: {txt_path}")

        dest_audio = OUTPUT_PROCESSED_DIR / audio_path.name
        shutil.move(str(audio_path), dest_audio)
        print(f"  -> Audio movido a:    {dest_audio}")

    print(f"\nListo. {total} archivo(s) procesado(s).")
    print(f"  Textos  -> {OUTPUT_STT_DIR}/")
    print(f"  Audios  -> {OUTPUT_PROCESSED_DIR}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcribe audios a texto usando Whisper.")
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large"],
        help="Tamaño del modelo Whisper (default: base)",
    )
    args = parser.parse_args()
    process(args.model)
