from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFormLayout, QGroupBox,
    QFileDialog, QMessageBox, QFrame, QSizePolicy,
)

from llm.adapter import PROVIDERS
from config.settings import get_setting, set_setting
from utils.helpers import log

DARK_BG = "#1E1E1E"
ACCENT = "#2E8B57"
TEXT = "#FFFFFF"
SECONDARY_BG = "#2A2A2A"
BORDER = "#3A3A3A"


class DropZone(QWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setStyleSheet(f"""
            DropZone {{
                background: {SECONDARY_BG};
                border: 2px dashed {ACCENT};
                border-radius: 12px;
            }}
            DropZone:hover {{
                border-color: #3AAA6F;
                background: #252525;
            }}
        """)

        icon_label = QLabel("📂", self)
        icon_label.setFont(QFont("Segoe UI", 36))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border: none; background: transparent;")

        self.text_label = QLabel("Trascina qui PDF, PNG o JPG\noppure clicca per selezionare", self)
        self.text_label.setFont(QFont("Segoe UI", 11))
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_label.setStyleSheet(f"color: {TEXT}; border: none; background: transparent;")

        self.hint_label = QLabel("Formati supportati: PDF, PNG, JPG, JPEG, TIFF", self)
        self.hint_label.setFont(QFont("Segoe UI", 9))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setStyleSheet("color: #888888; border: none; background: transparent;")

        layout.addWidget(icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)

    def mousePressEvent(self, event):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleziona Ricevute",
            "",
            "Documenti (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp);;Tutti i file (*)",
        )
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid = any(
                u.toLocalFile().lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"))
                for u in urls
            )
            if valid:
                event.acceptProposedAction()
                self.setStyleSheet(f"""
                    DropZone {{
                        background: #1A3A2A;
                        border: 2px dashed #3AAA6F;
                        border-radius: 12px;
                    }}
                """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            DropZone {{
                background: {SECONDARY_BG};
                border: 2px dashed {ACCENT};
                border-radius: 12px;
            }}
            DropZone:hover {{
                border-color: #3AAA6F;
                background: #252525;
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        self.dragLeaveEvent(None)
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        valid_ext = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}
        paths = [p for p in paths if any(p.lower().endswith(e) for e in valid_ext)]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(36)
        self.setStyleSheet(f"background: #252525; border-top: 1px solid {BORDER};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(24)

        self.last_sync_label = QLabel("Ultimo aggiornamento: —")
        self.total_label = QLabel("Spese: 0")
        self.pending_label = QLabel("In attesa: 0")

        for lbl in (self.last_sync_label, self.total_label, self.pending_label):
            lbl.setStyleSheet(f"color: #AAAAAA; font-size: 10px;")
            layout.addWidget(lbl)

        layout.addStretch()

    def update_stats(self, total: int, pending: int):
        from datetime import datetime
        self.last_sync_label.setText(f"Ultimo aggiornamento: {datetime.now().strftime('%H:%M')}")
        self.total_label.setText(f"Spese: {total}")
        pending_color = "#CC3333" if pending > 0 else "#AAAAAA"
        self.pending_label.setText(f"In attesa: {pending}")
        self.pending_label.setStyleSheet(f"color: {pending_color}; font-size: 10px;")


class SettingsPanel(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_current()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── LLM Provider group ──────────────────────────────────────────────
        llm_group = QGroupBox("Configurazione LLM")
        llm_group.setStyleSheet(self._group_style())
        llm_form = QFormLayout(llm_group)
        llm_form.setSpacing(10)

        self.provider_combo = QComboBox()
        self.provider_combo.setStyleSheet(self._input_style())
        for key, info in PROVIDERS.items():
            self.provider_combo.addItem(info["label"], key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setStyleSheet(self._input_style())

        self.api_key_field = QLineEdit()
        self.api_key_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_field.setPlaceholderText("Incolla qui la tua API key...")
        self.api_key_field.setStyleSheet(self._input_style())

        self.base_url_field = QLineEdit()
        self.base_url_field.setPlaceholderText("Solo per endpoint personalizzati (es. http://localhost:11434/v1)")
        self.base_url_field.setStyleSheet(self._input_style())

        llm_form.addRow("Provider:", self.provider_combo)
        llm_form.addRow("Modello:", self.model_combo)
        llm_form.addRow("API Key:", self.api_key_field)
        llm_form.addRow("URL Base:", self.base_url_field)

        # ── Fiscal settings group ───────────────────────────────────────────
        fiscal_group = QGroupBox("Impostazioni Fiscali")
        fiscal_group.setStyleSheet(self._group_style())
        fiscal_form = QFormLayout(fiscal_group)
        fiscal_form.setSpacing(10)

        self.regime_combo = QComboBox()
        self.regime_combo.setStyleSheet(self._input_style())
        self.regime_combo.addItem("Regime Ordinario", "ordinario")
        self.regime_combo.addItem("Regime Forfettario", "forfettario")

        self.irpef_field = QLineEdit("23.0")
        self.irpef_field.setStyleSheet(self._input_style())
        self.irpef_field.setMaximumWidth(100)

        self.regional_field = QLineEdit("2.03")
        self.regional_field.setStyleSheet(self._input_style())
        self.regional_field.setMaximumWidth(100)

        fiscal_form.addRow("Regime fiscale:", self.regime_combo)
        fiscal_form.addRow("Aliquota IRPEF (%):", self.irpef_field)
        fiscal_form.addRow("Addizionale regionale (%):", self.regional_field)

        # ── Interface group ─────────────────────────────────────────────────
        ui_group = QGroupBox("Interfaccia")
        ui_group.setStyleSheet(self._group_style())
        ui_form = QFormLayout(ui_group)
        ui_form.setSpacing(10)

        self.lang_combo = QComboBox()
        self.lang_combo.setStyleSheet(self._input_style())
        self.lang_combo.addItem("Italiano", "it")
        self.lang_combo.addItem("English", "en")

        ui_form.addRow("Lingua:", self.lang_combo)

        # ── DB group ────────────────────────────────────────────────────────
        db_group = QGroupBox("Database")
        db_group.setStyleSheet(self._group_style())
        db_layout = QVBoxLayout(db_group)

        self.db_path_label = QLabel("Percorso DB: —")
        self.db_path_label.setStyleSheet("color: #AAAAAA; font-size: 10px;")
        db_layout.addWidget(self.db_path_label)

        db_btn_layout = QHBoxLayout()
        export_btn = QPushButton("Esporta Backup")
        export_btn.setStyleSheet(self._btn_style())
        export_btn.clicked.connect(self._export_backup)

        import_btn = QPushButton("Importa Backup")
        import_btn.setStyleSheet(self._btn_style())
        import_btn.clicked.connect(self._import_backup)

        db_btn_layout.addWidget(export_btn)
        db_btn_layout.addWidget(import_btn)
        db_btn_layout.addStretch()
        db_layout.addLayout(db_btn_layout)

        # ── Save button ─────────────────────────────────────────────────────
        save_btn = QPushButton("Salva Impostazioni")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #3AAA6F; }}
            QPushButton:pressed {{ background: #256B44; }}
        """)
        save_btn.clicked.connect(self._save)

        layout.addWidget(llm_group)
        layout.addWidget(fiscal_group)
        layout.addWidget(ui_group)
        layout.addWidget(db_group)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

    def _group_style(self) -> str:
        return f"""
            QGroupBox {{
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 11px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: {ACCENT};
            }}
        """

    def _input_style(self) -> str:
        return f"""
            QLineEdit, QComboBox {{
                background: {SECONDARY_BG};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 11px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {ACCENT};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background: {SECONDARY_BG};
                color: {TEXT};
                selection-background-color: {ACCENT};
            }}
        """

    def _btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: {SECONDARY_BG};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: #333333; border-color: {ACCENT}; }}
        """

    def _on_provider_changed(self):
        key = self.provider_combo.currentData()
        info = PROVIDERS.get(key, {})
        self.model_combo.clear()
        for m in info.get("models", []):
            self.model_combo.addItem(m)
        self.base_url_field.setEnabled(key == "custom")

    def _load_current(self):
        provider = get_setting("llm_provider", "openai")
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == provider:
                self.provider_combo.setCurrentIndex(i)
                break
        self._on_provider_changed()

        model = get_setting("llm_model", "")
        if model:
            idx = self.model_combo.findText(model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setCurrentText(model)

        self.api_key_field.setText(get_setting("llm_api_key", ""))
        self.base_url_field.setText(get_setting("llm_base_url", ""))

        irpef = get_setting("irpef_rate", 23.0)
        self.irpef_field.setText(str(irpef))
        regional = get_setting("regional_rate", 2.03)
        self.regional_field.setText(str(regional))

        regime = get_setting("regime", "ordinario")
        for i in range(self.regime_combo.count()):
            if self.regime_combo.itemData(i) == regime:
                self.regime_combo.setCurrentIndex(i)
                break

        lang = get_setting("language", "it")
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == lang:
                self.lang_combo.setCurrentIndex(i)
                break

        db_path = get_setting("db_path", "")
        self.db_path_label.setText(f"Percorso DB: {db_path}")

    def _save(self):
        from config.settings import load_settings, save_settings
        s = load_settings()
        s["llm_provider"] = self.provider_combo.currentData()
        s["llm_model"] = self.model_combo.currentText()
        s["llm_api_key"] = self.api_key_field.text().strip()
        s["llm_base_url"] = self.base_url_field.text().strip()
        s["regime"] = self.regime_combo.currentData()
        s["language"] = self.lang_combo.currentData()
        try:
            s["irpef_rate"] = float(self.irpef_field.text())
            s["regional_rate"] = float(self.regional_field.text())
        except ValueError:
            QMessageBox.warning(self, "Errore", "Valori aliquota non validi.")
            return
        save_settings(s)
        log.info("Impostazioni salvate")
        QMessageBox.information(self, "Salvato", "Impostazioni salvate con successo.")
        self.settings_saved.emit()

    def _export_backup(self):
        try:
            from db.database import get_db
            db = get_db()
        except Exception:
            QMessageBox.warning(self, "Errore", "Database non connesso.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salva Backup", "dedutto_backup.dedutto", "Backup Dedutto (*.dedutto)"
        )
        if path:
            try:
                db.export_backup(path)
                QMessageBox.information(self, "Backup", f"Backup esportato in:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione:\n{e}")

    def _import_backup(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importa Backup", "", "Backup Dedutto (*.dedutto);;Tutti i file (*)"
        )
        if path:
            reply = QMessageBox.question(
                self,
                "Conferma",
                "Importare il backup sovrascriverà tutti i dati attuali. Continuare?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    from db.database import get_db
                    db = get_db()
                    db.import_backup(path)
                    QMessageBox.information(self, "Importato", "Backup importato con successo.")
                except Exception as e:
                    QMessageBox.critical(self, "Errore", f"Errore durante l'importazione:\n{e}")
