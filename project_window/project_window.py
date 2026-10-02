import logging
import os
import re
import threading
import time
from gettext import gettext as _
from gettext import pgettext
from typing import TYPE_CHECKING, Optional

import PyQt5
import tiktoken
from PyQt5.QtCore import QSettings, Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QKeySequence, QTextCharFormat, QTextCursor, QTextDocument
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QShortcut,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QTreeWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from compendium.enhanced_compendium import EnhancedCompendiumWindow

import muse.prompt_handler as prompt_handler
from compendium.compendium_panel import CompendiumPanel
from settings.backup_manager import show_backup_dialog
from settings.llm_api_aggregator import WWApiAggregator
from settings.llm_worker import LLMWorker
from settings.settings_manager import WWSettingsManager
from settings.theme_manager import ThemeManager
from util.tts_manager import WW_TTSManager

from .activity_bar import ActivityBar
from .bottom_stack import BottomStack
from .book_details_panel import BookDetailsPanel
from .embedded_prompts_panel import EmbeddedPromptsPanel
from .focus_mode import FocusMode
from .global_toolbar import GlobalToolbar
from .project_model import ProjectModel
from .project_tree_widget import ProjectTreeWidget
from .rewrite_feature import RewriteDialog
from .scene_editor import SceneEditor
from .search_replace_panel import SearchReplacePanel
from .token_limit_dialog import TokenLimitDialog

pyqt_dir = os.path.dirname(PyQt5.__file__)
possible_paths = [
    os.path.join(pyqt_dir, "Qt5", "plugins", "platforms"),
    os.path.join(pyqt_dir, "Qt", "plugins", "platforms")
]
plugin_path = ""
for path in possible_paths:
    if os.path.exists(path) and os.listdir(path):
        plugin_path = path
        break
if plugin_path:
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path


