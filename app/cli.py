"""CLI headless para transcribir en lote, pensada para que otro proceso la llame.

A diferencia de `transcribe.py` y de la GUI, esta entrada no escribe nada en
`output/` ni mueve los audios: recibe rutas, devuelve JSON por stdout y no toca
el disco del que llama. Eso la hace segura de invocar desde un servicio que ya
administra sus propios archivos (por ejemplo el indice de WhatsApp del
waba-mcp-server).

Uso:
    python -m app.cli --model base a.ogg b.opus
    python -m app.cli --model base --backend gpu --language es a.ogg

Salida: una linea JSON por archivo (JSONL), en el mismo orden de entrada:
    {"file": "a.ogg", "ok": true, "text": "...", "language": "es", "duration": 12.3}
    {"file": "b.opus", "ok": false, "error": "..."}

El modelo se carga UNA vez por invocacion, asi que conviene pasar varios
archivos de golpe en vez de llamar al proceso una vez por audio.
"""

import argparse
import json
import sys
from pathlib import Path

SUPPORTED_FORMATS = {".opus", ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".mp4", ".webm", ".amr"}


def emit(payload: dict) -> None:
    """Una linea JSON por archivo, con flush: el llamador puede ir leyendo."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log(message: str) -> None:
    """Todo lo que no sea resultado va a stderr, para no ensuciar el JSONL."""
    sys.stderr.write(message + "\n")
    sys.stderr.flush()


def load_cpu(model_size: str):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def run(path: Path, language: str | None):
        segments, info = model.transcribe(str(path), language=language)
        text = " ".join(seg.text for seg in segments).strip()
        return text, getattr(info, "language", None), getattr(info, "duration", None)

    return run


def load_gpu(model_size: str):
    import os

    # RX 6700 XT (gfx1031) no esta en los targets del build ROCm de PyTorch.
    os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", "10.3.0")

    import torch
    import whisper

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"backend gpu: usando {device}")
    model = whisper.load_model(model_size, device=device)

    def run(path: Path, language: str | None):
        result = model.transcribe(str(path), fp16=(device == "cuda"), language=language)
        return result["text"].strip(), result.get("language"), None

    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Transcribe audios a JSONL por stdout.")
    parser.add_argument("files", nargs="*", help="Rutas de audio. Si se omite, se leen de stdin, una por linea.")
    parser.add_argument("--model", default="base", help="Tamaño del modelo Whisper (tiny/base/small/medium/large).")
    parser.add_argument(
        "--backend",
        default="gpu",
        choices=["cpu", "gpu"],
        help="gpu = openai-whisper + ROCm/CUDA (por defecto), cpu = faster-whisper. Si la GPU no carga, cae a cpu.",
    )
    parser.add_argument("--language", default=None, help="Fuerza el idioma (ej. es). Por defecto se autodetecta.")
    args = parser.parse_args(argv)

    paths = [Path(f) for f in args.files]
    if not paths:
        paths = [Path(line.strip()) for line in sys.stdin if line.strip()]

    if not paths:
        log("no se recibio ningun archivo")
        return 2

    # Los archivos que no existen se reportan sin cargar el modelo, que es lo caro.
    usable = []
    for path in paths:
        if not path.is_file():
            emit({"file": str(path), "ok": False, "error": "el archivo no existe"})
            continue
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            emit({"file": str(path), "ok": False, "error": f"formato no soportado: {path.suffix}"})
            continue
        usable.append(path)

    if not usable:
        return 1

    log(f"cargando modelo '{args.model}' (backend {args.backend})...")
    backend = args.backend
    try:
        run = load_gpu(args.model) if backend == "gpu" else load_cpu(args.model)
    except Exception as err:
        # La GPU es preferente, no obligatoria: un driver ROCm ausente o un
        # modelo que no cabe en VRAM no debe dejar sin transcribir. Se cae a CPU
        # y se avisa por stderr, que es donde el llamador mira el diagnostico.
        if backend == "gpu":
            log(f"la GPU no cargo ({err}); reintentando en CPU")
            backend = "cpu"
            try:
                run = load_cpu(args.model)
            except Exception as cpu_err:
                for path in usable:
                    emit({"file": str(path), "ok": False, "error": f"no se pudo cargar el modelo: {cpu_err}"})
                return 1
        else:
            for path in usable:
                emit({"file": str(path), "ok": False, "error": f"no se pudo cargar el modelo: {err}"})
            return 1

    failures = 0
    for index, path in enumerate(usable, 1):
        log(f"[{index}/{len(usable)}] {path.name}")
        try:
            text, language, duration = run(path, args.language)
        except Exception as err:
            failures += 1
            emit({"file": str(path), "ok": False, "error": str(err)})
            continue
        emit({
            "file": str(path),
            "ok": True,
            "text": text,
            "language": language,
            "duration": duration,
            "model": args.model,
            "backend": backend,
        })

    return 1 if failures == len(usable) else 0


if __name__ == "__main__":
    raise SystemExit(main())
