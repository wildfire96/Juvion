import re
import uuid
from gettext import gettext as _

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from compendium.compendium_manager import CompendiumEventBus, CompendiumManager
from settings.theme_manager import ThemeManager

DEBUG = False

class EnhancedCompendiumWindow(QMainWindow):
    """
    Enhanced Compendium Window - A comprehensive interface for managing compendium data
    with categories, entries, tags, relationships, details, and images.
    """

    NOTEBOOK_BASE_FIELDS = (
        ("descricao", "Descrição", "Explique o essencial desta ficha."),
        ("papel_na_historia", "Papel na história", "Como esta ficha move a obra?"),
        ("estado_atual", "Estado atual", "O que é verdade sobre esta ficha neste momento?"),
    )
    NOTEBOOK_CATEGORY_FIELDS = {
        "personagens": (
            ("nome_completo", "Nome completo", "Nomes, títulos ou apelidos."),
            ("idade", "Idade", "Idade, fase de vida ou passagem de tempo relevante."),
            ("arquetipo", "Arquétipo", "Função dramática ou imagem central deste personagem."),
            ("aparencia", "Aparência", "Traços físicos e presença."),
            ("caracteristicas", "Características", "Traços marcantes, cicatrizes ou condições físicas."),
            ("vestimenta", "Vestimenta", "Roupas, símbolos e objetos que carrega."),
            ("personalidade", "Personalidade", "Qualidades, falhas e maneirismos."),
            ("objetivo", "Objetivo", "O que esta pessoa quer?"),
            ("conflito", "Conflito", "O que impede ou complica esse objetivo?"),
            ("arco", "Arco", "Como muda ao longo da narrativa?"),
            ("acoes_principais", "Ações principais", "Decisões e feitos que definem sua participação."),
        ),
        "worldbuilding": (
            ("geografia", "Geografia", "Terreno, limites e pontos de referência."),
            ("cultura", "Cultura", "Costumes, valores e vida cotidiana."),
            ("historia", "História", "Origem, acontecimentos e memórias importantes."),
            ("regras", "Regras", "Leis naturais, sociais ou fantásticas."),
        ),
        "organizações": (
            ("proposito", "Propósito", "Por que este grupo existe?"),
            ("lideranca", "Liderança", "Quem decide e como o poder funciona?"),
            ("membros", "Membros", "Quem pertence ao grupo?"),
            ("sede", "Sede", "Onde atua ou se reúne?"),
            ("valores", "Valores", "Crenças, regras e limites."),
        ),
        "seres": (
            ("origem", "Origem", "De onde vem este povo ou ser?"),
            ("caracteristicas", "Características", "Traços físicos, mentais ou sociais."),
            ("costumes", "Costumes", "Hábitos, rituais e tabus."),
            ("habilidades", "Habilidades", "Capacidades marcantes."),
        ),
        "sistemas e poderes": (
            ("funcionamento", "Funcionamento", "Como este sistema funciona na prática?"),
            ("limites", "Limites e custos", "O que não pode fazer e qual é o preço?"),
            ("origem_poder", "Origem", "De onde vem esta força ou tecnologia?"),
            ("usuarios", "Usuários", "Quem pode usar e como aprende?"),
        ),
        "itens e artefatos": (
            ("origem_item", "Origem", "Quem criou ou encontrou este item?"),
            ("propriedades", "Propriedades", "O que faz, guarda ou permite?"),
            ("limites_item", "Limites e riscos", "Custos, fraquezas e consequências."),
            ("portadores", "Portadores", "Quem já usou ou procura este item?"),
        ),
        "histórias e eventos": (
            ("quando", "Quando", "Data, era ou período no universo."),
            ("causas", "Causas", "O que levou a este acontecimento?"),
            ("consequencias", "Consequências", "O que mudou depois?"),
            ("envolvidos", "Envolvidos", "Pessoas, povos ou grupos importantes."),
        ),
        "conceitos & lore": (
            ("definicao", "Definição", "O que este conceito significa?"),
            ("origem_lore", "Origem", "Como surgiu ou foi descoberto?"),
            ("interpretacoes", "Interpretações", "Quem acredita, contesta ou teme isso?"),
        ),
        "criaturas": (
            ("habitat", "Habitat", "Onde vive ou aparece?"),
            ("comportamento", "Comportamento", "Como age, caça ou se comunica?"),
            ("fraquezas", "Fraquezas", "Como evitar, conter ou derrotar?"),
        ),
        "narrativa": (
            ("funcao", "Função narrativa", "Que efeito produz na história?"),
            ("ponto_de_vista", "Ponto de vista", "Quem observa ou conta isso?"),
            ("tom", "Tom", "Qual sensação deve transmitir?"),
        ),
    }
    NOTEBOOK_SUBCATEGORY_FIELDS = {
        "protagonistas": (("ferida", "Ferida central", "Uma dor, crença ou falta que guia suas escolhas."),),
        "antagonistas": (("oposicao", "Estratégia de oposição", "Como se coloca contra o protagonista?"),),
        "países": (("capital", "Capital", "Cidade ou centro de poder."), ("governo", "Governo", "Forma de governo e figuras relevantes.")),
        "lugares": (("atmosfera", "Atmosfera", "Sensações, sons e imagens deste lugar."),),
        "magia": (("manifestacao", "Manifestação", "Como a magia se mostra no mundo?"),),
        "tecnologia": (("nivel_tecnologico", "Nível tecnológico", "Alcance e presença no cotidiano."),),
        "armas": (("combate", "Uso em combate", "Estilo, alcance e efeitos."),),
        "relíquias": (("lenda", "Lenda", "Histórias e crenças ligadas à relíquia."),),
    }
    def __init__(self, parent=None):
        """
        Initialize the Enhanced Compendium Window.
        
        Args:
            project_name (str): Name of the project
            parent: Parent widget
        """
        super().__init__(parent)
        self.dirty = False  # Track unsaved changes
        self.project_name = "default" # project_name is set when we become visible
        self.controller = parent
        self.event_bus = CompendiumEventBus.get_instance()
        self.manager = CompendiumManager(self.project_name, event_bus=self.event_bus)
        self.event_bus.add_updated_listener(self.on_compendium_updated)
        self.compendium_data = {}
        self.graph_window = None
        self.timeline_window = None

        # 1) Create a QToolBar at the top
        self.toolbar = self.create_toolbar()
        self.addToolBar(self.toolbar)

        # 2) Set up the central widget (which holds the main layout and splitter)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # 3) Create the main splitter for the rest of the UI
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.main_splitter)

        # 4) Create the left (tree), center (content/tabs), and right (tags) panels
        self.create_tree_view()
        self.create_center_panel()
        self.create_right_panel()

        # 5) Set splitter proportions
        self.main_splitter.setStretchFactor(0, 1)  # Tree view
        self.main_splitter.setStretchFactor(1, 2)  # Content panel
        self.main_splitter.setStretchFactor(2, 1)  # Right panel

        # 6) Set up the compendium file and populate the UI
        self.populate_compendium()
        self.connect_signals()

        # 7) Window title and size
        self.setWindowTitle("Juvion — Universo: {}".format(self.project_name))
        self.resize(900, 700)

        # 8) Populate the project combo and connect its signal
        self.populate_project_combo()

        # 9) Read saved settings
        self.read_settings()

    def read_settings(self):
        """Read window and splitter settings from QSettings."""
        settings = QSettings("MyCompany", "WritingwayProject")
        geometry = settings.value("compendium_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = settings.value("compendium_windowState")
        if window_state:
            self.restoreState(window_state)
        splitter_state = settings.value("compendium_mainSplitterState")
        if splitter_state:
            self.main_splitter.restoreState(splitter_state)

    def write_settings(self):
        """Write window and splitter settings to QSettings."""
        settings = QSettings("MyCompany", "WritingwayProject")
        settings.setValue("compendium_geometry", self.saveGeometry())
        settings.setValue("compendium_windowState", self.saveState())
        settings.setValue("compendium_mainSplitterState", self.main_splitter.saveState())

    def closeEvent(self, event):
        """Handle window close event to save settings and any unsaved changes."""
        if self.dirty and hasattr(self, 'current_entry') and hasattr(self, 'current_entry_item'):
            self.save_current_entry()
        self.write_settings()
        event.accept()

    def mark_dirty(self):
        """Mark the current entry as having unsaved changes."""
        self.dirty = True

    def create_toolbar(self):
        """Create the project selection toolbar at the top of the window."""
        toolbar = QToolBar(_("Project Toolbar"), self)
        toolbar.setObjectName("EnhToolBar_Main")
        label = QLabel("<b>Obra:</b>")
        toolbar.addWidget(label)
        self.project_combo = QComboBox()
        toolbar.addWidget(self.project_combo)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.addWidget(spacer)
        graph_action = toolbar.addAction(_("Mapa de relações"))
        graph_action.triggered.connect(self.open_universe_graph)
        timeline_action = toolbar.addAction("Linha do tempo")
        timeline_action.triggered.connect(self.open_timeline)
        return toolbar

    def open_universe_graph(self):
        """Open the visual map for the current project's universe relationships."""
        if self.graph_window is None:
            from compendium.universe_graph import UniverseGraphWindow
            self.graph_window = UniverseGraphWindow(self.project_name, self)
        else:
            self.graph_window.open_project(self.project_name)
        self.graph_window.show()
        self.graph_window.raise_()
        self.graph_window.activateWindow()

    def open_timeline(self):
        """Open the two-track timeline with the current project's scene structure."""
        from compendium.timeline import TimelineWindow
        from project_window.tree_manager import load_structure

        structure = load_structure(self.project_name)
        if self.timeline_window is None:
            self.timeline_window = TimelineWindow(self.project_name, structure, self)
        else:
            self.timeline_window.open_project(self.project_name, structure)
        self.timeline_window.show()
        self.timeline_window.raise_()
        self.timeline_window.activateWindow()

    def populate_project_combo(self, project_name=None):
        """
        Populate the project pulldown.
        
        Args:
            project_name (str, optional): Specific project to select
        """

        if project_name:
            self.project_name = project_name
        else:
            project_name = self.project_name

        self.project_combo.blockSignals(True)
        self.project_combo.clear()

        projects = self.parent().get_project_list()
        if projects:
            projects.sort()
            self.project_combo.addItems(projects)
            index = self.project_combo.findText(self.sanitize(project_name))
            if index < 0:
                self.project_combo.setCurrentIndex(0)
                self.project_name = self.project_combo.currentText()
            else:
                self.project_combo.setCurrentIndex(index)
        else:
            self.project_combo.addItem("default")
            self.project_combo.setCurrentIndex(0)
            self.project_name = "default"

        self.project_combo.blockSignals(False)
        self.project_combo.currentTextChanged.connect(self.on_project_combo_changed)
        self.setWindowTitle("Juvion — Universo: {}".format(self.project_name))

    def on_project_combo_changed(self, new_project):
        """Update the project and reload the compendium when a different project is selected."""
        self.change_project(new_project)
        self.select_first_entry()

    def select_first_entry(self):
        """Select the first non-category entry in the tree."""
        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child_item = cat_item.child(j)
                if child_item.data(0, Qt.UserRole) == "entry":
                    self.tree.setCurrentItem(child_item)
                    return
                if child_item.data(0, Qt.UserRole) == "subcategory" and child_item.childCount() > 0:
                    self.tree.setCurrentItem(child_item.child(0))
                    return

    def change_project(self, new_project):
        """Switch to a different project and reload its compendium data."""
        self.project_name = new_project
        self.manager = CompendiumManager(self.project_name, event_bus=self.event_bus)
        self.compendium_data = self.manager.load_data()
        self.setWindowTitle("Juvion — Universo: {}".format(self.project_name))
        self.populate_compendium()

    def create_tree_view(self):
        """Create the left panel: a tree view (with a search bar) for categories and entries."""
        self.tree_widget = QWidget()
        tree_layout = QVBoxLayout(self.tree_widget)
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Buscar fichas e tags…")
        tree_layout.addWidget(self.search_bar)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel(_("Universo"))
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree_layout.addWidget(self.tree)
        self.main_splitter.addWidget(self.tree_widget)

    def create_center_panel(self):
        """
        Create the center panel with a header and a tabbed view for content, details, 
        relationships, and images.
        """
        self.center_widget = QWidget()
        center_layout = QVBoxLayout(self.center_widget)

        # Header with entry name and save button
        self.header_widget = QWidget()
        header_layout = QHBoxLayout(self.header_widget)
        self.entry_name_label = QLabel("Nenhuma ficha selecionada")
        self.entry_name_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(self.entry_name_label)
        header_layout.addStretch()
        self.canon_combo = QComboBox()
        self.canon_combo.addItems(self.manager.CANON_STATUSES)
        self.canon_combo.setToolTip("Defina se esta ficha é confirmada, rumor, planejada, descartada ou contraditória.")
        header_layout.addWidget(self.canon_combo)
        self.save_button = QPushButton("Salvar ficha")
        self.save_button.setProperty("primary", True)
        self.save_button.setToolTip("Guarde o conteúdo, as relações, as tags e as notas desta ficha.")
        header_layout.addWidget(self.save_button)
        center_layout.addWidget(self.header_widget)

        self.tabs = QTabWidget()

        # Overview tab - a structured, optional notebook visible to AI
        self.overview_tab = QWidget()
        overview_layout = QVBoxLayout(self.overview_tab)
        self.notebook_context_label = QLabel("Escolha os detalhes que fazem sentido para esta ficha. Todos são opcionais.")
        self.notebook_context_label.setWordWrap(True)
        overview_layout.addWidget(self.notebook_context_label)
        self.notebook_options = QGroupBox("Adicionar detalhe")
        self.notebook_options_layout = QGridLayout(self.notebook_options)
        overview_layout.addWidget(self.notebook_options)
        self.notebook_scroll = QScrollArea()
        self.notebook_scroll.setWidgetResizable(True)
        self._reset_notebook_forms()
        overview_layout.addWidget(self.notebook_scroll, 1)
        self.tabs.addTab(self.overview_tab, "Ficha")
        self.tabs.setTabToolTip(0, "Caderno de detalhes opcionais usados como contexto pela Musa IA.")

        # Details tab - private notes not visible to AI
        self.details_editor = QTextEdit()
        self.details_editor.setPlaceholderText("Anote detalhes privados que não devem ser enviados à Musa IA.")
        self.tabs.addTab(self.details_editor, "Notas privadas")
        self.tabs.setTabToolTip(1, "Anotações só para você; não entram no contexto da Musa IA.")

        # Relationships tab
        self.relationships_tab = QWidget()
        relationships_layout = QVBoxLayout(self.relationships_tab)
        self.relationships_form = QGroupBox("Relações")
        form_layout = QFormLayout()
        self.relationship_combo = QComboBox()
        self.relationship_type = QLineEdit()
        self.relationship_canon = QComboBox()
        self.relationship_canon.addItems(self.manager.CANON_STATUSES)
        self.add_relationship_button = QPushButton("Adicionar relação")
        self.add_relationship_button.setToolTip("Conecte esta ficha a outra e descreva o vínculo entre elas.")
        form_layout.addRow("Ficha relacionada:", self.relationship_combo)
        form_layout.addRow("Tipo de relação:", self.relationship_type)
        form_layout.addRow("Cânone:", self.relationship_canon)
        form_layout.addRow(self.add_relationship_button)
        self.relationships_form.setLayout(form_layout)
        self.relationships_list = QTreeWidget()
        self.relationships_list.setHeaderLabels(["Ficha", "Relação", "Cânone"])
        relationships_layout.addWidget(self.relationships_form)
        relationships_layout.addWidget(self.relationships_list)
        self.tabs.addTab(self.relationships_tab, "Relações")

        # Images tab
        self.images_tab = QTabWidget()
        self.image_scroll = QScrollArea()
        self.image_scroll.setWidgetResizable(True)
        self.image_widget = QWidget()
        self.image_layout = QHBoxLayout(self.image_widget)
        self.image_scroll.setWidget(self.image_widget)
        self.images_tab.addTab(self.image_scroll, "Imagens")
        self.add_image_button = QPushButton("Adicionar imagem")
        self.add_image_button.setToolTip("Anexe uma imagem de referência a esta ficha.")
        images_layout = QVBoxLayout()
        images_layout.addWidget(self.images_tab)
        images_layout.addWidget(self.add_image_button)
        self.image_widget = QWidget()
        self.image_widget.setLayout(images_layout)
        self.tabs.addTab(self.image_widget, "Imagens")

        center_layout.addWidget(self.tabs)
        self.main_splitter.addWidget(self.center_widget)

    def create_right_panel(self):
        """Create the right panel for tags management."""
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        self.tags_form = QGroupBox("Tags")
        form_layout = QFormLayout()
        self.tag_input = QLineEdit()
        self.tag_color_button = QPushButton("Escolher cor")
        self.tag_color_button.setToolTip("Escolha a cor usada para identificar esta tag.")
        self.add_tag_button = QPushButton("Adicionar tag")
        self.add_tag_button.setToolTip("Adicione uma etiqueta para encontrar esta ficha depois.")
        form_layout.addRow("Tag:", self.tag_input)
        form_layout.addRow(self.tag_color_button)
        form_layout.addRow(self.add_tag_button)
        self.tags_form.setLayout(form_layout)
        self.tags_list = QListWidget()
        self.tags_list.setContextMenuPolicy(Qt.CustomContextMenu)
        right_layout.addWidget(self.tags_form)
        right_layout.addWidget(self.tags_list)
        self.main_splitter.addWidget(self.right_widget)

    def connect_signals(self):
        """Connect all necessary signals for interactive functionality."""
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.currentItemChanged.connect(self.on_item_changed)
        self.search_bar.textChanged.connect(self.filter_tree)
        self.save_button.clicked.connect(self.save_current_entry)
        self.add_tag_button.clicked.connect(self.add_tag)
        self.tag_color_button.clicked.connect(self.choose_tag_color)
        self.tags_list.customContextMenuRequested.connect(self.show_tags_context_menu)
        self.add_relationship_button.clicked.connect(self.add_relationship)
        self.relationships_list.customContextMenuRequested.connect(self.show_relationships_context_menu)
        self.add_image_button.clicked.connect(self.add_image)
        self.details_editor.textChanged.connect(self.mark_dirty)
        self.canon_combo.currentTextChanged.connect(self.mark_dirty)

    def _reset_notebook_forms(self):
        """Replace the notebook page that holds the optional fields for an entry."""
        previous_widget = self.notebook_scroll.takeWidget()
        if previous_widget:
            previous_widget.deleteLater()
        self.notebook_forms_widget = QWidget()
        self.notebook_forms_layout = QVBoxLayout(self.notebook_forms_widget)
        self.notebook_forms_layout.setContentsMargins(4, 4, 4, 4)
        self.notebook_forms_layout.setSpacing(8)
        self.notebook_empty_label = QLabel("Use um botão acima para adicionar o primeiro detalhe desta ficha.")
        self.notebook_empty_label.setWordWrap(True)
        self.notebook_forms_layout.addWidget(self.notebook_empty_label)
        self.notebook_forms_layout.addStretch()
        self.notebook_scroll.setWidget(self.notebook_forms_widget)
        self.notebook_inputs = {}
        self.notebook_forms = {}

    def _entry_notebook_fields(self, entry_item):
        """Return the optional prompts that fit the entry's category and subcategory."""
        if not entry_item:
            return []
        parent = entry_item.parent()
        subcategory = ""
        category = ""
        if parent and parent.data(0, Qt.UserRole) == "subcategory":
            subcategory = parent.text(0)
            category = parent.parent().text(0) if parent.parent() else ""
        elif parent:
            category = parent.text(0)

        fields = list(self.NOTEBOOK_BASE_FIELDS)
        fields.extend(self.NOTEBOOK_CATEGORY_FIELDS.get(category.casefold(), ()))
        fields.extend(self.NOTEBOOK_SUBCATEGORY_FIELDS.get(subcategory.casefold(), ()))
        unique_fields = []
        seen = set()
        for field in fields:
            if field[0] not in seen:
                unique_fields.append(field)
                seen.add(field[0])
        return unique_fields

    def configure_notebook(self, entry_item, values):
        """Build a category-aware notebook and restore its saved optional values."""
        self._reset_notebook_forms()
        while self.notebook_options_layout.count():
            item = self.notebook_options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fields = self._entry_notebook_fields(entry_item)
        self.notebook_field_specs = {field[0]: field for field in fields}
        if not entry_item:
            self.notebook_context_label.setText("Selecione uma ficha para montar seu caderno de detalhes.")
            self.notebook_options.setEnabled(False)
            return

        parent = entry_item.parent()
        category = parent.text(0) if parent else ""
        subcategory = ""
        if parent and parent.data(0, Qt.UserRole) == "subcategory":
            subcategory = parent.text(0)
            category = parent.parent().text(0) if parent.parent() else ""
        hierarchy = category + (" › " + subcategory if subcategory else "")
        self.notebook_context_label.setText(
            "Campos opcionais para {}. Clique em um botão para adicioná-lo ao caderno.".format(hierarchy)
        )
        self.notebook_options.setEnabled(True)
        for index, field in enumerate(fields):
            key, label, _placeholder = field
            button = QPushButton("+ " + label)
            button.setToolTip("Adicionar “{}” ao caderno desta ficha.".format(label))
            button.clicked.connect(lambda _checked, field_key=key: self.add_notebook_field(field_key))
            self.notebook_options_layout.addWidget(button, index // 3, index % 3)

        for key, value in (values or {}).items():
            if not value:
                continue
            if key not in self.notebook_field_specs:
                self.notebook_field_specs[key] = (key, key.replace("_", " ").capitalize(), "")
            self.add_notebook_field(key, str(value), focus=False)

    def add_notebook_field(self, field_key, value="", focus=True):
        """Insert one optional field into the scrollable notebook page."""
        if field_key in self.notebook_inputs:
            if focus:
                self.notebook_inputs[field_key].setFocus()
            return
        key, label, placeholder = self.notebook_field_specs[field_key]
        field_box = QGroupBox(label)
        field_layout = QVBoxLayout(field_box)
        actions = QHBoxLayout()
        hint = QLabel(placeholder)
        hint.setWordWrap(True)
        actions.addWidget(hint, 1)
        remove_button = QPushButton("Remover")
        remove_button.setToolTip("Retirar este campo do caderno.")
        remove_button.clicked.connect(lambda: self.remove_notebook_field(field_key))
        actions.addWidget(remove_button)
        field_layout.addLayout(actions)
        input_widget = QTextEdit()
        input_widget.setPlaceholderText(placeholder)
        input_widget.setPlainText(value)
        input_widget.setMinimumHeight(76)
        input_widget.textChanged.connect(self.mark_dirty)
        field_layout.addWidget(input_widget)
        self.notebook_forms_layout.insertWidget(self.notebook_forms_layout.count() - 1, field_box)
        self.notebook_empty_label.hide()
        self.notebook_inputs[field_key] = input_widget
        self.notebook_forms[field_key] = field_box
        if focus:
            input_widget.setFocus()
        self.mark_dirty()

    def remove_notebook_field(self, field_key):
        """Remove a field chosen by the writer without deleting any other detail."""
        field_box = self.notebook_forms.pop(field_key, None)
        self.notebook_inputs.pop(field_key, None)
        if field_box:
            self.notebook_forms_layout.removeWidget(field_box)
            field_box.deleteLater()
        if not self.notebook_inputs:
            self.notebook_empty_label.show()
        self.mark_dirty()

    def collect_notebook_values(self):
        """Collect non-empty optional fields for persistence and AI context."""
        return {
            key: input_widget.toPlainText().strip()
            for key, input_widget in self.notebook_inputs.items()
            if input_widget.toPlainText().strip()
        }

    def notebook_to_context(self, values):
        """Keep the structured notebook useful as readable context for the Musa IA."""
        paragraphs = []
        for key, value in values.items():
            label = self.notebook_field_specs.get(key, (key, key.replace("_", " ").capitalize(), ""))[1]
            paragraphs.append("{}: {}".format(label, value))
        return "\n\n".join(paragraphs)

    def sanitize(self, text):
        """Sanitize text by removing non-word characters for safe filenames."""
        return re.sub(r'\W+', '', text)

    def _category_data(self, category_item):
        """Return the persisted category represented by a top-level tree item."""
        if not category_item:
            return None
        return next(
            (category for category in self.compendium_data.get("categories", [])
             if category.get("name") == category_item.text(0)),
            None,
        )

    def _entries_for_parent_item(self, parent_item):
        """Return the data list that owns entries below a category or subcategory."""
        if not parent_item:
            return None
        item_type = parent_item.data(0, Qt.UserRole)
        if item_type == "category":
            category = self._category_data(parent_item)
            return category.setdefault("entries", []) if category else None
        if item_type == "subcategory":
            category = self._category_data(parent_item.parent())
            if category:
                subcategory = next(
                    (item for item in category.setdefault("subcategories", [])
                     if item.get("name") == parent_item.text(0)),
                    None,
                )
                return subcategory.setdefault("entries", []) if subcategory else None
        return None

    def _entry_data(self, entry_item):
        """Find an entry in its actual category or subcategory data container."""
        entries = self._entries_for_parent_item(entry_item.parent()) if entry_item else None
        if entries is None:
            return None
        entry_uuid = entry_item.data(2, Qt.UserRole)
        return next(
            (entry for entry in entries
             if entry.get("uuid") == entry_uuid or entry.get("name") == entry_item.text(0)),
            None,
        )

    def _all_entries(self, category):
        """Yield direct and subcategory entries from a category."""
        yield from category.get("entries", [])
        for subcategory in category.get("subcategories", []):
            yield from subcategory.get("entries", [])

    def _is_factory_category(self, category_item):
        """Keep the shared universe structure available in every project."""
        category_name = category_item.text(0).casefold()
        return any(category_name in aliases for _name, aliases, _subcategories in self.manager.UNIVERSE_CATEGORIES)

    def _is_factory_subcategory(self, subcategory_item):
        category_item = subcategory_item.parent()
        if not category_item:
            return False
        category_name = category_item.text(0).casefold()
        subcategory_name = subcategory_item.text(0).casefold()
        for _name, aliases, subcategories in self.manager.UNIVERSE_CATEGORIES:
            if category_name in aliases:
                return subcategory_name in {name.casefold() for name in subcategories}
        return False

    def populate_compendium(self):
        """Populate the tree view with compendium data from the manager."""
        selected_item_info = self.get_selected_item_info()
        self.tree.clear()
        bold_font = QFont()
        bold_font.setBold(True)
        self.compendium_data = self.manager.load_data()
        for cat in self.compendium_data.get("categories", []):
            cat_name = cat.get("name", "Unnamed Category")
            cat_item = QTreeWidgetItem(self.tree, [cat_name])
            cat_item.setData(0, Qt.UserRole, "category")
            cat_item.setBackground(0, QBrush(ThemeManager.get_category_background_color()))
            cat_item.setFont(0, bold_font)
            for entry in sorted(cat.get("entries", []), key=lambda e: e.get("name", "")):
                entry_name = entry.get("name", "Unnamed Entry")
                entry_item = QTreeWidgetItem(cat_item, [entry_name])
                entry_item.setData(0, Qt.UserRole, "entry")
                entry_item.setData(1, Qt.UserRole, entry.get("content", ""))
                entry_item.setData(2, Qt.UserRole, entry.get("uuid", str(uuid.uuid4())))
            for subcategory in cat.get("subcategories", []):
                subcategory_item = QTreeWidgetItem(cat_item, [subcategory.get("name", "Unnamed Subcategory")])
                subcategory_item.setData(0, Qt.UserRole, "subcategory")
                subcategory_item.setFont(0, bold_font)
                for entry in sorted(subcategory.get("entries", []), key=lambda e: e.get("name", "")):
                    entry_item = QTreeWidgetItem(subcategory_item, [entry.get("name", "Unnamed Entry")])
                    entry_item.setData(0, Qt.UserRole, "entry")
                    entry_item.setData(1, Qt.UserRole, entry.get("content", ""))
                    entry_item.setData(2, Qt.UserRole, entry.get("uuid", str(uuid.uuid4())))
                subcategory_item.setExpanded(True)
            cat_item.setExpanded(True)
        self.restore_selection(selected_item_info)
        self.update_relation_combo()

    def get_selected_item_info(self):
        """Return info about the currently selected item for preserving selection."""
        current_item = self.tree.currentItem()
        if not current_item:
            return None
        item_type = current_item.data(0, Qt.UserRole)
        item_name = current_item.text(0)
        if item_type == "entry":
            parent_item = current_item.parent()
            subcategory_name = parent_item.text(0) if parent_item and parent_item.data(0, Qt.UserRole) == "subcategory" else None
            category_item = parent_item.parent() if subcategory_name else parent_item
            category_name = category_item.text(0) if category_item else None
            return {"type": "entry", "name": item_name, "category": category_name, "subcategory": subcategory_name}
        if item_type == "subcategory":
            parent_item = current_item.parent()
            return {"type": "subcategory", "name": item_name, "category": parent_item.text(0) if parent_item else None}
        return {"type": "category", "name": item_name}

    def restore_selection(self, selected_item_info):
        """Attempt to reselect the previously selected item after refresh."""
        if not selected_item_info:
            return
        item_type = selected_item_info["type"]
        item_name = selected_item_info["name"]
        if item_type == "category":
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                if cat_item.text(0) == item_name and cat_item.data(0, Qt.UserRole) == "category":
                    self.tree.setCurrentItem(cat_item)
                    return
        elif item_type == "subcategory":
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                if cat_item.text(0) != selected_item_info.get("category"):
                    continue
                for j in range(cat_item.childCount()):
                    subcategory_item = cat_item.child(j)
                    if subcategory_item.data(0, Qt.UserRole) == "subcategory" and subcategory_item.text(0) == item_name:
                        self.tree.setCurrentItem(subcategory_item)
                        return
        elif item_type == "entry":
            category_name = selected_item_info["category"]
            subcategory_name = selected_item_info.get("subcategory")
            for i in range(self.tree.topLevelItemCount()):
                cat_item = self.tree.topLevelItem(i)
                if category_name and cat_item.text(0) != category_name:
                    continue
                for j in range(cat_item.childCount()):
                    child_item = cat_item.child(j)
                    if child_item.data(0, Qt.UserRole) == "entry" and not subcategory_name:
                        if child_item.text(0) == item_name:
                            self.tree.setCurrentItem(child_item)
                            return
                    elif child_item.data(0, Qt.UserRole) == "subcategory":
                        if subcategory_name and child_item.text(0) != subcategory_name:
                            continue
                        for k in range(child_item.childCount()):
                            entry_item = child_item.child(k)
                            if entry_item.text(0) == item_name and entry_item.data(0, Qt.UserRole) == "entry":
                                self.tree.setCurrentItem(entry_item)
                                return
                if category_name and cat_item.text(0) == category_name:
                    if cat_item.childCount() > 0:
                        self.tree.setCurrentItem(cat_item.child(0))
                    else:
                        self.tree.setCurrentItem(cat_item)
                    return
        self.tree.clearSelection()

    def show_context_menu(self, pos):
        """Show context menu for tree items with appropriate actions."""
        item = self.tree.itemAt(pos)
        menu = QMenu(self)
        if item:
            item_type = item.data(0, Qt.UserRole)
            if item_type == "category":
                menu.addAction("Criar ficha", lambda: self.new_entry(item))
                menu.addAction("Criar subcategoria", lambda: self.new_subcategory(item))
                menu.addAction("Renomear categoria", lambda: self.rename_item(item, "category"))
                menu.addAction("Excluir categoria", lambda: self.delete_category(item))
            elif item_type == "subcategory":
                menu.addAction("Criar ficha", lambda: self.new_entry(item))
                menu.addAction("Renomear subcategoria", lambda: self.rename_item(item, "subcategory"))
                menu.addAction("Excluir subcategoria", lambda: self.delete_subcategory(item))
            elif item_type == "entry":
                menu.addAction("Renomear ficha", lambda: self.rename_item(item, "entry"))
                menu.addAction("Mover para cima", lambda: self.move_item(item, "up"))
                menu.addAction("Mover para baixo", lambda: self.move_item(item, "down"))
                menu.addAction("Mover para…", lambda: self.move_entry(item))
                menu.addSeparator()
                menu.addAction("Excluir ficha", lambda: self.delete_entry(item))
        else:
            menu.addAction("Criar categoria", self.new_category)
        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def save_current_entry(self):
        """Save the current entry's data to the compendium."""
        if hasattr(self, 'current_entry') and hasattr(self, 'current_entry_item'):
            self.save_entry(self.current_entry_item)
            self.dirty = False

    def save_entry(self, entry_item):
        """Save the entry data to compendium_data and persist to file."""
        entry_name = entry_item.text(0)
        entries = self._entries_for_parent_item(entry_item.parent())
        if entries is None:
            return
        notebook = self.collect_notebook_values()
        content = self.notebook_to_context(notebook)
        entry_item.setData(1, Qt.UserRole, content)
        entry = self._entry_data(entry_item)
        if entry is None:
            entry = {"name": entry_name, "content": content, "uuid": entry_item.data(2, Qt.UserRole)}
            entries.append(entry)
        else:
            entry["content"] = content
            entry["uuid"] = entry_item.data(2, Qt.UserRole)
        self.compendium_data["extensions"]["entries"].setdefault(entry_name, self.manager.default_entry_metadata())
        if entry_name in self.compendium_data["extensions"]["entries"]:
            extended_data = self.compendium_data["extensions"]["entries"][entry_name]
            extended_data["notebook"] = notebook
            extended_data["details"] = self.details_editor.toPlainText()
            extended_data["canon"] = self.canon_combo.currentText()
            extended_data["tags"] = [
                {"name": self.tags_list.item(i).text(), "color": self.tags_list.item(i).data(Qt.UserRole)}
                for i in range(self.tags_list.count())
            ]
            extended_data["relationships"] = [
                {
                    "name": self.relationships_list.topLevelItem(i).text(0),
                    "type": self.relationships_list.topLevelItem(i).text(1),
                    "canon": self.relationships_list.topLevelItem(i).text(2),
                }
                for i in range(self.relationships_list.topLevelItemCount())
            ]
            extended_data["images"] = self.get_images()
        self.save_compendium_to_file()

    def save_compendium_to_file(self):
        """Save the compendium data back to the file via the manager."""
        try:
            self.manager.save_data(self.compendium_data)
            if DEBUG:
                print("Saved compendium data to", self.compendium_file)
        except Exception as e:
            if DEBUG:
                print("Error saving compendium data:", e)
            QMessageBox.warning(self, _("Error"), _("Failed to save compendium data: {}").format(str(e)))

    def new_category(self):
        """Create a new category in the compendium."""
        name, ok = QInputDialog.getText(self, _("New Category"), _("Category name:"))
        if ok and name:
            cat_item = QTreeWidgetItem(self.tree, [name])
            cat_item.setData(0, Qt.UserRole, "category")
            cat_item.setBackground(0, QBrush(ThemeManager.get_category_background_color()))
            cat_item.setFont(0, QFont("", weight=QFont.Bold))
            self.compendium_data["categories"].append({"name": name, "entries": [], "subcategories": []})
            self.save_compendium_to_file()

    def new_subcategory(self, category_item):
        """Create an optional subcategory below the selected category."""
        name, ok = QInputDialog.getText(self, _("New Subcategory"), _("Subcategory name:"))
        category = self._category_data(category_item)
        if ok and name and category:
            subcategory_item = QTreeWidgetItem(category_item, [name])
            subcategory_item.setData(0, Qt.UserRole, "subcategory")
            subcategory_item.setFont(0, QFont("", weight=QFont.Bold))
            category.setdefault("subcategories", []).append({"name": name, "entries": []})
            category_item.setExpanded(True)
            self.save_compendium_to_file()

    def new_entry(self, category_item):
        """Create a new entry under the selected category or subcategory."""
        name, ok = QInputDialog.getText(self, _("New Entry"), _("Entry name:"))
        entries = self._entries_for_parent_item(category_item)
        if ok and name and entries is not None:
            entry_uuid = str(uuid.uuid4())
            entry_item = QTreeWidgetItem(category_item, [name])
            entry_item.setData(0, Qt.UserRole, "entry")
            entry_item.setData(1, Qt.UserRole, "")
            entry_item.setData(2, Qt.UserRole, entry_uuid)
            entries.append({"name": name, "content": "", "uuid": entry_uuid})
            self.compendium_data["extensions"]["entries"][name] = self.manager.default_entry_metadata()
            category_item.setExpanded(True)
            self.tree.setCurrentItem(entry_item)
            self.save_compendium_to_file()
            self.update_relation_combo()

    def delete_category(self, category_item):
        """Delete a category and all its entries after confirmation."""
        if self._is_factory_category(category_item):
            QMessageBox.information(
                self,
                _("Default Category"),
                _("This standard universe category stays available in every project. You can leave it empty."),
            )
            return
        confirm = QMessageBox.question(self, _("Confirm Deletion"),
            _("Are you sure you want to delete the category '{}' and all its entries?").format(category_item.text(0)),
            QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            for entry in self._all_entries(self._category_data(category_item) or {}):
                entry_name = entry.get("name", "")
                if entry_name in self.compendium_data["extensions"]["entries"]:
                    del self.compendium_data["extensions"]["entries"][entry_name]
            root = self.tree.invisibleRootItem()
            root.removeChild(category_item)
            self.compendium_data["categories"] = [
                cat for cat in self.compendium_data["categories"] if cat.get("name") != category_item.text(0)
            ]
            self.save_compendium_to_file()
            self.update_relation_combo()

    def delete_subcategory(self, subcategory_item):
        """Delete a subcategory and its optional entries after confirmation."""
        if self._is_factory_subcategory(subcategory_item):
            QMessageBox.information(
                self,
                _("Default Subcategory"),
                _("This standard subcategory stays available in every project. You can leave it empty."),
            )
            return
        confirm = QMessageBox.question(
            self, _("Confirm Deletion"),
            _("Are you sure you want to delete the subcategory '{}' and all its entries?").format(subcategory_item.text(0)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            entries = self._entries_for_parent_item(subcategory_item) or []
            for entry in entries:
                self.compendium_data["extensions"]["entries"].pop(entry.get("name", ""), None)
            category = self._category_data(subcategory_item.parent())
            if category:
                category["subcategories"] = [
                    item for item in category.get("subcategories", [])
                    if item.get("name") != subcategory_item.text(0)
                ]
            subcategory_item.parent().removeChild(subcategory_item)
            self.save_compendium_to_file()
            self.update_relation_combo()

    def delete_entry(self, entry_item):
        """Delete an entry after confirmation."""
        entry_name = entry_item.text(0)
        confirm = QMessageBox.question(self, _("Confirm Deletion"),
            _("Are you sure you want to delete the entry '{}'?").format(entry_name),
            QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            if entry_name in self.compendium_data["extensions"]["entries"]:
                del self.compendium_data["extensions"]["entries"][entry_name]
            parent = entry_item.parent()
            entries = self._entries_for_parent_item(parent)
            if parent and entries is not None:
                parent.removeChild(entry_item)
                entry_uuid = entry_item.data(2, Qt.UserRole)
                entries[:] = [
                    entry for entry in entries
                    if entry.get("uuid") != entry_uuid and entry.get("name") != entry_name
                ]
            self.save_compendium_to_file()
            if hasattr(self, 'current_entry') and self.current_entry == entry_name:
                self.clear_entry_ui()
            self.update_relation_combo()

    def rename_item(self, item, item_type):
        """Rename a category or entry."""
        current_text = item.text(0)
        new_text, ok = QInputDialog.getText(self, _("Rename {}").format(item_type.capitalize()), _("New name:"), text=current_text)
        if ok and new_text:
            if item_type == "entry":
                old_name = current_text
                if old_name in self.compendium_data["extensions"]["entries"]:
                    self.compendium_data["extensions"]["entries"][new_text] = self.compendium_data["extensions"]["entries"][old_name]
                    del self.compendium_data["extensions"]["entries"][old_name]
                entry = self._entry_data(item)
                if entry:
                    entry["name"] = new_text
                for metadata in self.compendium_data["extensions"]["entries"].values():
                    for relationship in metadata.get("relationships", []):
                        if relationship.get("name") == old_name:
                            relationship["name"] = new_text
                item.setText(0, new_text)
                if hasattr(self, 'current_entry') and self.current_entry == old_name:
                    self.current_entry = new_text
                    self.entry_name_label.setText(new_text)
            elif item_type == "subcategory":
                category = self._category_data(item.parent())
                if category:
                    for subcategory in category.get("subcategories", []):
                        if subcategory.get("name") == current_text:
                            subcategory["name"] = new_text
                            break
                item.setText(0, new_text)
            else:
                for cat in self.compendium_data["categories"]:
                    if cat.get("name") == current_text:
                        cat["name"] = new_text
                        break
                item.setText(0, new_text)
            self.save_compendium_to_file()
            if item_type == "entry":
                self.update_relation_combo()

    def move_item(self, item, direction):
        """Move an entry up or down within its category."""
        parent = item.parent() or self.tree.invisibleRootItem()
        index = parent.indexOfChild(item)
        if direction == "up" and index > 0:
            parent.takeChild(index)
            parent.insertChild(index - 1, item)
            self.tree.setCurrentItem(item)
            self.update_category_data(parent)
        elif direction == "down" and index < parent.childCount() - 1:
            parent.takeChild(index)
            parent.insertChild(index + 1, item)
            self.tree.setCurrentItem(item)
            self.update_category_data(parent)
        self.save_compendium_to_file()

    def update_category_data(self, parent):
        """Update category data to reflect the current order of items."""
        entries = self._entries_for_parent_item(parent)
        if entries is not None:
            entries_by_uuid = {entry.get("uuid"): entry for entry in entries}
            entries_by_name = {entry.get("name"): entry for entry in entries}
            entries[:] = [
                entries_by_uuid.get(parent.child(i).data(2, Qt.UserRole), entries_by_name.get(parent.child(i).text(0)))
                for i in range(parent.childCount())
                if parent.child(i).data(0, Qt.UserRole) == "entry"
            ]

    def move_entry(self, entry_item):
        """Move an entry to a different category via context menu."""
        from PyQt5.QtGui import QCursor
        menu = QMenu(self)
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            if cat_item.data(0, Qt.UserRole) == "category":
                action = menu.addAction(cat_item.text(0))
                action.setData(cat_item)
                for j in range(cat_item.childCount()):
                    subcategory_item = cat_item.child(j)
                    if subcategory_item.data(0, Qt.UserRole) == "subcategory":
                        action = menu.addAction("  {} › {}".format(cat_item.text(0), subcategory_item.text(0)))
                        action.setData(subcategory_item)
        selected_action = menu.exec_(QCursor.pos())
        if selected_action is not None:
            target_parent = selected_action.data()
            if target_parent is not None:
                current_parent = entry_item.parent()
                source_entries = self._entries_for_parent_item(current_parent)
                target_entries = self._entries_for_parent_item(target_parent)
                entry_data = self._entry_data(entry_item)
                if current_parent is not None and source_entries is not None and target_entries is not None and entry_data is not None:
                    current_parent.removeChild(entry_item)
                    source_entries.remove(entry_data)
                    target_entries.append(entry_data)
                    target_parent.addChild(entry_item)
                    target_parent.setExpanded(True)
                    self.tree.setCurrentItem(entry_item)
                    self.save_compendium_to_file()

    def on_item_changed(self, current, previous):
        """Handle tree item selection changes, saving previous entry if dirty."""
        if previous is not None and previous.data(0, Qt.UserRole) == "entry" and self.dirty:
            self.save_entry(previous)
        if current is None:
            self.clear_entry_ui()
            return
        item_type = current.data(0, Qt.UserRole)
        if item_type == "entry":
            entry_name = current.text(0)
            self.load_entry(entry_name, current)
        else:
            self.clear_entry_ui()

    def load_entry(self, entry_name, entry_item):
        """
        Load all data for the selected entry into the UI panels.
        
        Args:
            entry_name (str): Name of the entry
            entry_item: The QTreeWidgetItem for this entry
        """
        if hasattr(self, 'current_entry') and hasattr(self, 'current_entry_item') and self.dirty:
            self.save_current_entry()
        self.current_entry = entry_name
        self.current_entry_item = entry_item
        self.entry_name_label.setText(entry_name)
        content = entry_item.data(1, Qt.UserRole)
        has_extended = entry_name in self.compendium_data["extensions"]["entries"]
        if has_extended:
            extended_data = self.compendium_data["extensions"]["entries"][entry_name]
            notebook = extended_data.get("notebook", {})
            if not notebook and content:
                notebook = {"descricao": content}
            self.configure_notebook(entry_item, notebook)
            self.details_editor.blockSignals(True)
            self.details_editor.setPlainText(extended_data.get("details", ""))
            self.details_editor.blockSignals(False)
            self.canon_combo.blockSignals(True)
            self.canon_combo.setCurrentText(extended_data.get("canon", "Confirmado"))
            self.canon_combo.blockSignals(False)
            self.tags_list.clear()
            for tag in extended_data.get("tags", []):
                if isinstance(tag, dict):
                    tag_name = tag.get("name", "")
                    tag_color = tag.get("color", "#000000")
                else:
                    tag_name = tag
                    tag_color = "#000000"
                item = QListWidgetItem(tag_name)
                item.setData(Qt.UserRole, tag_color)
                item.setForeground(QBrush(QColor(tag_color)))
                item.setToolTip(_("right-click to move the tag within this list - this impacts the colour of your entry"))
                self.tags_list.addItem(item)
            self.relationships_list.clear()
            for rel in extended_data.get("relationships", []):
                rel_item = QTreeWidgetItem([
                    rel.get("name", ""),
                    rel.get("type", ""),
                    rel.get("canon", "Confirmado"),
                ])
                self.relationships_list.addTopLevelItem(rel_item)
            self.load_images(extended_data.get("images", []))
        else:
            self.configure_notebook(entry_item, {"descricao": content} if content else {})
            self.details_editor.clear()
            self.canon_combo.setCurrentText("Confirmado")
            self.tags_list.clear()
            self.relationships_list.clear()
            self.clear_images()
        self.update_entry_indicator()
        self.dirty = False
        self.tabs.show()

    def clear_entry_ui(self):
        """Clear all entry data from the UI panels."""
        self.entry_name_label.setText(_("No entry selected"))
        self.configure_notebook(None, {})
        self.details_editor.clear()
        self.canon_combo.blockSignals(True)
        self.canon_combo.setCurrentText("Confirmado")
        self.canon_combo.blockSignals(False)
        self.tags_list.clear()
        self.relationships_list.clear()
        self.clear_images()
        self.dirty = False
        self.tabs.hide()
        if hasattr(self, 'current_entry'):
            del self.current_entry
        if hasattr(self, 'current_entry_item'):
            del self.current_entry_item

    def clear_images(self):
        """Clear all images from the images layout."""
        while self.image_layout.count():
            child = self.image_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def open_with_entry(self, project_name, entry_name):
        """Make visible and raise window, then show the entry."""
        self.populate_project_combo(project_name)
        self.change_project(project_name)
        self.show()
        self.raise_()
        if entry_name:
            self.find_and_select_entry(entry_name)

    def find_and_select_entry(self, entry_name):
        """Search the tree and select an entry by name."""
        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child_item = cat_item.child(j)
                if child_item.data(0, Qt.UserRole) == "entry" and child_item.text(0) == entry_name:
                    self.tree.setCurrentItem(child_item)
                    return
                if child_item.data(0, Qt.UserRole) == "subcategory":
                    for k in range(child_item.childCount()):
                        entry_item = child_item.child(k)
                        if entry_item.data(0, Qt.UserRole) == "entry" and entry_item.text(0) == entry_name:
                            self.tree.setCurrentItem(entry_item)
                            return

    def update_relation_combo(self):
        """Update the relationship combo box with all entry names."""
        self.relationship_combo.clear()
        entries = []
        for cat in self.compendium_data.get("categories", []):
            for entry in self._all_entries(cat):
                entries.append(entry.get("name", ""))
        entries.sort()
        self.relationship_combo.addItems(entries)

    def add_tag(self):
        """Add a new tag to the current entry."""
        tag_name = self.tag_input.text().strip()
        if tag_name and hasattr(self, 'current_entry'):
            tag_color = self.tag_color_button.property("current_color") or "#000000"
            item = QListWidgetItem(tag_name)
            item.setData(Qt.UserRole, tag_color)
            item.setForeground(QBrush(QColor(tag_color)))
            item.setToolTip(_("right-click to move the tag within this list - this impacts the colour of your entry"))
            self.tags_list.addItem(item)
            self.tag_input.clear()
            self.mark_dirty()

    def choose_tag_color(self):
        """Open a color dialog to choose a tag color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.tag_color_button.setProperty("current_color", color.name())
            self.tag_color_button.setStyleSheet(f"background-color: {color.name()};")
            self.mark_dirty()

    def show_tags_context_menu(self, pos):
        """Show context menu for tags list."""
        item = self.tags_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            menu.addAction(_("Remove Tag"), lambda: self.remove_tag(item))
            menu.addAction(_("Move Up"), lambda: self.move_tag(item, "up"))
            menu.addAction(_("Move Down"), lambda: self.move_tag(item, "down"))
            menu.exec_(self.tags_list.viewport().mapToGlobal(pos))

    def remove_tag(self, item):
        """Remove a tag from the tags list."""
        row = self.tags_list.row(item)
        self.tags_list.takeItem(row)
        self.mark_dirty()

    def move_tag(self, item, direction):
        """Move a tag up or down in the tags list."""
        row = self.tags_list.row(item)
        if direction == "up" and row > 0:
            self.tags_list.takeItem(row)
            self.tags_list.insertItem(row - 1, item)
            self.tags_list.setCurrentItem(item)
        elif direction == "down" and row < self.tags_list.count() - 1:
            self.tags_list.takeItem(row)
            self.tags_list.insertItem(row + 1, item)
            self.tags_list.setCurrentItem(item)
        self.mark_dirty()

    def add_relationship(self):
        """Add a new relationship to the current entry."""
        rel_name = self.relationship_combo.currentText()
        rel_type = self.relationship_type.text().strip()
        if rel_name and rel_type and hasattr(self, 'current_entry'):
            rel_item = QTreeWidgetItem([rel_name, rel_type, self.relationship_canon.currentText()])
            self.relationships_list.addTopLevelItem(rel_item)
            self.relationship_type.clear()
            self.mark_dirty()

    def show_relationships_context_menu(self, pos):
        """Show context menu for relationships list."""
        item = self.relationships_list.itemAt(pos)
        if item:
            menu = QMenu(self)
            menu.addAction(_("Remove Relationship"), lambda: self.remove_relationship(item))
            menu.exec_(self.relationships_list.viewport().mapToGlobal(pos))

    def remove_relationship(self, item):
        """Remove a relationship from the relationships list."""
        index = self.relationships_list.indexOfTopLevelItem(item)
        self.relationships_list.takeTopLevelItem(index)
        self.mark_dirty()

    def add_image(self):
        """Add an image to the current entry."""
        file_name, _unused = QFileDialog.getOpenFileName(self, _("Select Image"), "", _("Images (*.png *.jpg *.jpeg *.bmp)"))
        if file_name and hasattr(self, 'current_entry'):
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                label = QLabel()
                label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                self.image_layout.addWidget(label)
                self.compendium_data["extensions"]["entries"][self.current_entry]["images"].append(file_name)
                self.mark_dirty()

    def load_images(self, images):
        """Load images into the images tab."""
        self.clear_images()
        for image_path in images:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                label = QLabel()
                label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio))
                self.image_layout.addWidget(label)

    def get_images(self):
        """Return the list of image paths for the current entry."""
        if hasattr(self, 'current_entry'):
            return self.compendium_data["extensions"]["entries"].get(self.current_entry, {}).get("images", [])
        return []

    def update_entry_indicator(self):
        """Update the entry indicator based on relationships (green if has relationships)."""
        if hasattr(self, 'current_entry'):
            relationships = self.compendium_data["extensions"]["entries"].get(self.current_entry, {}).get("relationships", [])
            if relationships:
                self.entry_name_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: green;")
            else:
                self.entry_name_label.setStyleSheet("font-size: 16pt; font-weight: bold;")

    def on_compendium_updated(self, updated_project_name):
        """Handle compendium update notifications from the event bus."""
        if updated_project_name == self.project_name:
            self.populate_compendium()

    def filter_tree(self):
        """Filter the tree based on search bar input (entries and tags)."""
        search_text = self.search_bar.text().lower()
        for i in range(self.tree.topLevelItemCount()):
            cat_item = self.tree.topLevelItem(i)
            cat_visible = not search_text
            for j in range(cat_item.childCount()):
                child_item = cat_item.child(j)
                if child_item.data(0, Qt.UserRole) == "entry":
                    entry_visible = self._entry_matches_search(child_item, search_text)
                    child_item.setHidden(not entry_visible)
                    cat_visible = cat_visible or entry_visible
                elif child_item.data(0, Qt.UserRole) == "subcategory":
                    subcategory_visible = search_text in child_item.text(0).lower()
                    for k in range(child_item.childCount()):
                        entry_item = child_item.child(k)
                        entry_visible = self._entry_matches_search(entry_item, search_text)
                        entry_item.setHidden(not entry_visible and not subcategory_visible)
                        subcategory_visible = subcategory_visible or entry_visible
                    child_item.setHidden(not subcategory_visible)
                    cat_visible = cat_visible or subcategory_visible
            cat_item.setHidden(not cat_visible)

    def _entry_matches_search(self, entry_item, search_text):
        entry_name = entry_item.text(0).lower()
        entry_tags = self.compendium_data["extensions"]["entries"].get(entry_item.text(0), {}).get("tags", [])
        tag_names = [tag.get("name", "").lower() if isinstance(tag, dict) else tag.lower() for tag in entry_tags]
        return search_text in entry_name or any(search_text in tag for tag in tag_names)
