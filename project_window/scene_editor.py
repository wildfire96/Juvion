import glob
import json
import os
import re
import sys
from gettext import gettext as _
from typing import TYPE_CHECKING

from PyQt5.QtCore import QEvent, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QKeySequence, QPen, QPixmap, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import (
    QAction,
    QColorDialog,
    QComboBox,
    QButtonGroup,
    QFrame,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QShortcut,
    QStyle,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from spylls.hunspell import Dictionary

from settings.theme_manager import ThemeManager
from util.color_manager import ColorManager
from util.find_dialog import FindDialog

from .focus_mode import PlainTextEdit

if TYPE_CHECKING:
    from .project_window import ProjectWindow


class SceneEditor(QWidget):
    """Scene editor with toolbar, text area, and spellchecking support."""

    # ---------------------------------------------------------------------------
    # Class-level attribute declarations.
    # Attributes created via setattr(...) in setup_toolbar() and those assigned
    # inside init_ui()/setup_editor() are listed here so PyCharm can resolve them.
    # ---------------------------------------------------------------------------
    toolbar: QToolBar
    editor: "PlainTextEdit"
    font_combo: QFontComboBox
    font_size_combo: QComboBox
    typography_scope_frame: QFrame
    lang_combo: QComboBox
    spellcheck_timer: QTimer
    # Formatting / alignment actions (set via setattr in setup_toolbar)
    bold_action: QAction
    italic_action: QAction
    underline_action: QAction
    color_action: QAction
    tts_action: QAction
    align_left_action: QAction
    align_center_action: QAction
    align_right_action: QAction
    manual_save_action: QAction
    oh_shit_action: QAction
    analysis_editor_action: QAction

    def __init__(self, controller: "ProjectWindow", tint_color: QColor = QColor("black")):
        super().__init__()
        self.controller = controller
        self.tint_color = tint_color
        self.suppress_updates = False

        # Setup dictionary path
        # Runtime initialization supplies writable assets, including preferences.
        self.dict_dir = os.path.join(os.getcwd(), "assets", "dictionaries")

        self.languages = {}
        self.dictionary = None
        self.extra_selections = []
        self.spellcheck_selections = []
        self.universe_selections = []
        self.universe_entries = []
        self.universe_suggestion = None
        self.settings_file = os.path.join(self.dict_dir, "editor_settings.json")
        self.saved_language = "Off"

        # Load saved language preference if available
        self.load_language_preference()

        # --- Initialize ColorManager here ---
        settings_path = os.path.join(self.dict_dir, "color_settings.json")
        self.color_manager = ColorManager(settings_path)

        self.shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self.shortcut_find.activated.connect(self.open_find_dialog)
        self.find_dialog = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.toolbar = QToolBar("Editor Toolbar")
        self.editor = PlainTextEdit()

        self.setup_toolbar()
        self.setup_editor()

        layout.addWidget(self.toolbar)
        self.create_typography_scope_panel(layout)
        self.create_universe_suggestion_bar(layout)
        layout.addWidget(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)

        self.load_languages()

    def setup_toolbar(self):
        self.toolbar.setStyleSheet("QToolBar { padding: 2px 4px; } QToolButton { padding: 2px 4px; font-size: 12px; }")
        self.toolbar.setIconSize(QSize(16, 16))
        # Formatting actions
        for name, icon, label, tooltip, func, check in [
            ("bold", "assets/icons/bold.svg", "Negrito", "Aplique negrito ao texto selecionado.", self.controller.toggle_bold, True),
            ("italic", "assets/icons/italic.svg", "Itálico", "Aplique itálico ao texto selecionado.", self.controller.toggle_italic, True),
            ("underline", "assets/icons/underline.svg", "Sublinhado", "Sublinhe o texto selecionado.", self.controller.toggle_underline, True),
            ("color", QIcon(QPixmap("assets/icons/color.svg")), "Cor", "Altere a cor do texto selecionado.", self.on_color_action, False),
        ]:
            setattr(self, f"{name}_action", self.add_action(name, icon, label, tooltip, func, check))
        self.toolbar.addSeparator()

        # TTS
        self.tts_action = self.add_action(
            "tts", "assets/icons/play-circle.svg", "Ouvir texto", "Leia em voz alta a seleção ou, sem seleção, a cena inteira.",
            self.controller.toggle_tts, False
        )
        self.toolbar.addSeparator()

        # Alignment
        for name, icon, label, tooltip, func in [
            ("align_left", "assets/icons/align-left.svg", "À esquerda", "Alinhe o parágrafo à esquerda.", self.controller.align_left),
            ("align_center", "assets/icons/align-center.svg", "Centralizar", "Centralize o parágrafo.", self.controller.align_center),
            ("align_right", "assets/icons/align-right.svg", "À direita", "Alinhe o parágrafo à direita.", self.controller.align_right),
        ]:
            setattr(self, f"{name}_action", self.add_action(name, icon, label, tooltip, func, False))

        self.toolbar.addSeparator()
        # Font selection
        self.font_combo = QFontComboBox()
        self.font_combo.setToolTip("Escolha uma fonte e defina abaixo onde ela será aplicada.")
        self.font_combo.installEventFilter(self)
        self.font_combo.currentFontChanged.connect(self.controller.update_font_family)
        self.toolbar.addWidget(self.font_combo)

        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems([str(s) for s in [10,12,14,16,18,20,24,28,32]])
        self.font_size_combo.setCurrentText("12")
        self.font_size_combo.setToolTip("Escolha um tamanho e defina abaixo onde ele será aplicado.")
        self.font_size_combo.installEventFilter(self)
        self.font_size_combo.currentIndexChanged.connect(
            lambda: self.controller.set_font_size(int(self.font_size_combo.currentText()))
        )
        self.font_size_combo.setMinimumWidth(60)
        self.toolbar.addWidget(self.font_size_combo)
        self.toolbar.addSeparator()

        # Scene-specific
        for name, icon, label, tooltip, func in [
            ("manual_save", "assets/icons/save.svg", "Salvar cena", "Grave agora o texto da cena aberta.", self.controller.manual_save_scene),
            ("oh_shit", "assets/icons/rotate-ccw.svg", "Versões", "Abra cópias de segurança e recupere uma versão anterior da cena.", self.controller.on_oh_shit),
            ("analysis_editor", "assets/icons/feather.svg", "Analisar texto", "Abra ferramentas de leitura e análise para a cena aberta.", self.controller.open_analysis_editor),
        ]:
            setattr(self, f"{name}_action", self.add_action(name, icon, label, tooltip, func, False))

        self.toolbar.addSeparator()
        # Language combo
        self.toolbar.addWidget(QLabel("Revisão ortográfica:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setToolTip("Escolha o idioma usado para revisar a ortografia.")
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        self.toolbar.addWidget(self.lang_combo)

    def create_typography_scope_panel(self, layout):
        """Create the contextual scope chooser shown while changing typography."""
        self.typography_scope_frame = QFrame()
        self.typography_scope_frame.setObjectName("TypographyScopeFrame")
        scope_layout = QHBoxLayout(self.typography_scope_frame)
        scope_layout.setContentsMargins(10, 5, 10, 5)
        scope_layout.setSpacing(6)
        scope_layout.addWidget(QLabel("Aplicar fonte e tamanho em:"))

        self.typography_scope_group = QButtonGroup(self)
        self.typography_scope_buttons = {}
        choices = [
            ("selection", "Selecionado apenas", "Altera somente o trecho marcado no editor."),
            ("open", "Texto aberto", "Altera todo o texto que está aberto agora."),
            ("document", "Todo o documento", "Altera todas as cenas salvas desta obra."),
        ]
        for scope, label, tooltip in choices:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.clicked.connect(lambda _checked, value=scope: self.set_typography_scope(value))
            self.typography_scope_group.addButton(button)
            self.typography_scope_buttons[scope] = button
            scope_layout.addWidget(button)
        scope_layout.addStretch()
        self.set_typography_scope("selection")
        self.typography_scope_frame.hide()
        layout.addWidget(self.typography_scope_frame)

    def create_universe_suggestion_bar(self, layout):
        """Show one quiet, writer-controlled completion from the current universe."""
        self.universe_suggestion_frame = QFrame()
        self.universe_suggestion_frame.setObjectName("UniverseSuggestionFrame")
        suggestion_layout = QHBoxLayout(self.universe_suggestion_frame)
        suggestion_layout.setContentsMargins(10, 5, 10, 5)
        suggestion_layout.setSpacing(8)
        suggestion_layout.addWidget(QLabel("Sugestão do Universo:"))
        self.universe_suggestion_button = QPushButton()
        self.universe_suggestion_button.setToolTip("Insira esta sugestão na posição do cursor.")
        self.universe_suggestion_button.clicked.connect(self.accept_universe_suggestion)
        suggestion_layout.addWidget(self.universe_suggestion_button)
        suggestion_layout.addWidget(QLabel("Tab para inserir"))
        suggestion_layout.addStretch()
        self.universe_suggestion_frame.hide()
        layout.addWidget(self.universe_suggestion_frame)

    def set_typography_scope(self, scope):
        self.typography_scope = scope
        button = self.typography_scope_buttons.get(scope)
        if button:
            button.setChecked(True)

    def current_typography_scope(self):
        return getattr(self, "typography_scope", "selection")

    def eventFilter(self, watched, event):
        if watched in (getattr(self, "font_combo", None), getattr(self, "font_size_combo", None)):
            if event.type() in (QEvent.MouseButtonPress, QEvent.FocusIn):
                self.typography_scope_frame.show()
        if watched is getattr(self, "editor", None) and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Tab and self.universe_suggestion:
                self.accept_universe_suggestion()
                return True
        return super().eventFilter(watched, event)

    def add_action(self, name, icon, label, tooltip, callback, checkable=False):
        """
        Adds a toolbar action. 
        - If `icon` is a QIcon, use it directly (preserving original colors).
        - If `icon` is a string path, pass it through ThemeManager.get_tinted_icon.
        """
        if isinstance(icon, QIcon):
            action_icon = icon
        else:
            action_icon = ThemeManager.get_tinted_icon(icon, self.tint_color)

        action = QAction(action_icon, label, self)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.setCheckable(checkable)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        if name in {"manual_save", "oh_shit", "analysis_editor"}:
            button = self.toolbar.widgetForAction(action)
            if button:
                button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        return action

    def setup_editor(self):
        e = self.editor
        e.setObjectName("ManuscriptEditor")
        e.setFont(QFont("Palatino Linotype", 13))
        e.setPlaceholderText(_("Select a node to edit..."))
        e.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        e.customContextMenuRequested.connect(self.show_context_menu)
        e.installEventFilter(self)
        e.textChanged.connect(self.controller.on_editor_text_changed)
        e.textChanged.connect(self.start_spellcheck_timer)
        e.cursorPositionChanged.connect(self.update_toolbar_state)
        e.selectionChanged.connect(self.update_toolbar_state)

        # Adjust viewport margins to prevent scrollbar from obscuring content
        scrollbar_width = e.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        e.setViewportMargins(0, 0, scrollbar_width, 0)  # Reserve space on the right for scrollbar

        # Spellcheck timer
        self.spellcheck_timer = QTimer(self)
        self.spellcheck_timer.setSingleShot(True)
        self.spellcheck_timer.setInterval(500)
        self.spellcheck_timer.timeout.connect(self.check_spelling)

        self.universe_assistance_timer = QTimer(self)
        self.universe_assistance_timer.setSingleShot(True)
        self.universe_assistance_timer.setInterval(260)
        self.universe_assistance_timer.timeout.connect(self.refresh_universe_assistance)

        # Set a callback to check spelling when content is loaded
        QTimer.singleShot(500, self.delayed_initial_check)

    def on_color_action(self):
        """
        Show a single QColorDialog for foreground only, then apply it to the selected text.
        """
        # 1) Ask user for a new foreground color:
        col = QColorDialog.getColor(
            self.color_manager.default_fg,
            self,
            "Select Text Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel
        )
        if not col.isValid():
            return

        # 2) Update default in ColorManager and save (background stays unchanged):
        self.color_manager.default_fg = col
        self.color_manager.save_colors(self.color_manager.default_fg, self.color_manager.default_bg)

        # 3) Apply only the foreground color to the current selection:
        self.color_manager.apply_fg_to_selection(self.editor, col)

    def load_languages(self):
        self.languages.clear()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        self.lang_combo.addItem("Off")

        # Populate from .aff/.dic pairs
        for aff in glob.glob(os.path.join(self.dict_dir, '*.aff')):
            code = os.path.splitext(os.path.basename(aff))[0]
            dic = os.path.join(self.dict_dir, f"{code}.dic")
            if os.path.isfile(dic):
                self.languages[code] = code
                self.lang_combo.addItem(code)

        # Add Other entry at bottom
        self.lang_combo.addItem("Other")

        # Restore saved
        saved_index = self.lang_combo.findText(self.saved_language)
        if saved_index >= 0:
            self.lang_combo.setCurrentIndex(saved_index)
        else:
            self.lang_combo.setCurrentIndex(0)
        self.lang_combo.blockSignals(False)

        # Apply saved if not Off/Other
        if self.saved_language not in ("Off", "Other"):
            self.apply_saved_language()

    def on_language_changed(self, idx):
        lang = self.lang_combo.currentText()

        # We turn off the check
        if lang == "Off":
            self.dictionary = None
            self.clear_spellcheck_highlights()
            self.save_language_preference(lang)
            return

        # Handling “Other” items
        if lang == "Other":
            dlg = QMessageBox(self)
            dlg.setWindowTitle(_("Additional Dictionaries"))
            dlg.setTextFormat(Qt.TextFormat.RichText)
            dlg.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            dlg.setText(_(
                "For more dictionaries, please visit:<br>"
                "<a href=\"https://github.com/LibreOffice/dictionaries\">"
                "https://github.com/LibreOffice/dictionaries</a><br>"
                "Paste the .aff and .dic file into the folder:<br>"
                "Writingway/assets/dictionaries"
            ))
            dlg.exec_()
            prev = self.saved_language if self.saved_language in self.languages else "Off"
            self.lang_combo.setCurrentText(prev)
            return

        # Build full path (without extension) to the .aff/.dic files
        dict_base = os.path.join(self.dict_dir, lang)
        try:
            # Load the dictionary from "<dict_base>.aff" and "<dict_base>.dic"
            self.dictionary = Dictionary.from_files(dict_base)
            # Run spell‑check immediately
            self.check_spelling()
            # Remember selection
            self.save_language_preference(lang)
        except Exception as e:
            QMessageBox.critical(
                self,
                _("Error"),
                _(f"Cannot load {lang}: {e}")
            )
            self.dictionary = None
            self.clear_spellcheck_highlights()

    def save_language_preference(self, lang):
        try:
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            settings = {"language": lang}
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f)
            self.saved_language = lang
        except Exception as e:
            print(f"Error saving language preference: {e}")

    def load_language_preference(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, encoding='utf-8') as f:
                    settings = json.load(f)
                    self.saved_language = settings.get("language", "Off")
        except Exception as e:
            print(f"Error loading language preference: {e}")

    def apply_saved_language(self):
        if self.saved_language not in self.languages:
            return

        # Build full path (without extension) to the .aff/.dic files
        dict_base = os.path.join(self.dict_dir, self.saved_language)
        try:
            # Load the dictionary from "<dict_base>.aff" and "<dict_base>.dic"
            self.dictionary = Dictionary.from_files(dict_base)
            # If there's already text in the editor, highlight misspellings right away
            if self.editor.toPlainText():
                self.check_spelling()
        except Exception as e:
            print(f"Error loading dictionary {self.saved_language}: {e}")

    def clear_spellcheck_highlights(self):
        self.spellcheck_selections = []
        self.apply_extra_selections()

    def start_spellcheck_timer(self):
        if self.dictionary:
            self.spellcheck_timer.start()

    def check_spelling(self):
        """Check spelling and highlight misspelled words with improved visibility."""
        self.spellcheck_selections = []
        if not self.dictionary:
            self.apply_extra_selections()
            return
        text = self.editor.toPlainText()

        # Create enhanced format for spelling errors
        fmt = QTextCharFormat()
        fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        fmt.setUnderlineColor(QColor(255, 0, 0))  # Bright red

        # Make underline thicker with pen
        pen = QPen(QColor(255, 0, 0))
        pen.setWidth(2)  # Thicker underline
        fmt.setUnderlineColor(pen.color())

        # Use improved regex for word detection that can handle apostrophes and hyphens
        # This matches words and contractions better than the simple \w+ pattern
        word_pattern = r"\b[^\W\d_]+(?:['’-][^\W\d_]+)*\b"

        for m in re.finditer(word_pattern, text):
            w = m.group()
            if not self.dictionary.lookup(w):
                cur = QTextCursor(self.editor.document())
                cur.setPosition(m.start())
                cur.setPosition(m.end(), QTextCursor.MoveMode.KeepAnchor)
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cur
                sel.format = fmt
                self.spellcheck_selections.append(sel)
        self.apply_extra_selections()

    def apply_extra_selections(self):
        """Render spelling and Universe annotations together instead of overwriting either."""
        self.extra_selections = self.spellcheck_selections + self.universe_selections
        self.editor.setExtraSelections(self.extra_selections)

    def set_universe_entries(self, entries):
        """Receive a compact index of this work's Universe from the controller."""
        self.universe_entries = entries or []
        self.schedule_universe_assistance()

    def schedule_universe_assistance(self):
        if hasattr(self, "universe_assistance_timer"):
            self.universe_assistance_timer.start()

    def refresh_universe_assistance(self):
        """Underline Universe names and identify possible new proper nouns in wine tones."""
        text = self.editor.toPlainText()
        self.universe_selections = []
        recognized_spans = set()
        known_format = QTextCharFormat()
        known_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
        known_format.setUnderlineColor(QColor("#7b2e3d"))
        candidate_format = QTextCharFormat()
        candidate_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.DashUnderline)
        candidate_format.setUnderlineColor(QColor("#a95062"))

        known_names = {entry.get("name", "").casefold() for entry in self.universe_entries}
        for entry in sorted(self.universe_entries, key=lambda item: len(item.get("name", "")), reverse=True):
            name = entry.get("name", "").strip()
            if len(name) < 2:
                continue
            for match in re.finditer(r"(?<!\w){}(?!\w)".format(re.escape(name)), text, re.IGNORECASE):
                span = match.span()
                if span in recognized_spans:
                    continue
                cursor = QTextCursor(self.editor.document())
                cursor.setPosition(span[0])
                cursor.setPosition(span[1], QTextCursor.MoveMode.KeepAnchor)
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = known_format
                self.universe_selections.append(selection)
                recognized_spans.add(span)

        ignored_candidates = {
            "A", "O", "As", "Os", "Um", "Uma", "Ele", "Ela", "Eles", "Elas", "Eu", "Nós",
            "No", "Na", "Nos", "Nas", "Em", "Mas", "Se", "Quando", "Então", "Depois",
        }
        for match in re.finditer(r"\b[A-ZÀ-ÖØ-Þ][\wÀ-ÖØ-öø-ÿ'-]{2,}\b", text):
            candidate = match.group()
            if candidate in ignored_candidates or candidate.casefold() in known_names:
                continue
            if any(start <= match.start() and match.end() <= end for start, end in recognized_spans):
                continue
            cursor = QTextCursor(self.editor.document())
            cursor.setPosition(match.start())
            cursor.setPosition(match.end(), QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = candidate_format
            self.universe_selections.append(selection)

        self.apply_extra_selections()
        self.update_universe_suggestion()

    def update_universe_suggestion(self):
        """Choose a single relevant completion from the word being typed and paragraph context."""
        cursor = self.editor.textCursor()
        block_text = cursor.block().text().casefold()
        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        prefix = word_cursor.selectedText().casefold()
        ranked = []
        for entry in self.universe_entries:
            name = entry.get("name", "").strip()
            if not name:
                continue
            lower_name = name.casefold()
            if prefix and lower_name == prefix:
                continue
            score = 0
            if len(prefix) >= 2 and lower_name.startswith(prefix):
                score += 100
            content_words = set(re.findall(r"[\wÀ-ÖØ-öø-ÿ'-]{4,}", entry.get("content", "").casefold()))
            context_words = set(re.findall(r"[\wÀ-ÖØ-öø-ÿ'-]{4,}", block_text))
            score += min(12, len(content_words & context_words) * 3)
            if lower_name in block_text:
                score += 20
            if score:
                ranked.append((score, name, entry))
        if not ranked:
            self.universe_suggestion = None
            self.universe_suggestion_frame.hide()
            return
        _score, name, entry = max(ranked, key=lambda item: (item[0], item[1].casefold()))
        self.universe_suggestion = name
        hierarchy = entry.get("category", "")
        if entry.get("subcategory"):
            hierarchy += " › " + entry["subcategory"]
        self.universe_suggestion_button.setText(name)
        self.universe_suggestion_button.setToolTip("Inserir {} do Universo: {}.".format(name, hierarchy))
        self.universe_suggestion_frame.show()

    def accept_universe_suggestion(self):
        """Insert the visible suggestion only after the writer explicitly accepts it."""
        suggestion = self.universe_suggestion
        if not suggestion:
            return
        cursor = self.editor.textCursor()
        word_cursor = QTextCursor(cursor)
        word_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        typed = word_cursor.selectedText()
        if typed and suggestion.casefold().startswith(typed.casefold()):
            word_cursor.insertText(suggestion)
        else:
            before = self.editor.toPlainText()[:cursor.position()]
            cursor.insertText((" " if before and not before[-1].isspace() else "") + suggestion)
        self.universe_suggestion = None
        self.universe_suggestion_frame.hide()
        self.schedule_universe_assistance()

    def show_context_menu(self, pos):
        menu = self.editor.createStandardContextMenu(pos)
        cur = self.editor.textCursor()
        if cur.hasSelection():
            act = menu.addAction(_("Rewrite"))
            act.triggered.connect(self.controller.rewrite_selected_text)
        context_cursor = QTextCursor(cur)
        if not context_cursor.hasSelection():
            context_cursor = self.editor.cursorForPosition(pos)
            context_cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        universe_name = " ".join(context_cursor.selectedText().split()).strip(".,;:!?()[]{}\"")
        if universe_name:
            add_to_universe = menu.addAction("Adicionar “{}” ao Universo".format(universe_name))
            source_paragraph = context_cursor.block().text().strip()
            add_to_universe.triggered.connect(
                lambda _checked=False, name=universe_name, paragraph=source_paragraph:
                self.controller.add_text_to_universe(name, paragraph)
            )
        if self.dictionary:
            wc = self.editor.cursorForPosition(pos)
            wc.select(QTextCursor.SelectionType.WordUnderCursor)
            w = wc.selectedText()
            if w and not self.dictionary.lookup(w):
                sugs = self.dictionary.suggest(w)
                if sugs:
                    sm = menu.addMenu(_("Suggestions"))
                    for s in sugs:
                        a = sm.addAction(s)
                        a.triggered.connect(lambda _, s=s, c=wc: self.replace_word(c, s))
                else:
                    menu.addAction(_("(No suggestions)"))
        menu.exec_(self.editor.mapToGlobal(pos))

    def replace_word(self, cursor, new):
        cursor.insertText(new)
        self.check_spelling()

    def update_toolbar_state(self):
        if self.suppress_updates:
            return
        self.suppress_updates = True
        cur = self.editor.textCursor()
        if cur.hasSelection():
            fm = self.get_selection_formats(cur.selectionStart(), cur.selectionEnd())
            self.update_toggles_for_selection(fm)
        else:
            cf = self.editor.currentCharFormat()
            self.update_toggles(cf)
        aln = cur.blockFormat().alignment()
        self.align_left_action.setChecked(aln == Qt.AlignmentFlag.AlignLeft)
        self.align_center_action.setChecked(aln == Qt.AlignmentFlag.AlignCenter)
        self.align_right_action.setChecked(aln == Qt.AlignmentFlag.AlignRight)
        self.suppress_updates = False

    def get_selection_formats(self, start, end):
        """
        Returns a list of character formats for each character in the start-end range.
        Used to analyze the formatting of the selected text.
        """
        formats = []
        cursor = self.editor.textCursor()
        for pos in range(start, end):
            cursor.setPosition(pos)
            formats.append(cursor.charFormat())
        return formats

    def delayed_initial_check(self):
        """Perform a delayed initial spell check to make sure content is loaded."""
        if self.dictionary and self.editor and self.editor.toPlainText():
            self.check_spelling()

    def update_toggles(self, cf):
        self.bold_action.setChecked(cf.fontWeight() >= QFont.Weight.Bold)
        self.italic_action.setChecked(cf.fontItalic())
        self.underline_action.setChecked(cf.fontUnderline())

    def update_toggles_for_selection(self, formats):
        """
        formats: a list of QTextCharFormat objects for each character in the selection.
        Checks if all characters have the same style (bold, italic, underline).
        """
        # If no formats, exit
        if not formats:
            return

        # Get the state of the first character as a reference
        first_format = formats[0]
        first_bold = first_format.font().bold()
        first_italic = first_format.font().italic()
        first_underline = first_format.font().underline()

        # Check that all characters have the same style as the first one
        all_bold = all(fmt.font().bold() == first_bold for fmt in formats)
        all_italic = all(fmt.font().italic() == first_italic for fmt in formats)
        all_underline = all(fmt.font().underline() == first_underline for fmt in formats)

        # Set the state of the buttons
        self.bold_action.setChecked(all_bold and first_bold)
        self.italic_action.setChecked(all_italic and first_italic)
        self.underline_action.setChecked(all_underline and first_underline)

    def update_tint(self, tint_color):
        self.tint_color = tint_color
        # Update formatting actions
        formatting_actions = [
            ("bold", "assets/icons/bold.svg"),
            ("italic", "assets/icons/italic.svg"),
            ("underline", "assets/icons/underline.svg")
        ]
        for name, path in formatting_actions:
            action = getattr(self, f"{name}_action", None)
            if action:
                action.setIcon(ThemeManager.get_tinted_icon(path, tint_color))

        # Update TTS action
        tts_action = getattr(self, "tts_action", None)
        if tts_action:
            tts_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/play-circle.svg", tint_color))

        # Update alignment actions
        alignment_actions = [
            ("align_left", "assets/icons/align-left.svg"),
            ("align_center", "assets/icons/align-center.svg"),
            ("align_right", "assets/icons/align-right.svg")
        ]
        for name, path in alignment_actions:
            action = getattr(self, f"{name}_action", None)
            if action:
                action.setIcon(ThemeManager.get_tinted_icon(path, tint_color))

        # Update scene-specific actions
        scene_actions = [
            ("manual_save", "assets/icons/save.svg"),
            ("oh_shit", "assets/icons/share.svg"),
            ("analysis_editor", "assets/icons/feather.svg")
        ]
        for name, path in scene_actions:
            action = getattr(self, f"{name}_action", None)
            if action:
                action.setIcon(ThemeManager.get_tinted_icon(path, tint_color))

    def open_find_dialog(self):
        if self.find_dialog is None:
            self.find_dialog = FindDialog(self.editor, self)
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.search_field.setFocus()
