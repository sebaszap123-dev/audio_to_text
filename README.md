# audio_to_text

Herramienta con GUI para transcribir archivos de audio a texto usando Whisper de forma local y offline.

Soporta dos backends:
- **CPU** — [faster-whisper](https://github.com/SYSTRAN/faster-whisper), rápido en CPU con int8.
- **GPU AMD** — [openai-whisper](https://github.com/openai/whisper) + PyTorch ROCm, usa la GPU via ROCm.

## Por qué se creó

Necesidad de transcribir notas de voz (WhatsApp `.opus`) de forma local y masiva sin servicios externos.

## Requisitos del sistema

- Python 3.10+
- `ffmpeg` instalado

```bash
# Fedora
sudo dnf install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

---

## Instalación — versión CPU (faster-whisper)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Instalación — versión GPU AMD (openai-whisper + ROCm)

```bash
python -m venv .venv
source .venv/bin/activate

# 1. PyTorch con ROCm (requiere índice especial)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.3

# 2. Resto de dependencias
pip install -r requirements_gpu.txt

# 3. Verificar que la GPU es detectada
python -c "import torch; print('GPU disponible:', torch.cuda.is_available())"
```

---

## Uso — GUI

```bash
# Versión CPU
.venv/bin/python run_gui.py

# Versión GPU AMD
.venv/bin/python run_gui_gpu.py

# Alternativa CPU (módulo directo)
.venv/bin/python -m app
```

## Uso — CLI headless (para otros programas)

`app/cli.py` es la entrada sin GUI: recibe rutas, devuelve JSONL por stdout y **no** escribe en `output/` ni mueve los audios. Es la que usa el [waba_mcp_server](../../../infra/tools/tools-misc/waba_mcp_server) para transcribir notas de voz de WhatsApp.

```bash
# GPU por defecto, con caída automática a CPU si ROCm/CUDA no carga
.venv/bin/python -m app.cli --model base audio1.ogg audio2.opus

# Forzando idioma y backend
.venv/bin/python -m app.cli --model small --backend cpu --language es audio.ogg

# Rutas por stdin, una por línea (evita el límite de argumentos del sistema)
ls audios/*.ogg | .venv/bin/python -m app.cli --model base
```

Salida: una línea JSON por archivo, en el orden de entrada.

```json
{"file": "audio1.ogg", "ok": true, "text": "...", "language": "es", "model": "base", "backend": "gpu"}
{"file": "roto.ogg", "ok": false, "error": "..."}
```

El progreso y los errores del motor van por **stderr**, así que stdout queda limpio para consumo programático. El modelo se carga una sola vez por invocación: conviene pasar varios archivos de golpe en vez de llamar al proceso una vez por audio.

## Modelos disponibles

| Modelo | Velocidad | Precisión |
|--------|-----------|-----------|
| tiny   | +++       | +         |
| base   | ++        | ++        |
| small  | +         | +++       |
| medium | -         | ++++      |
| large  | --        | +++++ |

Modelo por defecto: `base`.

## Formatos de audio soportados

`.opus`, `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`

## Resultado

```
output/
├── stt/        # Transcripciones en .txt (mismo nombre que el audio)
└── processed/  # Audios originales ya procesados
```

Los audios procesados se mueven automáticamente a `output/processed/` para no reprocesarlos.

## Qué tiene la GUI

- Selector de archivos filtrado por formatos soportados
- Lista de archivos con tooltip al path completo
- ComboBox de modelo (tiny / base / small / medium / large)
- Checkbox para mover audios a `output/processed/` tras transcribir
- Barra de progreso por archivo
- Log en vivo (ventana no se congela — usa QThread)
- Tab de resultados con visor de texto y botón copiar
