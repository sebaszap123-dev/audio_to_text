# audio_to_text

Herramienta de línea de comandos para transcribir archivos de audio a texto usando [faster-whisper](https://github.com/SYSTRAN/faster-whisper), una implementación optimizada de OpenAI Whisper.

## Por qué se creó

El proyecto nació de la necesidad de transcribir de forma local y masiva notas de voz (audios de WhatsApp en formato `.opus`) sin depender de servicios externos. Corre completamente offline en CPU.

## Requisitos

- Python 3.10+
- `ffmpeg` instalado en el sistema

```bash
# Ubuntu / Debian
sudo apt install ffmpeg
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Uso

1. Coloca los archivos de audio en la carpeta `audios/`.
   - Formatos soportados: `.opus`, `.mp3`, `.wav`

2. Ejecuta el script:

```bash
python transcribe.py
```

3. Opcionalmente elige el tamaño del modelo con `--model`:

```bash
python transcribe.py --model small
```

| Modelo  | Velocidad | Precisión |
|---------|-----------|-----------|
| tiny    | +++       | +         |
| base    | ++        | ++        |
| small   | +         | +++       |
| medium  | -         | ++++      |
| large   | --        | +++++     |

El modelo por defecto es `base`.

## Resultado

Después de procesar, los archivos quedan organizados así:

```
output/
├── stt/           # Transcripciones en .txt (mismo nombre que el audio)
└── processed/     # Audios originales ya procesados
```

Los audios se mueven automáticamente a `output/processed/` para no reprocesarlos en ejecuciones futuras.

## Para abrir la app:


# opción A
.venv/bin/python run_gui.py

# opción B
.venv/bin/python -m app

## Qué tiene la GUI:

Agregar audios — abre el selector de archivos filtrado por los formatos soportados (.opus, .mp3, .wav, .ogg, .m4a, .flac)
Lista de archivos seleccionados, con tooltip al path completo
ComboBox de modelo — tiny / base / small / medium / large
Checkbox para mover los audios a output/processed/ tras transcribir (o dejarlos donde están)
Barra de progreso por archivo
Log en vivo mientras corre el modelo (la ventana no se congela — usa QThread)
Al terminar, los archivos procesados desaparecen de la lista y aparece un diálogo de confirmación o de error