import os
import shutil
import uuid
from PyQt5.QtCore import Qt, QPointF, pyqtSignal, QRectF, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen, QBrush, QTransform, QCursor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem,
    QInputDialog, QMessageBox, QLabel, QMenu, QComboBox
)
from settings.settings_manager import WWSettingsManager

class MapPin(QGraphicsItem):
    """A clickable pin on the map that links to a compendium entry."""
    def __init__(self, x, y, entry_name, map_panel, parent=None):
        super().__init__(parent)
        self.setPos(x, y)
        self.entry_name = entry_name
        self.map_panel = map_panel
        self.radius = 12
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.is_hovered = False
        self.was_moved = False

    def boundingRect(self):
        return QRectF(-60, -self.radius, 120, self.radius * 2 + 24)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.Antialiasing)
        if self.isSelected():
            painter.setBrush(QBrush(QColor(255, 50, 50)))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
        elif self.is_hovered:
            painter.setBrush(QBrush(QColor(200, 50, 50)))
            painter.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            painter.setBrush(QBrush(QColor(150, 20, 20)))
            painter.setPen(QPen(QColor(255, 255, 255), 1))

        painter.drawEllipse(QRectF(-self.radius, -self.radius, self.radius*2, self.radius*2))

        # Draw label
        if self.isSelected() or self.is_hovered:
            painter.setPen(QPen(QColor(255, 255, 255)))
            font = painter.font()
            font.setPointSize(10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(-50, self.radius + 2, 100, 20), Qt.AlignCenter, self.entry_name)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        self.setCursor(Qt.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.was_moved = False
        elif event.button() == Qt.RightButton:
            self.setSelected(True)
            self.map_panel.show_pin_context_menu(self, event.screenPos())
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.was_moved = True
            self.map_panel.save_timer.start()
        return super().itemChange(change, value)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.map_panel.save_timer.stop()
        self.map_panel.save_map_data()
        if event.button() == Qt.LeftButton and not self.was_moved:
            self.map_panel.pin_clicked.emit(self.entry_name)


class InteractiveMapView(QGraphicsView):
    def __init__(self, map_panel, parent=None):
        super().__init__(parent)
        self.map_panel = map_panel
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.map_item = None
        self.is_adding_pin = False

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if self.is_adding_pin and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.map_panel.add_new_pin(scene_pos.x(), scene_pos.y())
            self.is_adding_pin = False
            self.setCursor(Qt.ArrowCursor)
            return

        super().mousePressEvent(event)


class MapPanel(QWidget):
    pin_clicked = pyqtSignal(str)  # Emitted with the compendium entry name

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.model = controller.model
        self.map_data = self.model.settings.get("map", {"image_path": "", "pins": []})
        self.pins = []
        self.project_dir = WWSettingsManager.get_project_path(self.model.project_name)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(250)
        self.save_timer.timeout.connect(self.save_map_data)
        self.init_ui()
        self.load_map_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.load_map_btn = QPushButton("Selecionar Imagem do Mapa")
        self.load_map_btn.clicked.connect(self.select_map_image)

        self.add_pin_btn = QPushButton("Adicionar Lugar (Pin)")
        self.add_pin_btn.clicked.connect(self.enable_add_pin_mode)
        self.add_pin_btn.setEnabled(False)

        toolbar_layout.addWidget(self.load_map_btn)
        toolbar_layout.addWidget(self.add_pin_btn)
        toolbar_layout.addStretch()

        # Map View
        self.map_view = InteractiveMapView(self)
        self.pin_clicked.connect(self.on_pin_clicked)

        layout.addLayout(toolbar_layout)
        layout.addWidget(self.map_view)

    def select_map_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Imagem do Mapa", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            if QPixmap(file_path).isNull():
                QMessageBox.warning(self, "Mapa", "Não foi possível ler essa imagem.")
                return
            if self.pins and QMessageBox.question(
                self, "Trocar mapa", "Trocar a imagem removerá os marcadores deste mapa. Continuar?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            ) != QMessageBox.Yes:
                return
            try:
                assets_dir = os.path.join(self.project_dir, "assets")
                os.makedirs(assets_dir, exist_ok=True)
                filename = "map_{}{}".format(uuid.uuid4().hex, os.path.splitext(file_path)[1].lower())
                shutil.copy2(file_path, os.path.join(assets_dir, filename))
            except OSError as error:
                QMessageBox.warning(self, "Mapa", "Não foi possível guardar o mapa na obra.\n\n{}".format(error))
                return
            self.save_timer.stop()
            self.map_data["image_path"] = "assets/" + filename
            self.pins.clear()
            self.save_map_data()
            self.load_map_data()

    def load_map_data(self):
        self.map_view.scene.clear()
        self.pins.clear()

        image_path = self.map_data.get("image_path", "")
        if image_path and not os.path.isabs(image_path):
            image_path = image_path.replace("\\", "/")
            image_path = os.path.join(self.project_dir, image_path)
        elif image_path and os.path.isfile(image_path):
            # Preserve older maps by importing the external image into the work.
            try:
                assets_dir = os.path.join(self.project_dir, "assets")
                os.makedirs(assets_dir, exist_ok=True)
                filename = "map_{}{}".format(uuid.uuid4().hex, os.path.splitext(image_path)[1].lower())
                shutil.copy2(image_path, os.path.join(assets_dir, filename))
                self.map_data["image_path"] = "assets/" + filename
                self.model.settings["map"] = self.map_data
                self.model.save_settings()
                image_path = os.path.join(assets_dir, filename)
            except OSError:
                pass  # Keep the original readable path if the copy fails.
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.map_view.map_item = QGraphicsPixmapItem(pixmap)
            self.map_view.scene.addItem(self.map_view.map_item)
            self.add_pin_btn.setEnabled(True)

            # Load pins
            for pin_data in self.map_data.get("pins", []):
                pin = MapPin(pin_data["x"], pin_data["y"], pin_data["entry_name"], self)
                self.map_view.scene.addItem(pin)
                self.pins.append(pin)

            self.map_view.fitInView(self.map_view.sceneRect(), Qt.KeepAspectRatio)
        else:
            self.add_pin_btn.setEnabled(False)
            text_item = self.map_view.scene.addText("Nenhum mapa selecionado.\nClique em 'Selecionar Imagem do Mapa'.")
            text_item.setDefaultTextColor(QColor("gray"))

    def enable_add_pin_mode(self):
        self.map_view.is_adding_pin = True
        self.map_view.setCursor(Qt.CrossCursor)

    def add_new_pin(self, x, y):
        # Fetch entries from compendium to populate the dropdown
        try:
            index = self.model.compendium.get_entry_index()
            entries = [entry["name"] for entry in index]
            entries.sort()
        except Exception as e:
            print("Error loading entries:", e)
            entries = []

        if not entries:
            QMessageBox.warning(self, "Aviso", "O Caderno de Fichas (Universo) está vazio. Crie fichas primeiro.")
            return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("Vincular Ficha")
        dialog.setLabelText("Selecione o lugar/ficha para vincular a este ponto:")
        dialog.setComboBoxItems(entries)
        dialog.setComboBoxEditable(False)

        if dialog.exec_() == QInputDialog.Accepted:
            entry_name = dialog.textValue()
            if entry_name:
                pin = MapPin(x, y, entry_name, self)
                self.map_view.scene.addItem(pin)
                self.pins.append(pin)
                self.save_map_data()

    def show_pin_context_menu(self, pin, screen_pos):
        menu = QMenu(self)
        delete_action = menu.addAction("Remover Marcador")
        action = menu.exec_(screen_pos)
        if action == delete_action:
            self.map_view.scene.removeItem(pin)
            self.pins.remove(pin)
            self.save_map_data()

    def save_map_data(self):
        pins_data = []
        for pin in self.pins:
            pins_data.append({
                "x": pin.x(),
                "y": pin.y(),
                "entry_name": pin.entry_name
            })
        self.map_data["pins"] = pins_data
        self.model.settings["map"] = self.map_data
        self.model.save_settings()

    def on_pin_clicked(self, entry_name):
        # Notify the project window to open this compendium entry
        self.controller.toggle_compendium_view(True)
        if self.controller.enhanced_window:
            self.controller.enhanced_window.open_with_entry(self.model.project_name, entry_name)
