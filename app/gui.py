import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core import SUPPORTED_FORMATS, OUTPUT_STT_DIR, process_files


class TranscriptionWorker(QThread):
    log = Signal(str)
    progress = Signal(int, int)
    finished = Signal(list)

    def __init__(self, audio_paths, model_size, move_files):
        super().__init__()
        self.audio_paths = audio_paths
        self.model_size = model_size
        self.move_files = move_files

    def run(self):
        results = process_files(
            self.audio_paths,
            self.model_size,
            on_log=self.log.emit,
            on_progress=self.progress.emit,
            move_files=self.move_files,
        )
        self.finished.emit(results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio to Text — Whisper")
        self.setMinimumSize(700, 550)
        self.audio_paths: list[Path] = []

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        # ── Tab 1: Transcribir ─────────────────────────────────────────
        tab_run = QWidget()
        run_layout = QVBoxLayout(tab_run)
        run_layout.setSpacing(10)
        run_layout.setContentsMargins(12, 12, 12, 12)

        file_row = QHBoxLayout()
        self.btn_add = QPushButton("Agregar audios…")
        self.btn_add.clicked.connect(self.pick_files)
        self.btn_clear = QPushButton("Limpiar lista")
        self.btn_clear.clicked.connect(self.clear_files)
        file_row.addWidget(self.btn_add)
        file_row.addWidget(self.btn_clear)
        file_row.addStretch()
        run_layout.addLayout(file_row)

        self.file_list = QListWidget()
        self.file_list.setAlternatingRowColors(True)
        self.file_list.setMinimumHeight(130)
        run_layout.addWidget(self.file_list)

        opts_row = QHBoxLayout()
        opts_row.addWidget(QLabel("Modelo:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        opts_row.addWidget(self.model_combo)
        opts_row.addSpacing(20)
        self.move_check = QCheckBox("Mover audios a output/processed/ tras transcribir")
        self.move_check.setChecked(True)
        opts_row.addWidget(self.move_check)
        opts_row.addStretch()
        run_layout.addLayout(opts_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        run_layout.addWidget(self.progress_bar)

        self.btn_run = QPushButton("Transcribir")
        self.btn_run.setFixedHeight(40)
        bold = QFont()
        bold.setBold(True)
        self.btn_run.setFont(bold)
        self.btn_run.clicked.connect(self.run_transcription)
        run_layout.addWidget(self.btn_run)

        run_layout.addWidget(QLabel("Log:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Monospace", 9))
        run_layout.addWidget(self.log_view)

        self.tabs.addTab(tab_run, "Transcribir")

        # ── Tab 2: Resultados ──────────────────────────────────────────
        tab_results = QWidget()
        res_layout = QVBoxLayout(tab_results)
        res_layout.setSpacing(8)
        res_layout.setContentsMargins(12, 12, 12, 12)

        res_layout.addWidget(QLabel("Archivos transcritos:"))
        self.result_list = QListWidget()
        self.result_list.setMaximumHeight(160)
        self.result_list.currentItemChanged.connect(self._load_result_text)
        res_layout.addWidget(self.result_list)

        top_bar = QHBoxLayout()
        self.result_label = QLabel("Selecciona un archivo para ver su texto.")
        top_bar.addWidget(self.result_label)
        top_bar.addStretch()
        self.btn_copy = QPushButton("Copiar texto")
        self.btn_copy.setEnabled(False)
        self.btn_copy.clicked.connect(self._copy_result_text)
        top_bar.addWidget(self.btn_copy)
        res_layout.addLayout(top_bar)

        self.result_view = QTextEdit()
        self.result_view.setReadOnly(True)
        self.result_view.setFont(QFont("Monospace", 9))
        res_layout.addWidget(self.result_view)

        self.tabs.addTab(tab_results, "Resultados")

        self.worker = None
        self._refresh_result_list()

    # ------------------------------------------------------------------
    def pick_files(self):
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_FORMATS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar archivos de audio", "", f"Audio ({exts})"
        )
        for p in paths:
            path = Path(p)
            if path not in self.audio_paths:
                self.audio_paths.append(path)
                item = QListWidgetItem(path.name)
                item.setToolTip(str(path))
                self.file_list.addItem(item)
        self._update_run_button()

    def clear_files(self):
        self.audio_paths.clear()
        self.file_list.clear()
        self.progress_bar.setValue(0)
        self._update_run_button()

    def _update_run_button(self):
        self.btn_run.setEnabled(bool(self.audio_paths))

    # ------------------------------------------------------------------
    def run_transcription(self):
        if not self.audio_paths:
            return
        self.btn_run.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.btn_clear.setEnabled(False)
        self.log_view.clear()
        self.progress_bar.setRange(0, len(self.audio_paths))
        self.progress_bar.setValue(0)

        self.worker = TranscriptionWorker(
            list(self.audio_paths),
            self.model_combo.currentText(),
            self.move_check.isChecked(),
        )
        self.worker.log.connect(self._append_log)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _append_log(self, msg: str):
        self.log_view.append(msg)

    def _on_progress(self, done: int, total: int):
        self.progress_bar.setValue(done)

    def _on_finished(self, results: list):
        errors = [r for r in results if not r["ok"]]
        if errors:
            names = "\n".join(r["file"] for r in errors)
            QMessageBox.warning(self, "Errores", f"Falló la transcripción de:\n{names}")
        else:
            QMessageBox.information(self, "Listo", "Todas las transcripciones completadas.")

        if self.move_check.isChecked():
            done_paths = {r["file"] for r in results if r["ok"]}
            self.audio_paths = [p for p in self.audio_paths if p.name not in done_paths]
            self._refresh_file_list()

        self.btn_run.setEnabled(bool(self.audio_paths))
        self.btn_add.setEnabled(True)
        self.btn_clear.setEnabled(True)
        self.worker = None

        self._refresh_result_list()
        self.tabs.setCurrentIndex(1)

    def _refresh_file_list(self):
        self.file_list.clear()
        for path in self.audio_paths:
            item = QListWidgetItem(path.name)
            item.setToolTip(str(path))
            self.file_list.addItem(item)

    # ------------------------------------------------------------------
    def _refresh_result_list(self):
        self.result_list.clear()
        self.result_view.clear()
        self.btn_copy.setEnabled(False)
        self.result_label.setText("Selecciona un archivo para ver su texto.")
        stt_dir = OUTPUT_STT_DIR
        if not stt_dir.exists():
            return
        for txt in sorted(stt_dir.glob("*.txt")):
            item = QListWidgetItem(txt.name)
            item.setData(Qt.UserRole, str(txt))
            self.result_list.addItem(item)

    def _load_result_text(self, current: QListWidgetItem, _previous):
        if current is None:
            self.result_view.clear()
            self.btn_copy.setEnabled(False)
            self.result_label.setText("Selecciona un archivo para ver su texto.")
            return
        path = Path(current.data(Qt.UserRole))
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as e:
            text = f"[Error leyendo archivo: {e}]"
        self.result_view.setPlainText(text)
        self.result_label.setText(path.name)
        self.btn_copy.setEnabled(bool(text.strip()))

    def _copy_result_text(self):
        text = self.result_view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.btn_copy.setText("¡Copiado!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copiar texto"))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
