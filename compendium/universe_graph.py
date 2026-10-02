"""Interactive relationship map for a project's universe database."""

from math import cos, pi, sin

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from compendium.compendium_manager import CompendiumEventBus, CompendiumManager


class UniverseGraphView(QGraphicsView):
    """Canvas with hand panning and wheel zoom for the relationship map."""

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)


class UniverseGraphWindow(QMainWindow):
    """Show the entries and canonical relationships of a Juvion universe."""

    CATEGORY_COLORS = {
        "Personagens": "#742b3a",
        "Worldbuilding": "#596f4d",
        "Organizações": "#8a6237",
        "Seres": "#6c4f86",
        "Sistemas e poderes": "#285f75",
        "Itens e artefatos": "#8b4c62",
        "Histórias e eventos": "#9a5735",
        "Conceitos & lore": "#526472",
        "Criaturas": "#704f43",
        "Narrativa": "#545454",
    }
    RELATIONSHIP_COLORS = {
        "Confirmado": "#742b3a",
        "Rumor": "#777777",
        "Planejado": "#3d6b91",
        "Descartado": "#9a9a9a",
        "Contraditório": "#a33232",
    }

    def __init__(self, project_name="default", parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.event_bus = CompendiumEventBus.get_instance()
        self.manager = CompendiumManager(project_name, event_bus=self.event_bus)
        self.event_bus.add_updated_listener(self.on_compendium_updated)
        self.nodes_by_id = {}
        self.node_metadata = {}

        self.setWindowTitle("Juvion — Mapa de relações: {}".format(project_name))
        self.resize(1120, 720)
        self._create_toolbar()
        self._create_content()
        self.refresh_graph()

    def _create_toolbar(self):
        toolbar = QToolBar("Mapa de relações", self)
        toolbar.setObjectName("UniverseGraphToolbar")
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("  Mostrar: "))
        self.canon_filter = QComboBox()
        self.canon_filter.addItem("Todos os vínculos")
        self.canon_filter.addItems(self.manager.CANON_STATUSES)
        self.canon_filter.currentTextChanged.connect(self.refresh_graph)
        toolbar.addWidget(self.canon_filter)

        refresh_action = QAction("Atualizar", self)
        refresh_action.triggered.connect(self.refresh_graph)
        toolbar.addAction(refresh_action)

        reset_zoom_action = QAction("Redefinir zoom", self)
        reset_zoom_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_zoom_action)

    def _create_content(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        self.scene = QGraphicsScene(self)
        self.view = UniverseGraphView(self.scene, self)
        self.scene.selectionChanged.connect(self._show_selected_node)
        splitter.addWidget(self.view)

        side_panel = QWidget()
        side_panel.setMinimumWidth(250)
        side_layout = QVBoxLayout(side_panel)
        title = QLabel("Detalhes da ficha")
        title.setStyleSheet("font-weight: 700; font-size: 15px;")
        side_layout.addWidget(title)
        self.details = QLabel("Selecione uma ficha para ver sua categoria, subcategoria e relações.")
        self.details.setWordWrap(True)
        self.details.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        side_layout.addWidget(self.details, 1)
        helper = QLabel("Arraste o mapa para navegar. Use a roda do mouse para aproximar ou afastar.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #777;")
        side_layout.addWidget(helper)
        splitter.addWidget(side_panel)
        splitter.setSizes([850, 270])

    def open_project(self, project_name):
        """Point this window at a project and redraw its graph."""
        if self.project_name != project_name:
            self.project_name = project_name
            self.manager = CompendiumManager(project_name, event_bus=self.event_bus)
        self.setWindowTitle("Juvion — Mapa de relações: {}".format(project_name))
        self.refresh_graph()

    def on_compendium_updated(self, project_name):
        if project_name == self.project_name and self.isVisible():
            self.refresh_graph()

    def reset_view(self):
        self.view.resetTransform()
        self.view.fitInView(self.scene.itemsBoundingRect().adjusted(-50, -50, 50, 50), Qt.KeepAspectRatio)

    def _entries(self, data):
        """Return all entries with their category context, including subcategories."""
        entries = []
        for category in data.get("categories", []):
            category_name = category.get("name", "Sem categoria")
            for entry in category.get("entries", []):
                entries.append((entry, category_name, ""))
            for subcategory in category.get("subcategories", []):
                subcategory_name = subcategory.get("name", "")
                for entry in subcategory.get("entries", []):
                    entries.append((entry, category_name, subcategory_name))
        return entries

    def refresh_graph(self):
        """Render current entries and indexed relationships into a readable radial graph."""
        data = self.manager.load_data()
        all_entries = self._entries(data)
        relationship_filter = self.canon_filter.currentText() if hasattr(self, "canon_filter") else "Todos os vínculos"
        relationships = [
            relationship for relationship in data.get("universe", {}).get("relationships", [])
            if relationship_filter == "Todos os vínculos" or relationship.get("canon", "Confirmado") == relationship_filter
        ]

        self.scene.clear()
        self.nodes_by_id.clear()
        self.node_metadata.clear()
        self.details.setText("Selecione uma ficha para ver sua categoria, subcategoria e relações.")

        if not all_entries:
            message = self.scene.addSimpleText("Crie fichas no Universo e conecte-as para vê-las neste mapa.")
            message.setPos(30, 30)
            self.scene.setSceneRect(0, 0, 700, 400)
            return

        radius = max(220, 75 * len(all_entries))
        node_width, node_height = 154, 54
        for index, (entry, category_name, subcategory_name) in enumerate(all_entries):
            angle = (2 * pi * index / len(all_entries)) - (pi / 2)
            x = radius + (radius * cos(angle)) - (node_width / 2)
            y = radius + (radius * sin(angle)) - (node_height / 2)
            color = QColor(self.CATEGORY_COLORS.get(category_name, "#6b5a60"))
            node = QGraphicsRectItem(x, y, node_width, node_height)
            node.setBrush(color)
            node.setPen(QPen(QColor("#ffffff"), 1.2))
            node.setFlag(QGraphicsRectItem.ItemIsSelectable)
            node.setData(0, entry.get("uuid", ""))
            self.scene.addItem(node)

            name = entry.get("name", "Ficha sem nome")
            label = QGraphicsSimpleTextItem(name[:23] + ("…" if len(name) > 23 else ""), node)
            label.setBrush(QColor("#ffffff"))
            label.setPos(10, 8)
            category_label = QGraphicsSimpleTextItem(subcategory_name or category_name, node)
            category_label.setBrush(QColor("#f2e8e9"))
            category_label.setScale(0.78)
            category_label.setPos(10, 31)

            entry_id = entry.get("uuid", "")
            self.nodes_by_id[entry_id] = node
            self.node_metadata[entry_id] = {
                "name": name,
                "category": category_name,
                "subcategory": subcategory_name,
                "content": entry.get("content", ""),
            }

        for relationship in relationships:
            source = self.nodes_by_id.get(relationship.get("source_id"))
            target = self.nodes_by_id.get(relationship.get("target_id"))
            if not source or not target or source is target:
                continue
            source_center = source.sceneBoundingRect().center()
            target_center = target.sceneBoundingRect().center()
            canon = relationship.get("canon", "Confirmado")
            pen = QPen(QColor(self.RELATIONSHIP_COLORS.get(canon, "#742b3a")), 2)
            if canon in {"Rumor", "Planejado", "Descartado"}:
                pen.setStyle(Qt.DashLine)
            edge = self.scene.addLine(source_center.x(), source_center.y(), target_center.x(), target_center.y(), pen)
            edge.setZValue(-1)
            relationship_type = relationship.get("type", "")
            if relationship_type:
                label = self.scene.addSimpleText(relationship_type)
                label.setBrush(QColor(self.RELATIONSHIP_COLORS.get(canon, "#742b3a")))
                label.setScale(0.78)
                label.setPos((source_center.x() + target_center.x()) / 2, (source_center.y() + target_center.y()) / 2)
                label.setZValue(-0.5)

        self.scene.setSceneRect(0, 0, radius * 2, radius * 2)
        self.reset_view()

    def _show_selected_node(self):
        selected = self.scene.selectedItems()
        for node in self.nodes_by_id.values():
            node.setPen(QPen(QColor("#ffffff"), 1.2))
        if not selected:
            self.details.setText("Selecione uma ficha para ver sua categoria, subcategoria e relações.")
            return
        node = selected[0]
        node.setPen(QPen(QColor("#201116"), 3))
        metadata = self.node_metadata.get(node.data(0), {})
        hierarchy = metadata.get("category", "")
        if metadata.get("subcategory"):
            hierarchy += " › " + metadata["subcategory"]
        content = metadata.get("content", "").strip()
        preview = content[:420] + ("…" if len(content) > 420 else "")
        self.details.setText(
            "<b>{}</b><br><br>{}<br><br>{}".format(
                metadata.get("name", "Ficha"), hierarchy, preview or "Sem descrição ainda."
            )
        )