class ProjectWindow(QMainWindow):
    # ---------------------------------------------------------------------------
    # Class-level attribute declarations — lets PyCharm resolve member types even
    # for attributes that are assigned inside init_ui() / setup_*() helpers rather
    # than directly in __init__.
    # ---------------------------------------------------------------------------
    model: "ProjectModel"
    global_toolbar: "GlobalToolbar"
    main_splitter: QSplitter
    left_widget: QWidget
    activity_bar: "ActivityBar"
    scene_editor: "SceneEditor"
    side_bar: QStackedWidget
    project_tree: "ProjectTreeWidget"
    search_panel: "SearchReplacePanel"
    compendium_panel: "CompendiumPanel"
    book_details_panel: "BookDetailsPanel"
    prompts_panel: "EmbeddedPromptsPanel"
    compendium_editor: QTextEdit
    prompts_editor: QWidget
    editor_stack: QStackedWidget
    bottom_stack: "BottomStack"
    word_count_label: QLabel
    last_save_label: QLabel
    focus_mode_shortcut: QShortcut
    autosave_timer: QTimer

    def __init__(self, project_name: str, compendium_window: Optional["EnhancedCompendiumWindow"], cover_path: str | None = None, project_updated=None):
        super().__init__()
        self.model = ProjectModel(project_name)
        self.project_updated = project_updated
        self.initial_cover_path = cover_path
        self.current_theme = WWSettingsManager.get_appearance_settings()["theme"]
        self.icon_tint = QColor(ThemeManager.ICON_TINTS.get(self.current_theme, "black"))
        self.tts_playing = False
        self.unsaved_preview = False
        self.enhanced_window = compendium_window
        self.worker: LLMWorker | None = None
        self.last_sidebar_width = 380
        self.init_ui()
        self.setup_connections()
        self.read_settings()
        self.load_initial_state()
        self.global_toolbar.toolbar.show()

    def init_ui(self):
        self.setWindowTitle("Juvion — {}".format(self.model.project_name))
        self.resize(1280, 780)
        self.setMinimumSize(980, 620)

        self.setup_status_bar()

        self.global_toolbar = GlobalToolbar(self, self.icon_tint)
        self.addToolBar(self.global_toolbar.toolbar)

        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        studio_header = QWidget()
        studio_header.setObjectName("StudioHeader")
        studio_layout = QHBoxLayout(studio_header)
        studio_layout.setContentsMargins(14, 6, 14, 6)
        studio_layout.setSpacing(8)
        studio_title = QLabel(self.model.project_name)
        studio_title.setObjectName("StudioProjectTitle")
        studio_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        studio_meta = QLabel("Estúdio • Manuscrito")
        studio_meta.setObjectName("StudioProjectMeta")
        studio_meta.setStyleSheet("font-size: 11px; opacity: 0.7;")
        studio_layout.addWidget(studio_title)
        studio_layout.addWidget(studio_meta)
        self.complete_item_button = QPushButton("Concluir item")
        self.complete_item_button.setProperty("primary", True)
        self.complete_item_button.setVisible(False)
        self.complete_item_button.clicked.connect(self.toggle_current_item_completion)
        studio_layout.addWidget(self.complete_item_button)
        studio_layout.addStretch()
        guide_button = QPushButton("Guia")
        guide_button.setToolTip("Veja para que serve cada área e comando principal do Juvion.")
        guide_button.setStyleSheet("padding: 3px 8px; font-size: 12px;")
        guide_button.clicked.connect(self.open_feature_guide)
        studio_layout.addWidget(guide_button)
        focus_button = QPushButton("Modo foco")
        focus_button.setToolTip("Escreva sem distrações. Atalho: F11.")
        focus_button.setStyleSheet("padding: 3px 8px; font-size: 12px;")
        focus_button.clicked.connect(self.open_focus_mode)
        studio_layout.addWidget(focus_button)
        muse_button = QPushButton("Musa IA")
        muse_button.setProperty("primary", True)
        muse_button.setStyleSheet("padding: 3px 10px; font-size: 12px;")
        muse_button.setToolTip("Escolha os prompts e use a assistência de escrita do Juvion.")
        muse_button.clicked.connect(self.open_muse_panel)
        studio_layout.addWidget(muse_button)
        export_button = QPushButton("Exportar obra")
        export_button.setStyleSheet("padding: 3px 10px; font-size: 12px;")
        export_button.setToolTip("Exporte a obra em DOCX (manuscrito editorial), EPUB, PDF, HTML ou Markdown.")
        export_button.clicked.connect(self.open_export_dialog)
        studio_layout.addWidget(export_button)
        main_layout.addWidget(studio_header)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.main_splitter)

        self.left_widget = QWidget()
        left_layout = QHBoxLayout(self.left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.activity_bar = ActivityBar(self, self.icon_tint, position="left")
        left_layout.addWidget(self.activity_bar)
        self.scene_editor = SceneEditor(self, self.icon_tint)

        self.side_bar = QStackedWidget()
        self.side_bar.setMinimumWidth(200)
        self.project_tree = ProjectTreeWidget(self, self.model)
        self.book_details_panel = BookDetailsPanel(self, self.model, self.initial_cover_path)
        self.search_panel = SearchReplacePanel(self, self.model, self.icon_tint)
        self.compendium_panel = CompendiumPanel(self, enhanced_window=self.enhanced_window)
        self.prompts_panel = EmbeddedPromptsPanel(self.model.project_name, self)
        from .progress_dashboard import ProgressDashboard
        self.progress_panel = ProgressDashboard(self)
        from .literary_revision_panel import LiteraryRevisionPanel
        self.revision_panel = LiteraryRevisionPanel(self)
        from .map_panel import MapPanel
        self.map_panel = MapPanel(self)
        self.side_bar.addWidget(self.project_tree)
        self.side_bar.addWidget(self.book_details_panel)
        self.side_bar.addWidget(self.search_panel)
        self.side_bar.addWidget(self.compendium_panel)
        self.side_bar.addWidget(self.prompts_panel)
        self.side_bar.addWidget(self.progress_panel)
        self.side_bar.addWidget(self.revision_panel)
        self.side_bar.addWidget(self.map_panel)
        left_layout.addWidget(self.side_bar)

        self.main_splitter.addWidget(self.left_widget)

        right_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.compendium_editor = QTextEdit()
        self.compendium_editor.setReadOnly(True)
        self.compendium_editor.setPlaceholderText(_("Select a compendium entry to view..."))
        self.prompts_editor = self.prompts_panel.editor_widget
        self.editor_stack = QStackedWidget()
        self.editor_stack.addWidget(self.scene_editor)
        self.editor_stack.addWidget(self.compendium_editor)
        self.editor_stack.addWidget(self.prompts_editor)
        self.bottom_stack = BottomStack(self, self.model, self.icon_tint)
        self.bottom_stack.preview_text.textChanged.connect(self.on_preview_text_changed)
        self.scene_editor.editor.textChanged.connect(self.on_editor_text_changed)

        right_vertical_splitter.addWidget(self.editor_stack)
        right_vertical_splitter.addWidget(self.bottom_stack)
        right_vertical_splitter.setStretchFactor(0, 4)
        right_vertical_splitter.setStretchFactor(1, 1)

        self.main_splitter.addWidget(right_vertical_splitter)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.setSizes([380, 800])
        self.main_splitter.splitterMoved.connect(self.update_sidebar_width)
        self.setCentralWidget(main_widget)

    def open_muse_panel(self):
        if not self.activity_bar.prompts_action.isChecked():
            self.activity_bar.prompts_action.trigger()

    def open_export_dialog(self):
        """Open the complete manuscript export dialog."""
        self.check_unsaved_changes()
        if self.model.unsaved_changes and self.get_current_scene_hierarchy():
            QMessageBox.warning(self, "Exportar obra", "Não foi possível salvar a cena aberta. Confira o salvamento antes de exportar.")
            return
        from exporter.export_dialog import show_export_dialog
        cover = self.initial_cover_path or self.model.settings.get("work", {}).get("cover")
        show_export_dialog(self, self.model.project_name, self.model, cover_path=cover)

    def open_feature_guide(self):
        """Open the concise, in-app map of the writing workspace."""
        from .feature_guide import FeatureGuideDialog

        FeatureGuideDialog(self).exec_()

    def update_sidebar_width(self, pos, index):
        if self.side_bar.isVisible():
            self.last_sidebar_width = self.main_splitter.sizes()[0]

    def toggle_outline_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.project_tree)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.bottom_stack.setVisible(True)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.outline_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.update_contextual_header()

    def toggle_work_details_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.book_details_panel)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.bottom_stack.setVisible(True)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.work_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def update_work_cover(self, cover_path: str | None):
        if self.project_updated:
            self.project_updated(self.model.project_name, cover_path)

    def toggle_search_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.search_panel)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.search_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def toggle_compendium_view(self, show):
        """Open the complete Universo workspace instead of the read-only compact preview."""
        if show and self.enhanced_window:
            current_item = self.compendium_panel.tree.currentItem()
            entry_name = (
                current_item.text(0)
                if current_item and current_item.data(0, Qt.ItemDataRole.UserRole) == "entry"
                else None
            )
            self.enhanced_window.open_with_entry(self.model.project_name, entry_name)
            # The activity button launches a workspace window; keep the manuscript view active behind it.
            self.activity_bar.compendium_action.setChecked(False)
            active_views = {
                self.project_tree: (self.activity_bar.outline_action, "outline"),
                self.book_details_panel: (self.activity_bar.work_action, "work"),
                self.search_panel: (self.activity_bar.search_action, "search"),
                self.prompts_panel: (self.activity_bar.prompts_action, "prompts"),
                self.progress_panel: (self.activity_bar.progress_action, "progress"),
                self.revision_panel: (self.activity_bar.revision_action, "revision"),
                self.map_panel: (self.activity_bar.map_action, "map"),
            }
            active_action, active_view = active_views.get(
                self.side_bar.currentWidget(), (self.activity_bar.outline_action, "outline")
            )
            active_action.setChecked(True)
            self.activity_bar.current_view = active_view
            return

        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.compendium_panel)
            self.editor_stack.setCurrentWidget(self.compendium_editor)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.compendium_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def toggle_prompts_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.prompts_panel)
            self.editor_stack.setCurrentWidget(self.prompts_editor)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
            self.bottom_stack.setVisible(False)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
            self.bottom_stack.setVisible(True)
        self.activity_bar.prompts_action.setChecked(show)
        self.complete_item_button.setVisible(False)

    def toggle_progress_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.progress_panel.refresh()
            self.side_bar.setCurrentWidget(self.progress_panel)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.progress_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def toggle_revision_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.revision_panel)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.revision_panel.run_analysis()
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(320)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.revision_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def toggle_map_view(self, show):
        self.side_bar.setVisible(show)
        if show:
            self.side_bar.setCurrentWidget(self.map_panel)
            self.editor_stack.setCurrentWidget(self.scene_editor)
            self.main_splitter.setSizes([self.last_sidebar_width, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, False)
            self.left_widget.setMinimumWidth(250)
            self.left_widget.setMaximumWidth(16777215)
        else:
            self.last_sidebar_width = self.main_splitter.sizes()[0]
            self.main_splitter.setSizes([50, self.main_splitter.sizes()[1]])
            self.main_splitter.setCollapsible(0, True)
            self.left_widget.setMinimumWidth(50)
            self.left_widget.setMaximumWidth(50)
        self.activity_bar.map_action.setChecked(show)
        self.bottom_stack.setVisible(True)
        self.complete_item_button.setVisible(False)

    def setup_status_bar(self):
        self.setStatusBar(self.statusBar())
        self.word_count_label = QLabel("0 palavras")
        self.last_save_label = QLabel("Ainda não salvo")
        self.statusBar().addPermanentWidget(self.word_count_label)
        self.statusBar().addPermanentWidget(self.last_save_label)

    def setup_connections(self):
        self.focus_mode_shortcut = QShortcut(QKeySequence("F11"), self)
        self.focus_mode_shortcut.activated.connect(self.open_focus_mode)
        self.bottom_stack.summary_controller.progress_updated.connect(self.bottom_stack._update_progress)

    def load_scene_from_hierarchy(self, hierarchy):
        if len(hierarchy) < 3:
            return
        item = self.project_tree.find_item_by_hierarchy(hierarchy)
        if item:
            self.project_tree.tree.setCurrentItem(item)
            self.load_current_item_content()

    def load_initial_state(self):
        current_pov = self.model.settings["global_pov_character"]
        self.update_pov_character_dropdown()
        self.bottom_stack.pov_character_combo.setCurrentText(current_pov)
        self.bottom_stack.pov_combo.setCurrentText(self.model.settings["global_pov"])
        self.bottom_stack.tense_combo.setCurrentText(self.model.settings["global_tense"])
        self.bottom_stack.prompt_input.setPlainText(self.load_prompt_input())
        if self.model.autosave_enabled:
            self.start_autosave_timer()
        if self.project_tree.tree.topLevelItemCount() > 0:
            act_item = self.project_tree.tree.topLevelItem(0)
            if act_item and act_item.childCount() > 0:
                chapter_item = act_item.child(0)
                if chapter_item.childCount() > 0:
                    self.project_tree.tree.setCurrentItem(chapter_item.child(0))
        self.refresh_universe_assistance()

    def start_autosave_timer(self):
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(300000)
        self.autosave_timer.timeout.connect(self.autosave_scene)
        self.autosave_timer.start()

    def read_settings(self):
        settings = QSettings("Juvion", "JuvionProject")
        geometry = settings.value(f"{self.model.project_name}/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        windowState = settings.value(f"{self.model.project_name}/windowState")
        if windowState:
            self.restoreState(windowState)
        splitterState = settings.value(f"{self.model.project_name}/mainSplitterState")
        if splitterState and hasattr(self, "main_splitter"):
            self.main_splitter.restoreState(splitterState)

    def write_settings(self):
        settings = QSettings("Juvion", "JuvionProject")
        settings.setValue(f"{self.model.project_name}/geometry", self.saveGeometry())
        settings.setValue(f"{self.model.project_name}/windowState", self.saveState())
        if hasattr(self, "main_splitter"):
            settings.setValue(f"{self.model.project_name}/mainSplitterState", self.main_splitter.saveState())

    def closeEvent(self, a0):
        if not self.check_unsaved_changes():
            a0.ignore()
            return
        if hasattr(self, 'autosave_timer') and self.autosave_timer.isActive():
            self.autosave_timer.stop()
        self.write_settings()
        a0.accept()

    def check_unsaved_changes(self, item=None):
        if self.model.unsaved_changes:
            self.autosave_scene(item)
        if self.unsaved_preview:
            self.autosave_preview()
        current_item = item or self.project_tree.tree.currentItem()
        if current_item and self.project_tree.get_item_level(current_item) < 2:
            content = self.scene_editor.editor.toPlainText()
            if content.strip():
                hierarchy = self.get_item_hierarchy(current_item)
                self.model.save_summary(hierarchy, content)
        return True

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def tree_item_changed(self, current, previous):
        if previous:
            self.check_unsaved_changes(previous)
        if not current:
            self.scene_editor.editor.clear()
            self.bottom_stack.stack.setCurrentIndex(0)
            self.update_contextual_header()
            return
        self.load_current_item_content()
        self.model.unsaved_changes = False
        self.unsaved_preview = False
        self.update_contextual_header()

    def update_contextual_header(self):
        """Expose the next relevant action for the active workspace and selection."""
        if not hasattr(self, "project_tree") or self.side_bar.currentWidget() != self.project_tree:
            self.complete_item_button.setVisible(False)
            return
        current_item = self.project_tree.tree.currentItem()
        if current_item is None:
            self.complete_item_button.setVisible(False)
            return
        level = self.project_tree.get_item_level(current_item)
        item_kind = ("ato", "capítulo", "cena")[min(level, 2)]
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole) or {}
        completed = item_data.get("status") == "Final Draft"
        self.complete_item_button.setText("Reabrir {}".format(item_kind) if completed else "Concluir {}".format(item_kind))
        self.complete_item_button.setToolTip(
            "Marque este {} como concluído.".format(item_kind)
            if not completed else "Marque este {} como em andamento novamente.".format(item_kind)
        )
        self.complete_item_button.setVisible(True)

    def toggle_current_item_completion(self):
        current_item = self.project_tree.tree.currentItem()
        if current_item is None:
            return
        item_data = current_item.data(0, Qt.ItemDataRole.UserRole) or {}
        new_status = "In Progress" if item_data.get("status") == "Final Draft" else "Final Draft"
        self.set_scene_status(current_item, new_status)
        self.update_contextual_header()

    def load_current_item_content(self):
        current = self.project_tree.tree.currentItem()
        if not current:
            return
        level = self.project_tree.get_item_level(current)
        editor = self.scene_editor.editor
        hierarchy = self.get_item_hierarchy(current)
        if level >= 2:
            content = self.model.load_scene_content(hierarchy)
            if content and content.lstrip().startswith("<"):
                editor.setHtml(content)
            elif content:
                editor.setPlainText(content)
            else:
                editor.clear()
            editor.setPlaceholderText(_("Enter scene content..."))
            self.bottom_stack.stack.setCurrentIndex(1)
        else:
            content = self.model.load_summary(hierarchy)
            if content and content.lstrip().startswith("<"):
                editor.setHtml(content)
            elif content:
                editor.setPlainText(content)
            else:
                editor.clear()
            editor.setPlaceholderText(_("Enter summary for {}...").format(current.text(0)))
            self.bottom_stack.stack.setCurrentIndex(0)
        self.update_setting_tooltips()
        self.scene_editor.update_toolbar_state()

    def get_item_hierarchy(self, item):
        hierarchy = []
        current = item
        while current:
            hierarchy.insert(0, current.text(0).strip())
            current = current.parent()
        return hierarchy

    def get_current_scene_hierarchy(self):
        current_item = self.project_tree.tree.currentItem()
        if not current_item:
            return None
        level = self.project_tree.get_item_level(current_item)
        if level < 2:
            return None
        return self.get_item_hierarchy(current_item)

    def set_scene_status(self, item, new_status):
        english_status = ProjectTreeWidget.REVERSE_STATUS_MAP.get(new_status, new_status)
        scene_data = item.data(0, Qt.ItemDataRole.UserRole) or {"name": item.text(0)}
        scene_data["status"] = english_status
        item.setData(0, Qt.ItemDataRole.UserRole, scene_data)
        self.project_tree.assign_item_icon(item, self.project_tree.get_item_level(item))
        self.model.update_structure(self.project_tree.tree)

    def manual_save_scene(self):
        current_item = self.project_tree.tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, _("Manual Save"), _("Please select a scene for manual save."))
            return
        content = self.scene_editor.editor.toHtml()
        if not content.strip():
            QMessageBox.warning(self, _("Manual Save"), _("There is no content to save."))
            return
        hierarchy = self.get_item_hierarchy(current_item)

        type_str = 'Scene'
        if self.project_tree.get_item_level(current_item) < 2:
            type_str = 'Summary'
            filepath = self.model.save_summary_to_file(hierarchy, content)
        else:
            filepath = self.model.save_scene(hierarchy, content)
        if filepath:
            self.update_save_status(_("{} manually saved").format(type_str))
            self.model.unsaved_changes = False

    def autosave_scene(self, current_item=None):
        if not current_item:
            current_item = self.project_tree.tree.currentItem()
        if not current_item or self.project_tree.get_item_level(current_item) < 2:
            return
        content = self.scene_editor.editor.toHtml()
        if not content.strip():
            return
        hierarchy = self.get_item_hierarchy(current_item)
        filepath = self.model.save_scene(hierarchy, content, expected_project_name=self.model.project_name)
        if filepath:
            self.update_save_status(_("Scene autosaved"))
            self.model.unsaved_changes = False

    def update_save_status(self, message):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.last_save_label.setText(_("Last Saved: {}").format(now))
        self.statusBar().showMessage(message, 3000)

    def autosave_preview(self):
        pass

    def on_oh_shit(self):
        current_item = self.project_tree.tree.currentItem()
        if not current_item:
            QMessageBox.warning(self, _("Backup Versions"), _("Please select an item to view backups."))
            return
        level = self.project_tree.get_item_level(current_item)
        hierarchy = self.get_item_hierarchy(current_item)
        is_scene = level >= 2
        backup_file_path = show_backup_dialog(
            self,
            self.model.project_name,
            current_item.text(0),
            hierarchy,
            is_scene
        )
        if backup_file_path:
            with open(backup_file_path, encoding="utf-8") as f:
                content = f.read()
            editor = self.scene_editor.editor
            if backup_file_path.endswith(".html"):
                editor.setHtml(content)
            else:
                editor.setPlainText(content)
            self.model.unsaved_changes = True
            QMessageBox.information(self, _("Backup Loaded"), _("Backup loaded from:\n{}").format(backup_file_path))

    def handle_pov_change(self, index):
        value = self.bottom_stack.pov_combo.currentText()
        if value == _("Custom..."):
            custom, ok = QInputDialog.getText(self, _("Custom POV"), _("Enter custom POV:"), text=self.model.settings["global_pov"])
            if ok and custom.strip():
                value = custom.strip()
                combo = self.bottom_stack.pov_combo
                if combo.findText(value) == -1:
                    combo.blockSignals(True)
                    combo.insertItem(0, value)
                    combo.setCurrentText(value)
                    combo.blockSignals(False)
                else:
                    combo.blockSignals(True)
                    combo.setCurrentText(value)
                    combo.blockSignals(False)
            else:
                combo = self.bottom_stack.pov_combo
                combo.blockSignals(True)
                combo.setCurrentText(self.model.settings["global_pov"])
                combo.blockSignals(False)
                return
        self.model.settings["global_pov"] = value
        self.update_setting_tooltips()
        self.model.save_settings()

    def handle_tense_change(self, index):
        value = self.bottom_stack.tense_combo.currentText()
        if value == _("Custom..."):
            custom, ok = QInputDialog.getText(self, pgettext("verb_tense", "Custom Tense"), pgettext("verb_tense", "Enter custom Tense:"), text=self.model.settings["global_tense"])
            if ok and custom.strip():
                value = custom.strip()
                if self.bottom_stack.tense_combo.findText(value) == -1:
                    self.bottom_stack.tense_combo.insertItem(0, value)
            else:
                self.bottom_stack.tense_combo.setCurrentText(self.model.settings["global_tense"])
                return
        self.model.settings["global_tense"] = value
        self.update_setting_tooltips()
        self.model.save_settings()

    def update_setting_tooltips(self):
        self.bottom_stack.pov_combo.setToolTip(_("POV: {}").format(self.model.settings['global_pov']))
        self.bottom_stack.pov_character_combo.setToolTip(_("POV Character: {}").format(self.model.settings['global_pov_character']))
        self.bottom_stack.tense_combo.setToolTip(pgettext("verb_tense", "Tense: {}").format(self.model.settings['global_tense']))

    def send_prompt(self):
        action_beats = self.bottom_stack.prompt_input.toPlainText().strip()
        if not action_beats:
            QMessageBox.warning(self, _("LLM Prompt"), _("Please enter some action beats before sending."))
            return
        prose_config = self.bottom_stack.prose_prompt_panel.get_prompt()
        if not prose_config:
            QMessageBox.warning(self, _("LLM Prompt"), _("Please select a prompt."))
            return
        overrides = self.bottom_stack.prose_prompt_panel.get_overrides()
        additional_vars = self.bottom_stack.get_additional_vars()
        current_scene_text = self.scene_editor.editor.toPlainText().strip() if self.project_tree.tree.currentItem() and self.project_tree.get_item_level(self.project_tree.tree.currentItem()) >= 2 else None
        extra_context = self.bottom_stack.context_panel.get_selected_context_text()
        final_prompt = prompt_handler.assemble_final_prompt(prose_config, action_beats, additional_vars, current_scene_text, extra_context)
        self.bottom_stack.preview_text.clear()
        self.bottom_stack.send_button.setEnabled(False)
        self.bottom_stack.preview_text.setReadOnly(True)
        QApplication.processEvents()
        self.stop_llm()
        self.worker = LLMWorker(final_prompt, overrides)
        self.worker.data_received.connect(self.update_text)
        self.worker.finished.connect(self.on_finished)
        self.worker.token_limit_exceeded.connect(self.handle_token_limit_error)
        self.worker.start()

    def handle_token_limit_error(self, error_msg):
        self.bottom_stack.send_button.setEnabled(True)
        current_item = self.project_tree.tree.currentItem()
        level = self.project_tree.get_item_level(current_item) if current_item else -1
        if current_item and level < 2 and current_item.data(0, Qt.ItemDataRole.UserRole).get("summary"):
            summary = current_item.data(0, Qt.ItemDataRole.UserRole)["summary"]
            self.retry_with_summary(summary)
            return
        self.statusBar().showMessage(_("Generating summary to fit token limit…"))
        self.bottom_stack.summary_controller.create_summary()
        QTimer.singleShot(30000, lambda: self.retry_with_auto_summary())

    def retry_with_summary(self, summary):
        additional_vars = {
            "pov": self.model.settings["global_pov"] or _("Third Person"),
            "pov_character": self.model.settings["global_pov_character"] or _("Character"),
            "tense": self.model.settings["global_tense"] or _("Present Tense"),
        }
        action_beats = self.bottom_stack.prompt_input.toPlainText().strip()
        prose_config = self.bottom_stack.prose_prompt_panel.get_prompt()
        final_prompt = prompt_handler.assemble_final_prompt(
            prose_config.get("text"),
            action_beats, additional_vars,
            summary,
            None
        )
        self.bottom_stack.preview_text.clear()
        self.bottom_stack.preview_text.setReadOnly(True)
        self.worker = LLMWorker(final_prompt, prose_config)
        self.worker.data_received.connect(self.update_text)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.cleanup_worker)
        self.worker.token_limit_exceeded.connect(self.show_token_limit_dialog)
        self.worker.start()

    def retry_with_auto_summary(self):
        summary = self.scene_editor.editor.toPlainText().strip()
        self.bottom_stack.preview_text.setPlainText(summary)
        self.statusBar().showMessage(_("Summary generated. Edit if needed, then resend."))

    def show_token_limit_dialog(self, error_msg):
        prose_config = self.bottom_stack.prose_prompt_panel.get_prompt()
        max_tokens = prose_config.get("max_tokens", 2000)
        dialog = TokenLimitDialog(error_msg, self.bottom_stack.preview_text.toPlainText(), max_tokens, parent=self)
        dialog.use_summary.connect(self.retry_with_summary)
        dialog.truncate_story.connect(self.retry_with_truncated_story)
        dialog.exec_()

    def retry_with_truncated_story(self):
        full_text = self.scene_editor.editor.toPlainText()
        prose_config = self.bottom_stack.prose_prompt_panel.get_prompt()
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(full_text)
        max_tokens = prose_config.get("max_tokens", 2000) * 0.5
        truncated = encoding.decode(tokens[-int(max_tokens):])
        self.retry_with_summary(truncated)

    def update_text(self, text):
        cursor = self.bottom_stack.preview_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.bottom_stack.preview_text.setTextCursor(cursor)
        self.bottom_stack.preview_text.insertPlainText(text)

    def cleanup_worker(self):
        logging.debug(f"Starting cleanup_worker, worker: {id(self.worker) if self.worker else None}")
        try:
            if self.worker:
                worker_id = id(self.worker)
                if self.worker.isRunning():
                    logging.debug(f"Stopping worker {worker_id}")
                    self.worker.stop()
                    self.worker.wait(5000)
                    if self.worker.isRunning():
                        logging.warning(f"Worker {worker_id} did not stop in time; skipping termination")
                try:
                    logging.debug(f"Disconnecting signals for worker {worker_id}")
                    self.worker.data_received.disconnect()
                    self.worker.finished.disconnect()
                    self.worker.token_limit_exceeded.disconnect()
                except TypeError as e:
                    logging.debug(f"Signal disconnection error for worker {worker_id}: {e}")
                logging.debug(f"Scheduling worker {worker_id} for deletion")
                self.worker.deleteLater()
                self.worker = None
        except Exception as e:
            logging.error(f"Error cleaning up LLMWorker: {e}", exc_info=True)
            QMessageBox.critical(self, _("Thread Error"), _("An error occurred while stopping the LLM thread: {}").format(str(e)))

    def on_finished(self):
        self.bottom_stack.send_button.setEnabled(True)
        self.bottom_stack.preview_text.setReadOnly(False)
        raw_text = self.bottom_stack.preview_text.toPlainText()
        if not raw_text.strip():
            QMessageBox.warning(self, _("LLM Response"), _("The LLM did not return any text. Possible token limit reached or an error occurred."))
            return
        formatted_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", raw_text)
        formatted_text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", formatted_text)
        formatted_text = formatted_text.replace("\n", "<br>")
        self.bottom_stack.preview_text.setHtml(formatted_text)
        logging.debug(f"Active threads: {threading.enumerate()}")

    def stop_llm(self):
        logging.debug(f"Starting stop_llm, worker: {id(self.worker) if self.worker else None}")
        try:
            if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
                logging.debug("Calling worker.stop()")
                self.worker.stop()
                logging.debug("Calling WWApiAggregator.interrupt()")
                WWApiAggregator.interrupt()
            self.bottom_stack.send_button.setEnabled(True)
            self.bottom_stack.preview_text.setReadOnly(False)
            logging.debug("Calling cleanup_worker")
            self.cleanup_worker()
        except Exception as e:
            logging.error(f"Error in stop_llm: {e}", exc_info=True)
            QMessageBox.critical(self, _("Error"), _("An error occurred while stopping the LLM: {}").format(str(e)))

    def apply_preview(self):
        try:
            preview = self.bottom_stack.preview_text.toHtml().strip()
            if not preview:
                QMessageBox.warning(self, _("Apply Preview"), _("No preview text to apply."))
                return
            prompt_block = None
            if self.bottom_stack.include_prompt_checkbox.isChecked():
                prompt = self.bottom_stack.prompt_input.toPlainText().strip()
                if prompt:
                    prompt_block = f"\n{'_' * 10}\n{prompt}\n{'_' * 10}\n"
            cursor = self.scene_editor.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if prompt_block:
                cursor.insertText(prompt_block)
            cursor.insertHtml(preview)
            self.scene_editor.editor.moveCursor(QTextCursor.MoveOperation.End)
            self.bottom_stack.preview_text.clear()
            self.unsaved_preview = False
            self.model.unsaved_changes = True
        except Exception as e:
            QMessageBox.warning(self, _("Apply Preview"), _("Error: {}").format(str(e)))

    def toggle_bold(self):
        cursor = self.scene_editor.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if self.scene_editor.editor.fontWeight() == QFont.Weight.Bold else QFont.Weight.Bold)
        cursor.mergeCharFormat(fmt)
        self.scene_editor.editor.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        cursor = self.scene_editor.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.scene_editor.editor.fontItalic())
        cursor.mergeCharFormat(fmt)
        self.scene_editor.editor.mergeCurrentCharFormat(fmt)

    def toggle_underline(self):
        cursor = self.scene_editor.editor.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.scene_editor.editor.fontUnderline())
        cursor.mergeCharFormat(fmt)
        self.scene_editor.editor.mergeCurrentCharFormat(fmt)

    def toggle_color(self):
        result = self.scene_editor.color_manager.choose_color(self.scene_editor)
        if not result:
            return
        fg, bg = result
        self.scene_editor.color_manager.apply_color_to_selection(
            self.scene_editor.editor, fg, bg
        )

    def align_left(self):
        self.scene_editor.editor.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def align_center(self):
        self.scene_editor.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def align_right(self):
        self.scene_editor.editor.setAlignment(Qt.AlignmentFlag.AlignRight)

    def set_font_size(self, size):
        fmt = QTextCharFormat()
        fmt.setFontPointSize(float(size))
        self.apply_typography_format(fmt)

    def update_font_family(self, font):
        fmt = QTextCharFormat()
        fmt.setFontFamilies([font.family()])
        self.apply_typography_format(fmt)

    def apply_typography_format(self, text_format):
        """Apply a font property to the chosen selection, open text, or manuscript."""
        editor = self.scene_editor.editor
        scope = self.scene_editor.current_typography_scope()
        cursor = editor.textCursor()
        if scope == "selection":
            if not cursor.hasSelection():
                self.statusBar().showMessage("Selecione um trecho ou escolha Texto aberto / Todo o documento.", 4500)
                return
            cursor.mergeCharFormat(text_format)
            editor.setTextCursor(cursor)
            self.model.unsaved_changes = True
            return

        if scope == "open":
            if not editor.toPlainText().strip():
                self.statusBar().showMessage("Não há texto aberto para formatar.", 3500)
                return
            original_cursor = editor.textCursor()
            full_text_cursor = QTextCursor(editor.document())
            full_text_cursor.select(QTextCursor.SelectionType.Document)
            full_text_cursor.mergeCharFormat(text_format)
            editor.setTextCursor(original_cursor)
            self.model.unsaved_changes = True
            self.statusBar().showMessage("Tipografia aplicada ao texto aberto.", 3000)
            return

        self.apply_typography_to_manuscript(text_format)

    def apply_typography_to_manuscript(self, text_format):
        """Apply a character format to every stored scene while preserving the open editor."""
        current_hierarchy = self.get_current_scene_hierarchy()
        formatted_scenes = 0

        if current_hierarchy and self.scene_editor.editor.toPlainText().strip():
            full_text_cursor = QTextCursor(self.scene_editor.editor.document())
            full_text_cursor.select(QTextCursor.SelectionType.Document)
            full_text_cursor.mergeCharFormat(text_format)
            self.model.save_scene(current_hierarchy, self.scene_editor.editor.toHtml())
            self.model.unsaved_changes = False
            formatted_scenes += 1

        def walk_scenes(nodes, parent_hierarchy):
            for node in nodes:
                hierarchy = parent_hierarchy + [node.get("name", "")]
                if node.get("scenes"):
                    yield from walk_scenes(node["scenes"], hierarchy)
                elif len(hierarchy) >= 3:
                    yield hierarchy
                if node.get("chapters"):
                    yield from walk_scenes(node["chapters"], hierarchy)

        for hierarchy in walk_scenes(self.model.structure.get("acts", []), []):
            if hierarchy == current_hierarchy:
                continue
            content = self.model.load_scene_content(hierarchy)
            if not content or not content.strip():
                continue
            document = QTextDocument()
            if content.lstrip().startswith("<"):
                document.setHtml(content)
            else:
                document.setPlainText(content)
            document_cursor = QTextCursor(document)
            document_cursor.select(QTextCursor.SelectionType.Document)
            document_cursor.mergeCharFormat(text_format)
            if self.model.save_scene(hierarchy, document.toHtml()):
                formatted_scenes += 1

        self.statusBar().showMessage(
            "Tipografia aplicada a {} cena(s) da obra.".format(formatted_scenes), 4500
        )

    def toggle_tts(self):
        if self.tts_playing:
            WW_TTSManager.stop()
            self.tts_playing = False
            self.scene_editor.tts_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/play-circle.svg"))
        else:
            cursor = self.scene_editor.editor.textCursor()
            text = cursor.selectedText() if cursor.hasSelection() else self.scene_editor.editor.toPlainText()
            start_position = 0 if cursor.hasSelection() else cursor.position()
            if not text.strip():
                QMessageBox.warning(self, _("TTS Warning"), _("There is no text to read."))
                return
            self.tts_playing = True
            self.scene_editor.tts_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/stop-circle.svg"))
            WW_TTSManager.speak(text, start_position=start_position, on_complete=self.tts_completed)

    def tts_completed(self):
        self.tts_playing = False
        self.scene_editor.tts_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/play-circle.svg"))

    def open_focus_mode(self):
        scene_text = self.scene_editor.editor.toPlainText()
        image_directory = os.path.join(os.getcwd(), "assets", "backgrounds")
        self.focus_window = FocusMode(image_directory, scene_text, theme_name=self.current_theme, scene_html=self.scene_editor.editor.toHtml())
        self.focus_window.on_close = self.focus_mode_closed
        self.focus_window.showFullScreen()
        self.focus_window.raise_()
        self.focus_window.activateWindow()

    def focus_mode_closed(self, updated_text):
        editor = self.scene_editor.editor
        if updated_text == editor.toHtml():
            return
        cursor = QTextCursor(editor.document())
        cursor.select(QTextCursor.Document)
        cursor.beginEditBlock()
        cursor.insertHtml(updated_text)
        cursor.endEditBlock()
        editor.setTextCursor(cursor)

    def open_analysis_editor(self):
        """Open the complete literary revision panel in the sidebar."""
        if not self.activity_bar.revision_action.isChecked():
            self.activity_bar.revision_action.trigger()
        else:
            self.revision_panel.run_analysis()

    def open_continuity_checker(self):
        """Open the project-level consistency review for prose, Universe, and timeline."""
        self.check_unsaved_changes()
        from compendium.continuity import ContinuityDialog

        if not hasattr(self, "continuity_dialog"):
            self.continuity_dialog = ContinuityDialog(self)
        else:
            self.continuity_dialog.refresh()
        self.continuity_dialog.show()
        self.continuity_dialog.raise_()
        self.continuity_dialog.activateWindow()

    def open_progress_dashboard(self):
        """Open the writing goals and structure progress dashboard via the toolbar."""
        if not self.activity_bar.progress_action.isChecked():
            self.activity_bar.progress_action.trigger()

    def open_web_llm(self):
        try:
            from util.web_llm import MainWindow
        except ImportError as e:
            QMessageBox.warning(self, "Dependência ausente", f"Não foi possível abrir a pesquisa por IA: {e}")
            return

        self.web_llm = MainWindow()
        self.web_llm.show()


    def open_ia_window(self):
        try:
            from util.ia_window import IAWindow
        except ImportError as e:
            QMessageBox.warning(self, "Dependência ausente", f"Não foi possível abrir a pesquisa no acervo: {e}")
            return

        self.ia_window = IAWindow()
        self.ia_window.show()

    def analysis_save_callback(self, updated_text):
        self.scene_editor.editor.setPlainText(updated_text)
        self.manual_save_scene()

    def open_compendium(self):
        self.toggle_compendium_view(True)

    def repopulate_prompts(self):
        self.bottom_stack.prose_prompt_panel.repopulate_prompts()

    def open_workshop(self):
        from workshop.workshop_controller import WorkshopController

        self.workshop_window = WorkshopController(self)
        self.workshop_window.view.show()

    def rewrite_selected_text(self):
        cursor = self.scene_editor.editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.warning(self, _("Rewrite"), _("No text selected to rewrite."))
            return
        selected_text = cursor.selectedText()
        dialog = RewriteDialog(self.model.project_name, selected_text, self)
        if dialog.exec_() == QDialog.DialogCode.Accepted:
            cursor.insertText(dialog.rewritten_text)
            self.scene_editor.editor.setTextCursor(cursor)

    def update_pov_character_dropdown(self):
        characters = []
        try:
            characters = self.model.compendium.get_characters()
        except Exception as e:
            print(f"Error loading characters from compendium: {e}")
        if not characters:
            characters = ["Alice", "Bob", "Charlie"]
        characters.append(_("Custom..."))
        self.bottom_stack.pov_character_combo.blockSignals(True)
        self.bottom_stack.pov_character_combo.clear()
        self.bottom_stack.pov_character_combo.addItems(characters)
        self.bottom_stack.pov_character_combo.blockSignals(False)

    def restore_pov_character(self, previous_pov, previous_index):
        combo = self.bottom_stack.pov_character_combo
        index = combo.findText(previous_pov)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            if combo.count() == 2 and combo.itemText(0) != _("Custom..."):
                combo.setCurrentIndex(0)
            elif combo.count() > previous_index: # possibly renamed character
                combo.blockSignals(True)
                combo.setCurrentIndex(previous_index)
                combo.blockSignals(False)
            else:
                combo.setCurrentIndex(combo.findText(_("Custom...")))

    def update_icons(self):
        tint_str = ThemeManager.ICON_TINTS.get(self.current_theme, "black")
        self.icon_tint = QColor(tint_str)
        self.global_toolbar.update_tint(self.icon_tint)
        self.scene_editor.update_tint(self.icon_tint)
        self.bottom_stack.update_tint(self.icon_tint)
        self.activity_bar.update_tint(self.icon_tint)
        self.search_panel.update_tint(self.icon_tint)
        self.project_tree.assign_all_icons()

    def refresh_category_backgrounds(self):
        """Refresh category background colors when the setting changes."""
        self.project_tree.assign_all_icons()

    def change_theme(self, new_theme):
        self.current_theme = new_theme
        stylesheet = ThemeManager.get_stylesheet(new_theme)
        self.setStyleSheet(stylesheet)
        ThemeManager.clear_icon_cache()
        self.update_icons()

    def on_editor_text_changed(self):
        text = self.scene_editor.editor.toPlainText()
        self.word_count_label.setText("{} palavras".format(len(text.split())))
        self.model.unsaved_changes = True

    def refresh_universe_assistance(self):
        """Refresh entity links and completion candidates after the Universe changes."""
        self.scene_editor.set_universe_entries(self.model.compendium.get_entry_index())

    def add_text_to_universe(self, name, source_paragraph):
        """Create a structured universe entry from a writer-selected word or phrase."""
        name = " ".join(name.split()).strip()
        if len(name) < 2:
            self.statusBar().showMessage("Selecione uma palavra ou expressão para adicionar ao Universo.", 3500)
            return
        existing = self.model.compendium.get_entry_index()
        if any(entry["name"].casefold() == name.casefold() for entry in existing):
            self.statusBar().showMessage("“{}” já existe no Universo.".format(name), 3500)
            return

        data = self.model.compendium.load_data()
        categories = [category.get("name", "") for category in data.get("categories", []) if category.get("name")]
        category_name, accepted = QInputDialog.getItem(
            self,
            "Adicionar ao Universo",
            "Categoria para “{}”:".format(name),
            categories,
            0,
            False,
        )
        if not accepted or not category_name:
            return
        category = next((item for item in data["categories"] if item.get("name") == category_name), None)
        subcategory_name = ""
        subcategories = [item.get("name", "") for item in category.get("subcategories", [])] if category else []
        if subcategories:
            choices = ["Sem subcategoria", *subcategories]
            chosen_subcategory, accepted = QInputDialog.getItem(
                self,
                "Adicionar ao Universo",
                "Subcategoria:",
                choices,
                0,
                False,
            )
            if not accepted:
                return
            subcategory_name = "" if chosen_subcategory == "Sem subcategoria" else chosen_subcategory

        source_text = "Citado na cena: {}".format(source_paragraph) if source_paragraph else ""
        if self.model.compendium.add_entry(name, category_name, subcategory_name, source_text):
            self.compendium_panel.populate_compendium()
            self.refresh_universe_assistance()
            self.statusBar().showMessage(
                "“{}” foi adicionado ao Universo. Abra Universo para completar sua ficha.".format(name), 4500
            )
        else:
            self.statusBar().showMessage("Não foi possível adicionar “{}” ao Universo.".format(name), 4000)

    def on_preview_text_changed(self):
        preview_text = self.bottom_stack.preview_text.toPlainText().strip()
        self.unsaved_preview = bool(preview_text)

    def load_prompt_input(self):
        prompt_input_file = WWSettingsManager.get_project_path(self.model.project_name, "action-beat.txt")
        if os.path.exists(prompt_input_file):
            try:
                with open(prompt_input_file, encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                print(f"Error loading prompt input: {e}")
        return ""

    def on_prompt_input_text_changed(self):
        if self.model.autosave_enabled:
            if not hasattr(self, 'prompt_input_timer'):
                self.prompt_input_timer = QTimer(self)
                self.prompt_input_timer.setSingleShot(True)
                self.prompt_input_timer.timeout.connect(self.save_prompt_input)
            self.prompt_input_timer.start(5000)

    def save_prompt_input(self):
        project_folder = WWSettingsManager.get_project_path(self.model.project_name)
        os.makedirs(project_folder, exist_ok=True)
        prompt_input_file = os.path.join(project_folder, "action-beat.txt")
        try:
            with open(prompt_input_file, "w", encoding="utf-8") as f:
                f.write(self.bottom_stack.prompt_input.toPlainText())
        except Exception as e:
            print(f"Error saving prompt input: {e}")

    def clear_search_highlights(self):
        if hasattr(self, 'search_panel'):
            self.search_panel.clear_extra_selections()

if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ProjectWindow("My Awesome Project", None)
    window.show()
    sys.exit(app.exec_())
