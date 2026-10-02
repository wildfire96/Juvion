"""New Project Dialog with Model/Template selector for Juvion."""

import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .templates_data import TEMPLATES


class NewProjectDialog(QDialog):
    """Dialog allowing the author to name the project and pick a craft template."""

    def __init__(self, existing_names, parent=None):
        super().__init__(parent)
        self.existing_names = [n.lower() for n in existing_names]
        self.selected_template_id = "novel"
        self.project_name = ""
        self.chosen_template = TEMPLATES["novel"]
        self.setWindowTitle("Nova Obra — Juvion")
        self.resize(750, 520)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header
        header = QLabel("Criar Nova Obra")
        header.setStyleSheet("font-size: 20px; font-weight: 700;")
        main_layout.addWidget(header)

        sub = QLabel("Escolha o título e um modelo de estrutura narrativa para guiar seus atos, capítulos e universo.")
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 13px; color: rgba(255,255,255,0.7);")
        main_layout.addWidget(sub)

        # Project Name input
        name_group = QGroupBox("Identificação da Obra")
        name_layout = QFormLayout(name_group)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex.: As Crônicas de Aethelgard")
        self.name_input.setStyleSheet("font-size: 14px; padding: 6px;")
        name_layout.addRow("Título da obra:", self.name_input)
        main_layout.addWidget(name_group)

        # Template Selection Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left list: Template cards
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Modelos de Obra:"))

        self.template_list = QListWidget()
        self.template_list.setStyleSheet("font-size: 13px;")
        for key, tmpl in TEMPLATES.items():
            item = QListWidgetItem(f"📖 {tmpl['name']}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.template_list.addItem(item)
        self.template_list.setCurrentRow(0)
        self.template_list.currentItemChanged.connect(self._on_template_selected)
        left_layout.addWidget(self.template_list)
        splitter.addWidget(left_widget)

        # Right pane: Template Details
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        right_layout.addWidget(QLabel("Detalhes do Modelo Selecionado:"))

        self.tmpl_desc = QTextEdit()
        self.tmpl_desc.setReadOnly(True)
        self.tmpl_desc.setStyleSheet("background-color: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 8px;")
        right_layout.addWidget(self.tmpl_desc)

        # Summary of acts/chapters
        self.tmpl_structure_label = QLabel()
        self.tmpl_structure_label.setWordWrap(True)
        self.tmpl_structure_label.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.8);")
        right_layout.addWidget(self.tmpl_structure_label)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, stretch=1)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_create = QPushButton("Criar Obra")
        self.btn_create.setProperty("primary", True)
        self.btn_create.setStyleSheet("font-weight: bold; padding: 8px 18px;")
        self.btn_create.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.btn_create)
        main_layout.addLayout(btn_layout)

        # Initial display
        self._on_template_selected(self.template_list.currentItem())

    def _on_template_selected(self, current_item):
        if not current_item:
            return
        tmpl_id = current_item.data(Qt.ItemDataRole.UserRole)
        tmpl = TEMPLATES.get(tmpl_id, TEMPLATES["novel"])
        self.selected_template_id = tmpl_id
        self.chosen_template = tmpl

        acts = tmpl["structure"]["acts"]
        total_chapters = sum(len(a.get("chapters", [])) for a in acts)
        total_scenes = sum(sum(len(c.get("scenes", [])) for c in a.get("chapters", [])) for a in acts)

        details_html = (
            f"<b>Gênero sugerido:</b> {tmpl['genre']}<br>"
            f"<b>Meta sugerida de palavras:</b> {tmpl['word_goal']:,} palavras<br>"
            f"<b>Categorias:</b> {tmpl['categories']}<br>"
            f"<b>Tags:</b> {tmpl['tags']}<br><br>"
            f"<b>Descrição:</b><br>{tmpl['description']}"
        ).replace(",", ".")
        self.tmpl_desc.setHtml(details_html)

        self.tmpl_structure_label.setText(
            f"Estrutura gerada: {len(acts)} ato(s), {total_chapters} capítulo(s) e {total_scenes} cena(s) estruturadas, "
            f"além de {len(tmpl.get('universe', []))} fichas pré-configuradas no Universo."
        )

    def _validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Nova Obra", "Por favor, digite o nome da nova obra.")
            self.name_input.setFocus()
            return

        if name.lower() in self.existing_names:
            QMessageBox.warning(self, "Nova Obra", f"Já existe uma obra chamada '{name}'. Escolha outro título.")
            self.name_input.setFocus()
            return

        self.project_name = name
        self.accept()
