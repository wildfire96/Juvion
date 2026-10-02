"""Book Details and Publishing Preparation Panel for Juvion.

Comprehensive publication readiness suite for authors:
- Cover inspection with resolution detection and aspect ratio check.
- Complete synopsis suite (Main Synopsis, Short Logline, and Back-cover Hook/Blurb).
- Full technical credits and metadata (ISBNs, Publisher, Edition, Year, Language, Age Rating, Content Warnings, BISAC categories, Keywords).
- Automatic CIP Catalog Card generator (Ficha Catalográfica) with 1-click clipboard export.
- Interactive Publication Checklist with categorized criteria and readiness progress tracking.
- One-click copy of editorial metadata package for store distribution (Amazon KDP, UICLAP, Kobo, etc.).
"""

import os
import shutil
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from settings.settings_manager import WWSettingsManager

if TYPE_CHECKING:
    from .project_model import ProjectModel
    from .project_window import ProjectWindow


CHECKLIST_ITEMS = [
    # (key, category, label)
    ("draft_complete", "Texto & Revisão", "Primeiro rascunho completo da obra"),
    ("beta_reading", "Texto & Revisão", "Leitura beta ou leitura crítica realizada"),
    ("proofreading", "Texto & Revisão", "Revisão ortográfica e gramatical concluída"),
    ("revision_complete", "Texto & Revisão", "Revisão literária, ritmo e consistência refinados"),

    ("cover_hires", "Capa & Visual", "Capa finalizada em alta resolução (mínimo 1600×2560 ou 300 DPI)"),
    ("cover_thumbnail", "Capa & Visual", "Tipografia e título legíveis mesmo em miniatura"),
    ("cover_spine", "Capa & Visual", "Lombada e quarta capa calculadas (se houver edição impressa)"),

    ("synopsis_ready", "Metadados & Burocracia", "Sinopse principal e gancho de contracapa atraentes"),
    ("isbn_registered", "Metadados & Burocracia", "ISBN registrado para cada formato (digital e/ou impresso)"),
    ("cip_generated", "Metadados & Burocracia", "Ficha catalográfica (CIP) gerada para as primeiras páginas"),
    ("metadata_defined", "Metadados & Burocracia", "Categorias BISAC/Thema e palavras-chave de busca definidas"),
    ("copyright_secured", "Metadados & Burocracia", "Direitos autorais ou registro legal providenciado"),

    ("ebook_validated", "Arquivos & Lançamento", "Arquivo digital (EPUB) validado e formatado"),
    ("print_ready", "Arquivos & Lançamento", "Arquivo para impressão (DOCX / PDF) conferido"),
    ("front_back_matter", "Arquivos & Lançamento", "Folha de rosto, ficha técnica e agradecimentos conferidos"),
]


