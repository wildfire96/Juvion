"""Two-track timeline for universe chronology and narrative order."""

import json
from uuid import uuid4

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGraphicsEllipseItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from compendium.compendium_manager import CompendiumManager
from settings.settings_manager import WWSettingsManager


class TimelineManager:
    """Persist project events without imposing a real-world calendar."""

    SCHEMA_VERSION = 1

    def __init__(self, project_name):
        self.project_name = project_name
        self.filepath = WWSettingsManager.get_project_relpath(project_name, "timeline.json")

    def load(self):
        try:
            with open(self.filepath, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            data = {"schema_version": self.SCHEMA_VERSION, "events": []}
        changed = self._normalise(data)
        if changed:
            self.save(data)
        return data

    def save(self, data):
        self._normalise(data)
        with open(self.filepath, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _normalise(self, data):
        changed = data.get("schema_version") != self.SCHEMA_VERSION
        data["schema_version"] = self.SCHEMA_VERSION
        if not isinstance(data.get("events"), list):
            data["events"] = []
            changed = True
        defaults = {
            "title": "",
            "description": "",
            "universe_date": "",
            "universe_order": 0,
            "narrative_order": 0,
            "canon": "Confirmado",
            "scene_path": "",
        }
        for event in data["events"]:
            if not event.get("id"):
                event["id"] = str(uuid4())
                changed = True
            for key, value in defaults.items():
                if key not in event:
                    event[key] = value
                    changed = True
        return changed


class TimelineCanvas(QGraphicsView):
    """Read-only, scrollable visual of the two event orders."""

    def __init__(self, parent=None):
        self.scene = QGraphicsScene(parent)
        super().__init__(self.scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

    def set_events(self, events):
        self.scene.clear()
        if not events:
            message = self.scene.addSimpleText("Crie eventos para comparar a ordem do universo com a ordem da narrativa.")
            message.setPos(28, 28)
            self.scene.setSceneRect(0, 0, 760, 240)
            return

        width = max(740, self.viewport().width() - 8)
        universe_x, narrative_x = width * 0.28, width * 0.72
        height = max(420, len(events) * 58 + 110)
        heading_pen = QColor("#7b001f")
        self._label("Tempo do universo", universe_x - 70, 20, heading_pen, 1.1)
        self._label("Ordem na narrativa", narrative_x - 70, 20, heading_pen, 1.1)
        line_pen = QPen(QColor("#c9b9ae"), 2)
        self.scene.addLine(universe_x, 62, universe_x, height - 24, line_pen)
        self.scene.addLine(narrative_x, 62, narrative_x, height - 24, line_pen)

        by_universe = sorted(events, key=lambda event: (event.get("universe_order", 0), event.get("title", "").casefold()))
        by_narrative = sorted(events, key=lambda event: (event.get("narrative_order", 0), event.get("title", "").casefold()))
        for index, event in enumerate(by_universe):
            self._event_node(event, universe_x, 84 + index * 58, "universe")
        for index, event in enumerate(by_narrative):
            self._event_node(event, narrative_x, 84 + index * 58, "narrative")
        self.scene.setSceneRect(0, 0, width, height)

    def _label(self, text, x, y, color, scale=1.0):
        label = QGraphicsSimpleTextItem(text)
        label.setBrush(color)
        label.setScale(scale)
        label.setPos(x, y)
        self.scene.addItem(label)

    def _event_node(self, event, x, y, track):
        canon = event.get("canon", "Confirmado")
        colors = {
            "Confirmado": "#7b001f",
            "Rumor": "#7d746d",
            "Planejado": "#426b88",
            "Descartado": "#a0a0a0",
            "Contraditório": "#9b3030",
        }
        color = QColor(colors.get(canon, "#7b001f"))
        node = QGraphicsEllipseItem(x - 7, y - 7, 14, 14)
        node.setBrush(color)
        node.setPen(QPen(QColor("#ffffff"), 1))
        self.scene.addItem(node)
        order = event.get("universe_order", 0) if track == "universe" else event.get("narrative_order", 0)
        suffix = event.get("universe_date", "") if track == "universe" else event.get("scene_path", "")
        text = "{} · {}".format(order, event.get("title", "Evento sem título"))
        if suffix:
            text += "\n{}".format(suffix)
        self._label(text, x + 15, y - 13, QColor("#342c28"))


class TimelineWindow(QMainWindow):
    """Edit events and compare chronology in a universe and its manuscript."""

    def __init__(self, project_name, project_structure=None, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.project_structure = project_structure or {}
        self.manager = TimelineManager(project_name)
        self.current_event_id = None
        self.setWindowTitle("Juvion — Linha do tempo: {}".format(project_name))
        self.resize(1120, 720)
        self._build_ui()
        self.populate_events()

    def _build_ui(self):
        toolbar = QToolBar("Linha do tempo", self)
        self.addToolBar(toolbar)
        new_action = toolbar.addAction("Novo evento")
        new_action.triggered.connect(self.new_event)
        delete_action = toolbar.addAction("Excluir evento")
        delete_action.triggered.connect(self.delete_event)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        intro = QLabel("Cada evento pode ter uma posição no tempo do universo e outra na ordem em que o leitor o descobre.")
        intro.setObjectName("PanelDescription")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._build_event_editor(), "Eventos")
        self.canvas = TimelineCanvas(self)
        self.tabs.addTab(self.canvas, "Visão dupla")

    def _build_event_editor(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.events_tree = QTreeWidget()
        self.events_tree.setHeaderLabels(["Evento", "Tempo do universo", "Narrativa", "Cânone"])
        self.events_tree.setMinimumWidth(420)
        self.events_tree.currentItemChanged.connect(self.load_selected_event)
        splitter.addWidget(self.events_tree)

        editor = QWidget()
        form = QFormLayout(editor)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Ex.: Primeiro encontro de Lira e Cael")
        self.universe_date_input = QLineEdit()
        self.universe_date_input.setPlaceholderText("Ex.: 14 de Brumário de 712")
        self.universe_order_input = QSpinBox()
        self.universe_order_input.setRange(0, 999999)
        self.universe_order_input.setToolTip("Use números para ordenar eventos, mesmo se seu calendário for ficcional.")
        self.narrative_order_input = QSpinBox()
        self.narrative_order_input.setRange(0, 999999)
        self.narrative_order_input.setToolTip("Define quando o leitor encontra este evento na narrativa.")
        self.canon_combo = QComboBox()
        self.canon_combo.addItems(CompendiumManager.CANON_STATUSES)
        self.scene_combo = QComboBox()
        self.scene_combo.setToolTip("Vincule o evento a uma cena quando ele acontece ou é revelado nela.")
        self._populate_scene_combo()
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("O que acontece? Quais consequências esse evento deixa para a história?")
        self.description_input.setMinimumHeight(180)
        form.addRow("Nome do evento:", self.title_input)
        form.addRow("Data no universo:", self.universe_date_input)
        form.addRow("Ordem no universo:", self.universe_order_input)
        form.addRow("Ordem na narrativa:", self.narrative_order_input)
        form.addRow("Cânone:", self.canon_combo)
        form.addRow("Cena vinculada:", self.scene_combo)
        form.addRow("Descrição:", self.description_input)
        self.save_button = QPushButton("Salvar evento")
        self.save_button.setProperty("primary", True)
        self.save_button.setToolTip("Guarde este evento e atualize as duas visões da linha do tempo.")
        self.save_button.clicked.connect(self.save_event)
        form.addRow(self.save_button)
        splitter.addWidget(editor)
        splitter.setSizes([460, 620])
        return widget

    def _populate_scene_combo(self):
        self.scene_combo.clear()
        self.scene_combo.addItem("Nenhuma cena vinculada", "")
        for path in self._scene_paths(self.project_structure):
            self.scene_combo.addItem(path, path)

    def _scene_paths(self, structure):
        paths = []
        for act in structure.get("acts", []):
            act_name = act.get("name", "Ato")
            for chapter in act.get("chapters", []):
                chapter_name = chapter.get("name", "Capítulo")
                for scene in chapter.get("scenes", []):
                    paths.append("{} › {} › {}".format(act_name, chapter_name, scene.get("name", "Cena")))
        return paths

    def open_project(self, project_name, project_structure=None):
        self.project_name = project_name
        self.project_structure = project_structure or {}
        self.manager = TimelineManager(project_name)
        self.setWindowTitle("Juvion — Linha do tempo: {}".format(project_name))
        self._populate_scene_combo()
        self.new_event()
        self.populate_events()

    def populate_events(self, selected_id=None):
        data = self.manager.load()
        self.events_tree.blockSignals(True)
        self.events_tree.clear()
        for event in sorted(data["events"], key=lambda item: (item.get("universe_order", 0), item.get("title", "").casefold())):
            item = QTreeWidgetItem([
                event.get("title", "Evento sem título"),
                event.get("universe_date", "") or str(event.get("universe_order", 0)),
                str(event.get("narrative_order", 0)),
                event.get("canon", "Confirmado"),
            ])
            item.setData(0, Qt.UserRole, event["id"])
            self.events_tree.addTopLevelItem(item)
            if event["id"] == selected_id:
                self.events_tree.setCurrentItem(item)
        self.events_tree.blockSignals(False)
        self.canvas.set_events(data["events"])
        if selected_id:
            self.load_selected_event(self.events_tree.currentItem(), None)

    def new_event(self):
        data = self.manager.load()
        next_order = max((max(event.get("universe_order", 0), event.get("narrative_order", 0)) for event in data["events"]), default=0) + 1
        self.current_event_id = None
        self.title_input.clear()
        self.universe_date_input.clear()
        self.universe_order_input.setValue(next_order)
        self.narrative_order_input.setValue(next_order)
        self.canon_combo.setCurrentText("Confirmado")
        self.scene_combo.setCurrentIndex(0)
        self.description_input.clear()
        self.title_input.setFocus()

    def load_selected_event(self, current, _previous):
        if current is None:
            return
        event_id = current.data(0, Qt.UserRole)
        data = self.manager.load()
        event = next((item for item in data["events"] if item["id"] == event_id), None)
        if event is None:
            return
        self.current_event_id = event_id
        self.title_input.setText(event.get("title", ""))
        self.universe_date_input.setText(event.get("universe_date", ""))
        self.universe_order_input.setValue(event.get("universe_order", 0))
        self.narrative_order_input.setValue(event.get("narrative_order", 0))
        self.canon_combo.setCurrentText(event.get("canon", "Confirmado"))
        scene_index = self.scene_combo.findData(event.get("scene_path", ""))
        self.scene_combo.setCurrentIndex(max(0, scene_index))
        self.description_input.setPlainText(event.get("description", ""))

    def save_event(self):
        title = self.title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Nome do evento", "Dê um nome ao evento antes de salvá-lo.")
            return
        data = self.manager.load()
        event = next((item for item in data["events"] if item["id"] == self.current_event_id), None)
        if event is None:
            event = {"id": str(uuid4())}
            data["events"].append(event)
            self.current_event_id = event["id"]
        event.update({
            "title": title,
            "description": self.description_input.toPlainText().strip(),
            "universe_date": self.universe_date_input.text().strip(),
            "universe_order": self.universe_order_input.value(),
            "narrative_order": self.narrative_order_input.value(),
            "canon": self.canon_combo.currentText(),
            "scene_path": self.scene_combo.currentData() or "",
        })
        self.manager.save(data)
        self.populate_events(self.current_event_id)

    def delete_event(self):
        if not self.current_event_id:
            return
        data = self.manager.load()
        event = next((item for item in data["events"] if item["id"] == self.current_event_id), None)
        if event is None:
            return
        choice = QMessageBox.question(
            self,
            "Excluir evento",
            "Excluir o evento '{}'?".format(event.get("title", "")),
            QMessageBox.Yes | QMessageBox.No,
        )
        if choice == QMessageBox.Yes:
            data["events"] = [item for item in data["events"] if item["id"] != self.current_event_id]
            self.manager.save(data)
            self.new_event()
            self.populate_events()
