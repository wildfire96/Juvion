from gettext import gettext as _
from typing import TYPE_CHECKING

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QAction, QToolBar, QVBoxLayout, QWidget

from settings.theme_manager import ThemeManager

if TYPE_CHECKING:
    from .project_window import ProjectWindow


class GlobalToolbar(QWidget):
    """Global actions toolbar at the top of the window."""
    def __init__(self, controller: "ProjectWindow", tint_color: QColor = QColor("black")):
        super().__init__()
        self.controller = controller  # Reference to ProjectWindow for callbacks
        self.tint_color = tint_color
        self.toolbar = QToolBar(_("Global Actions"))
        self.toolbar.setObjectName("GlobalActionsToolBar")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(self.toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        self.toolbar.setStyleSheet("QToolBar#GlobalActionsToolBar { padding: 2px 6px; font-size: 12px; } QToolButton { font-size: 12px; padding: 3px 6px; }")
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Create actions and store references
        self.workshop_action = self.add_action(
            "assets/icons/message-square.svg", "Conversar com a Musa",
            "Planeje, pesquise e tire dúvidas sobre a obra em uma conversa assistida.", self.controller.open_workshop,
        )
        self.web_llm_action = self.add_action(
            "assets/icons/wikidata.svg", "Pesquisar com IA",
            "Abra a ferramenta de pesquisa assistida por IA.", self.controller.open_web_llm,
        )
        self.ia_action = self.add_action(
            "assets/icons/arch.svg", "Pesquisar no acervo",
            "Pesquise obras e materiais no Internet Archive.", self.controller.open_ia_window,
        )
        self.focus_mode_action = self.add_action(
            "assets/icons/maximize-2.svg", "Modo foco",
            "Escreva sem distrações. Atalho: F11.", self.controller.open_focus_mode,
        )
        self.continuity_action = self.add_action(
            "assets/icons/alert-triangle.svg", "Verificar continuidade",
            "Procure fichas ausentes, relações quebradas e conflitos simples da Linha do tempo.",
            self.controller.open_continuity_checker,
        )
        self.progress_action = self.add_action(
            "assets/icons/bar-chart-2.svg", "Progresso da obra",
            "Acompanhe palavras, metas e a conclusão de atos, capítulos e cenas.",
            self.controller.open_progress_dashboard,
        )

    def add_action(self, icon_path, label, tooltip, callback):
        action = QAction(ThemeManager.get_tinted_icon(icon_path, self.tint_color), label, self)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.triggered.connect(callback)
        self.toolbar.addAction(action)
        return action

    def update_tint(self, tint_color):
        """Update icon tints when theme changes."""
        self.tint_color = tint_color
        self.workshop_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/message-square.svg", tint_color))
        self.web_llm_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/wikidata.svg", tint_color))
        self.ia_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/arch.svg", tint_color))
        self.focus_mode_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/maximize-2.svg", tint_color))
        self.continuity_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/alert-triangle.svg", tint_color))
        self.progress_action.setIcon(ThemeManager.get_tinted_icon("assets/icons/bar-chart-2.svg", tint_color))