class BookDetailsPanel(QWidget):
    """Publishing preparation and book identity workspace."""

    def __init__(self, controller: "ProjectWindow", model: "ProjectModel", cover_path: str | None = None):
        super().__init__()
        self.controller = controller
        self.model = model
        self.cover_path = cover_path or model.settings.get("work", {}).get("cover")
        self.checklist_checkboxes = {}
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        content.setObjectName("BookDetailsPanel")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)
        scroll.setWidget(content)

        # Header Title
        title = QLabel("A Obra & Preparação para Publicação")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        intro = QLabel("Configure a identidade visual, metadados, ficha técnica e acompanhe o checklist pré-lançamento.")
        intro.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.7);")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Capa & Identidade
        self.tab_identity = QWidget()
        self._build_identity_tab()
        self.tabs.addTab(self.tab_identity, "Capa & Identidade")

        # Tab 2: Sinopses & Chamadas
        self.tab_synopsis = QWidget()
        self._build_synopsis_tab()
        self.tabs.addTab(self.tab_synopsis, "Sinopses & Blurb")

        # Tab 3: Ficha Técnica & Metadados
        self.tab_metadata = QWidget()
        self._build_metadata_tab()
        self.tabs.addTab(self.tab_metadata, "Ficha Técnica")

        # Tab 4: Ficha Catalográfica (CIP)
        self.tab_cip = QWidget()
        self._build_cip_tab()
        self.tabs.addTab(self.tab_cip, "Dados bibliográficos")

        # Tab 5: Checklist de Publicação
        self.tab_checklist = QWidget()
        self._build_checklist_tab()
        self.tabs.addTab(self.tab_checklist, "Checklist de Lançamento")

        # Bottom Action Buttons
        bottom_box = QHBoxLayout()
        self.save_button = QPushButton("Salvar Informações da Obra")
        self.save_button.setProperty("primary", True)
        self.save_button.setStyleSheet("font-weight: bold; padding: 7px 14px;")
        self.save_button.clicked.connect(self.save)
        bottom_box.addWidget(self.save_button)

        self.btn_copy_summary = QPushButton("Copiar Resumo para Lojas (KDP)")
        self.btn_copy_summary.setToolTip("Copia título, sinopse, palavras-chave e metadados organizados para colar nas plataformas de publicação.")
        self.btn_copy_summary.clicked.connect(self.copy_store_metadata)
        bottom_box.addWidget(self.btn_copy_summary)
        layout.addLayout(bottom_box)

    # -------------------------------------------------------------------------
    # TAB 1: IDENTIDADE & CAPA
    # -------------------------------------------------------------------------
    def _build_identity_tab(self):
        layout = QVBoxLayout(self.tab_identity)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        cover_row = QHBoxLayout()
        self.cover_preview = QLabel("Sem capa")
        self.cover_preview.setObjectName("BookCoverPreview")
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setFixedSize(110, 165)
        self.cover_preview.setStyleSheet("border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; background: rgba(0,0,0,0.2);")
        cover_row.addWidget(self.cover_preview)

        cover_actions = QVBoxLayout()
        lbl_capa = QLabel("Capa da Obra")
        lbl_capa.setStyleSheet("font-weight: bold;")
        cover_actions.addWidget(lbl_capa)

        self.cover_info_label = QLabel("Nenhuma capa selecionada.")
        self.cover_info_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.7);")
        self.cover_info_label.setWordWrap(True)
        cover_actions.addWidget(self.cover_info_label)

        btn_row = QHBoxLayout()
        self.cover_button = QPushButton("Escolher capa...")
        self.cover_button.clicked.connect(self.choose_cover)
        btn_row.addWidget(self.cover_button)

        self.cover_remove_btn = QPushButton("Remover")
        self.cover_remove_btn.clicked.connect(self.remove_cover)
        btn_row.addWidget(self.cover_remove_btn)
        cover_actions.addLayout(btn_row)

        hint = QLabel("💡 Dica: A Amazon KDP recomenda 1600 × 2560 px (proporção 1:1.6). Para impressão, use mínimo 300 DPI.")
        hint.setStyleSheet("font-size: 11px; opacity: 0.8;")
        hint.setWordWrap(True)
        cover_actions.addWidget(hint)
        cover_actions.addStretch()

        cover_row.addLayout(cover_actions, stretch=1)
        layout.addLayout(cover_row)

        form = QFormLayout()
        form.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Título principal do livro")
        form.addRow("Título:", self.title_input)

        self.subtitle_input = QLineEdit()
        self.subtitle_input.setPlaceholderText("Subtítulo complementar (opcional)")
        form.addRow("Subtítulo:", self.subtitle_input)

        self.author_input = QLineEdit()
        self.author_input.setPlaceholderText("Nome do autor(a) ou pseudônimo")
        form.addRow("Autor(a):", self.author_input)

        self.series_input = QLineEdit()
        self.series_input.setPlaceholderText("Ex.: Crônicas da Última Aurora")
        form.addRow("Série:", self.series_input)

        self.volume_input = QLineEdit()
        self.volume_input.setPlaceholderText("Ex.: 1 ou Livro 1")
        form.addRow("Volume:", self.volume_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Planejamento", "Em escrita", "Em revisão", "Concluída", "Pronta para publicação"])
        form.addRow("Estágio:", self.status_combo)

        layout.addLayout(form)
        layout.addStretch()

    # -------------------------------------------------------------------------
    # TAB 2: SINOPSES & CHAMADAS
    # -------------------------------------------------------------------------
    def _build_synopsis_tab(self):
        layout = QVBoxLayout(self.tab_synopsis)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Hook / Blurb
        layout.addWidget(QLabel("Frase de Efeito / Gancho de Contracapa (Blurb):"))
        self.blurb_input = QLineEdit()
        self.blurb_input.setPlaceholderText("Ex.: Quando os deuses adormeceram, a única salvação foi despertar os monstros.")
        layout.addWidget(self.blurb_input)

        # Short Synopsis / Logline
        layout.addWidget(QLabel("Sinopse Curta (Logline - 1 ou 2 frases):"))
        self.short_synopsis_input = QTextEdit()
        self.short_synopsis_input.setMaximumHeight(70)
        self.short_synopsis_input.setPlaceholderText("Resumo conciso de alta intensidade para redes sociais, catálogos e apresentação a editoras...")
        layout.addWidget(self.short_synopsis_input)

        # Main Synopsis
        layout.addWidget(QLabel("Sinopse Completa (Texto de Contracapa e Lojas):"))
        self.synopsis_input = QTextEdit()
        self.synopsis_input.setPlaceholderText("Apresentação completa do universo, do conflito do protagonista e do dilema central que atrai os leitores...")
        layout.addWidget(self.synopsis_input, stretch=1)

        # Dedication / Epigraph
        layout.addWidget(QLabel("Dedicatória / Epígrafe (Página 6 do livro exportado):"))
        self.dedication_input = QTextEdit()
        self.dedication_input.setMaximumHeight(85)
        self.dedication_input.setPlaceholderText("Ex.: Obra cuja honra nasce de sonhos e fantasias...\nDedico esta escrita aos meus pais e a todos os leitores.")
        layout.addWidget(self.dedication_input)

    # -------------------------------------------------------------------------
    # TAB 3: FICHA TÉCNICA & METADADOS
    # -------------------------------------------------------------------------
    def _build_metadata_tab(self):
        layout = QVBoxLayout(self.tab_metadata)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(7)

        self.isbn_digital_input = QLineEdit()
        self.isbn_digital_input.setPlaceholderText("Ex.: 978-65-00-00000-0")
        form.addRow("ISBN Digital (E-book):", self.isbn_digital_input)

        self.isbn_print_input = QLineEdit()
        self.isbn_print_input.setPlaceholderText("Ex.: 978-65-00-00000-0")
        form.addRow("ISBN Impresso:", self.isbn_print_input)

        self.publisher_input = QLineEdit()
        self.publisher_input.setPlaceholderText("Nome da editora ou Publicação Independente")
        form.addRow("Editora / Selo:", self.publisher_input)

        self.cover_designer_input = QLineEdit()
        self.cover_designer_input.setPlaceholderText("Nome do capista, ilustrador ou designer da capa")
        form.addRow("Design da Capa:", self.cover_designer_input)

        self.edition_input = QLineEdit()
        self.edition_input.setText("1ª edição")
        form.addRow("Edição:", self.edition_input)

        self.year_input = QLineEdit()
        self.year_input.setText("2026")
        form.addRow("Ano de Publicação:", self.year_input)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Português", "Inglês", "Espanhol", "Francês", "Italiano", "Alemão", "Outro"])
        form.addRow("Idioma:", self.language_combo)

        self.age_rating_combo = QComboBox()
        self.age_rating_combo.addItems(["Livre para todos os públicos", "10+", "12+", "14+", "16+", "18+ (Conteúdo Adulto)"])
        form.addRow("Classificação Indicativa:", self.age_rating_combo)

        self.content_warnings_input = QLineEdit()
        self.content_warnings_input.setPlaceholderText("Ex.: Violência de fantasia, luto, temas sensíveis (opcional)")
        form.addRow("Avisos de Conteúdo:", self.content_warnings_input)

        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("Ex.: Fantasia Épica, Ficção Científica, Romance, Mistério")
        form.addRow("Gênero / BISAC:", self.category_input)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("Ex.: magia, dragões, conspiração, suspense, enemies to lovers")
        form.addRow("Palavras-chave (Tags):", self.tags_input)

        self.copyright_combo = QComboBox()
        self.copyright_combo.addItems([
            "Todos os direitos reservados (All Rights Reserved)",
            "Creative Commons (CC BY-NC-SA)",
            "Creative Commons (CC BY)",
            "Domínio Público"
        ])
        form.addRow("Direitos Autorais:", self.copyright_combo)

        layout.addLayout(form)
        layout.addStretch()

    # -------------------------------------------------------------------------
    # TAB 4: FICHA CATALOGRÁFICA (CIP)
    # -------------------------------------------------------------------------
    def _build_cip_tab(self):
        layout = QVBoxLayout(self.tab_cip)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        intro = QLabel("Prévia dos dados bibliográficos da obra. Revise os campos antes de usar na publicação.")
        intro.setStyleSheet("font-size: 11px; opacity: 0.7;")
        layout.addWidget(intro)

        self.cip_display = QTextEdit()
        self.cip_display.setReadOnly(True)
        self.cip_display.setStyleSheet("font-family: 'Courier New', monospace; font-size: 12px; background: rgba(0,0,0,0.25); border: 1px dashed rgba(255,255,255,0.2); padding: 10px;")
        layout.addWidget(self.cip_display, stretch=1)

        btn_row = QHBoxLayout()
        self.btn_refresh_cip = QPushButton("Atualizar prévia")
        self.btn_refresh_cip.clicked.connect(self.update_cip_card)
        btn_row.addWidget(self.btn_refresh_cip)

        self.btn_copy_cip = QPushButton("Copiar dados bibliográficos")
        self.btn_copy_cip.clicked.connect(self.copy_cip_to_clipboard)
        btn_row.addWidget(self.btn_copy_cip)
        layout.addLayout(btn_row)

    # -------------------------------------------------------------------------
    # TAB 5: CHECKLIST DE PUBLICAÇÃO
    # -------------------------------------------------------------------------
    def _build_checklist_tab(self):
        layout = QVBoxLayout(self.tab_checklist)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Readiness progress bar
        prog_header = QHBoxLayout()
        prog_header.addWidget(QLabel("Prontidão para Publicação:"))
        self.progress_pct_label = QLabel("0%")
        self.progress_pct_label.setStyleSheet("font-weight: bold;")
        prog_header.addStretch()
        prog_header.addWidget(self.progress_pct_label)
        layout.addLayout(prog_header)

        self.readiness_bar = QProgressBar()
        self.readiness_bar.setRange(0, 100)
        self.readiness_bar.setValue(0)
        self.readiness_bar.setTextVisible(False)
        self.readiness_bar.setFixedHeight(10)
        layout.addWidget(self.readiness_bar)

        # Categorized checkboxes inside a scrollable layout
        current_cat = None
        group = None
        group_layout = None

        for key, category, text in CHECKLIST_ITEMS:
            if category != current_cat:
                current_cat = category
                group = QGroupBox(category)
                group_layout = QVBoxLayout(group)
                group_layout.setContentsMargins(8, 8, 8, 8)
                group_layout.setSpacing(6)
                layout.addWidget(group)

            cb = QCheckBox(text)
            cb.stateChanged.connect(self._on_checklist_item_changed)
            self.checklist_checkboxes[key] = cb
            group_layout.addWidget(cb)

        layout.addStretch()

    # -------------------------------------------------------------------------
    # LOAD & REFRESH VALUES
    # -------------------------------------------------------------------------
    def _load_values(self):
        work = self.model.settings.get("work", {})
        pub = self.model.settings.get("publication", {})

        # Tab 1
        self.title_input.setText(self.model.project_name)
        self.subtitle_input.setText(pub.get("subtitle", ""))
        self.author_input.setText(pub.get("author", ""))
        self.series_input.setText(work.get("series", ""))
        self.volume_input.setText(work.get("volume", ""))
        index = self.status_combo.findText(work.get("status", "Planejamento"))
        self.status_combo.setCurrentIndex(max(index, 0))
        self._update_cover_preview()

        # Tab 2
        self.blurb_input.setText(pub.get("blurb", ""))
        self.short_synopsis_input.setPlainText(pub.get("short_synopsis", ""))
        self.synopsis_input.setPlainText(work.get("synopsis", ""))
        self.dedication_input.setPlainText(pub.get("dedication", ""))

        # Tab 3
        self.isbn_digital_input.setText(pub.get("isbn_digital", ""))
        self.isbn_print_input.setText(pub.get("isbn_print", ""))
        self.publisher_input.setText(pub.get("publisher", "Publicação Independente"))
        self.cover_designer_input.setText(pub.get("cover_designer", ""))
        self.edition_input.setText(pub.get("edition", "1ª edição"))
        self.year_input.setText(pub.get("publication_year", "2026"))
        idx_lang = self.language_combo.findText(pub.get("language", "Português"))
        self.language_combo.setCurrentIndex(max(idx_lang, 0))
        idx_age = self.age_rating_combo.findText(pub.get("age_rating", "Livre para todos os públicos"))
        self.age_rating_combo.setCurrentIndex(max(idx_age, 0))
        self.content_warnings_input.setText(pub.get("content_warnings", ""))
        self.category_input.setText(work.get("categories", ""))
        self.tags_input.setText(work.get("tags", ""))
        idx_copy = self.copyright_combo.findText(pub.get("copyright", "Todos os direitos reservados (All Rights Reserved)"))
        self.copyright_combo.setCurrentIndex(max(idx_copy, 0))

        # Tab 4 CIP
        self.update_cip_card()

        # Tab 5 Checklist
        checklist_state = pub.get("checklist", {})
        for key, cb in self.checklist_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(bool(checklist_state.get(key, False)))
            cb.blockSignals(False)
        self._calculate_checklist_progress()

    def _update_cover_preview(self):
        if not self.cover_path or not os.path.exists(self.cover_path):
            self.cover_preview.setPixmap(QPixmap())
            self.cover_preview.setText("Sem capa")
            self.cover_info_label.setText("Nenhuma capa selecionada.")
            return

        pixmap = QPixmap(self.cover_path)
        if pixmap.isNull():
            self.cover_preview.setPixmap(QPixmap())
            self.cover_preview.setText("Capa indisponível")
            self.cover_info_label.setText("Arquivo de imagem corrompido ou inacessível.")
            return

        w = pixmap.width()
        h = pixmap.height()
        ratio = round(h / w, 2) if w else 0
        ratio_text = "Ideal para e-book (1:1.6)" if 1.5 <= ratio <= 1.65 else f"Proporção: 1:{ratio}"

        self.cover_preview.setText("")
        self.cover_preview.setPixmap(
            pixmap.scaled(
                self.cover_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.cover_info_label.setText(
            f"Dimensões: <b>{w} × {h} px</b><br>"
            f"{ratio_text}<br>"
            f"Arquivo: {os.path.basename(self.cover_path)}"
        )

    def choose_cover(self):
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher capa da obra",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not source_path:
            return

        destination_dir = WWSettingsManager.get_project_path(self.model.project_name)
        os.makedirs(destination_dir, exist_ok=True)
        destination_path = os.path.join(destination_dir, os.path.basename(source_path))
        if os.path.abspath(source_path) != os.path.abspath(destination_path):
            shutil.copy2(source_path, destination_path)
        self.cover_path = os.path.relpath(destination_path)
        self._update_cover_preview()
        self.save()

    def remove_cover(self):
        self.cover_path = None
        self._update_cover_preview()
        self.save()

    # -------------------------------------------------------------------------
    # CIP CARD GENERATION
    # -------------------------------------------------------------------------
    def update_cip_card(self):
        author = self.author_input.text().strip() or "Autor Desconhecido"
        # Parse author surname
        name_parts = author.split()
        if len(name_parts) > 1:
            cip_author_name = f"{name_parts[-1].upper()}, {' '.join(name_parts[:-1])}"
        else:
            cip_author_name = author.upper()

        title = self.title_input.text().strip() or self.model.project_name
        subtitle = self.subtitle_input.text().strip()
        full_title = f"{title}: {subtitle}" if subtitle else title
        publisher = self.publisher_input.text().strip() or "Publicação Independente"
        year = self.year_input.text().strip() or "2026"
        edition = self.edition_input.text().strip() or "1ª ed."
        isbn_dig = self.isbn_digital_input.text().strip()
        isbn_prt = self.isbn_print_input.text().strip()
        category = self.category_input.text().strip() or "Ficção"

        card = [
            "------------------------------------------------------------------------",
            "         Prévia de dados bibliográficos — Juvion",
            "------------------------------------------------------------------------",
            f"{cip_author_name}.",
            f"   {full_title} / {author}. -- {edition} -- {publisher}, {year}.",
            "",
            f"   ISBN {isbn_dig} (recurso eletrônico)" if isbn_dig else "   ISBN digital: não informado"
        ]
        if isbn_prt:
            card.append(f"   ISBN {isbn_prt} (impresso)")

        card.extend([
            "",
            f"   1. {category}. 2. Literatura Brasileira / Ficção. I. Título.",
            "",
            "   Classificação bibliográfica: a preencher",
            "------------------------------------------------------------------------",
            "  Índice para catálogo sistemático: 1. Ficção : Literatura brasileira"
        ])

        self.cip_display.setPlainText("\n".join(card))

    def copy_cip_to_clipboard(self):
        self.update_cip_card()
        QApplication.clipboard().setText(self.cip_display.toPlainText())
        self.controller.statusBar().showMessage("Ficha catalográfica copiada para a área de transferência!", 3500)

    # -------------------------------------------------------------------------
    # CHECKLIST LOGIC
    # -------------------------------------------------------------------------
    def _on_checklist_item_changed(self):
        self._calculate_checklist_progress()
        self.save()

    def _calculate_checklist_progress(self):
        total = len(self.checklist_checkboxes)
        if total == 0:
            return
        checked = sum(1 for cb in self.checklist_checkboxes.values() if cb.isChecked())
        pct = int((checked / total) * 100)
        self.readiness_bar.setValue(pct)
        self.progress_pct_label.setText(f"{pct}% ({checked} de {total} itens prontos)")

    # -------------------------------------------------------------------------
    # SAVE & EXPORT METADATA PACKAGE
    # -------------------------------------------------------------------------
    def save(self):
        # 1. Update work dictionary
        self.model.settings["work"] = {
            "cover": self.cover_path,
            "synopsis": self.synopsis_input.toPlainText().strip(),
            "series": self.series_input.text().strip(),
            "volume": self.volume_input.text().strip(),
            "categories": self.category_input.text().strip(),
            "tags": self.tags_input.text().strip(),
            "status": self.status_combo.currentText(),
        }

        # 2. Update publication dictionary
        checklist_state = {key: cb.isChecked() for key, cb in self.checklist_checkboxes.items()}
        self.model.settings["publication"] = {
            "subtitle": self.subtitle_input.text().strip(),
            "author": self.author_input.text().strip(),
            "blurb": self.blurb_input.text().strip(),
            "short_synopsis": self.short_synopsis_input.toPlainText().strip(),
            "dedication": self.dedication_input.toPlainText().strip(),
            "isbn_digital": self.isbn_digital_input.text().strip(),
            "isbn_print": self.isbn_print_input.text().strip(),
            "publisher": self.publisher_input.text().strip(),
            "cover_designer": self.cover_designer_input.text().strip(),
            "edition": self.edition_input.text().strip(),
            "publication_year": self.year_input.text().strip(),
            "language": self.language_combo.currentText(),
            "age_rating": self.age_rating_combo.currentText(),
            "content_warnings": self.content_warnings_input.text().strip(),
            "bisac_subject": self.category_input.text().strip(),
            "copyright": self.copyright_combo.currentText(),
            "checklist": checklist_state,
        }

        self.model.save_settings()
        self.controller.update_work_cover(self.cover_path)
        self.controller.statusBar().showMessage("Informações de publicação salvas com sucesso!", 3000)

    def copy_store_metadata(self):
        """Format an all-in-one clipboard summary for pasting into publishing platforms (Amazon KDP, Kobo, UICLAP)."""
        title = self.title_input.text().strip() or self.model.project_name
        subtitle = self.subtitle_input.text().strip()
        author = self.author_input.text().strip() or "Autor Desconhecido"
        blurb = self.blurb_input.text().strip()
        synopsis = self.synopsis_input.toPlainText().strip()
        categories = self.category_input.text().strip()
        tags = self.tags_input.text().strip()
        isbn_d = self.isbn_digital_input.text().strip() or "Não informado"
        isbn_p = self.isbn_print_input.text().strip() or "Não informado"
        age = self.age_rating_combo.currentText()

        package = (
            f"=== PACOTE EDITORIAL DE PUBLICAÇÃO — {title.upper()} ===\n\n"
            f"TÍTULO: {title}\n"
            f"SUBTÍTULO: {subtitle}\n"
            f"AUTOR: {author}\n"
            f"SÉRIE: {self.series_input.text().strip()} (Vol. {self.volume_input.text().strip()})\n"
            f"CLASSIFICAÇÃO: {age}\n"
            f"ISBN DIGITAL: {isbn_d}\n"
            f"ISBN IMPRESSO: {isbn_p}\n\n"
            f"CATEGORIAS: {categories}\n"
            f"PALAVRAS-CHAVE: {tags}\n\n"
            f"GANCHO / BLURB:\n{blurb}\n\n"
            f"SINOPSE:\n{synopsis}\n"
            "========================================================\n"
        )
        QApplication.clipboard().setText(package)
        QMessageBox.information(
            self,
            "Metadados Copiados",
            "O resumo completo com Título, Autor, Sinopse, Categorias e Palavras-chave foi copiado para sua área de transferência!\n\n"
            "Você pode colar diretamente nos formulários de cadastro da Amazon KDP, UICLAP ou outra distribuidora."
        )
