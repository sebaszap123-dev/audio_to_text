import shutil
from pathlib import Path

SUPPORTED_FORMATS = {".opus", ".mp3", ".wav", ".ogg", ".m4a", ".flac"}
OUTPUT_PROCESSED_DIR = Path("output/processed")
OUTPUT_STT_DIR = Path("output/stt")


def setup_dirs():
    for d in [OUTPUT_PROCESSED_DIR, OUTPUT_STT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_model(model_size: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_file(model, audio_path: Path) -> str:
    segments, _ = model.transcribe(str(audio_path))
    return " ".join(seg.text for seg in segments).strip()


def process_files(
    audio_paths: list[Path],
    model_size: str,
    on_log=None,
    on_progress=None,
    move_files: bool = True,
) -> list[dict]:
    setup_dirs()

    def log(msg):
        if on_log:
            on_log(msg)

    log(f"Cargando modelo '{model_size}'...")
    model = load_model(model_size)

    total = len(audio_paths)
    results = []

    for i, audio_path in enumerate(audio_paths):
        log(f"[{i + 1}/{total}] Transcribiendo: {audio_path.name}")
        try:
            text = transcribe_file(model, audio_path)
        except Exception as e:
            log(f"  ERROR en '{audio_path.name}': {e}")
            results.append({"file": audio_path.name, "ok": False, "error": str(e)})
            if on_progress:
                on_progress(i + 1, total)
            continue

        txt_path = OUTPUT_STT_DIR / (audio_path.stem + ".txt")
        txt_path.write_text(text, encoding="utf-8")
        log(f"  -> Texto guardado: {txt_path}")

        if move_files:
            dest = OUTPUT_PROCESSED_DIR / audio_path.name
            shutil.move(str(audio_path), dest)
            log(f"  -> Audio movido a: {dest}")

        results.append({"file": audio_path.name, "ok": True, "output": str(txt_path)})

        if on_progress:
            on_progress(i + 1, total)

    log(f"\nListo. {total} archivo(s) procesado(s).")
    return results
