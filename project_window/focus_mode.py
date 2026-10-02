import os
import re
import sys

from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtGui import QKeyEvent, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class PlainTextEdit(QTextEdit):
    """Text editor that always pastes plain text."""

    def __init__(self):
        super().__init__()
        self.zoom_factor = 10

    def adjust_zoom(self, delta):
        self.zoom_factor = max(5, min(self.zoom_factor + delta, 30))
        stylesheet = self.styleSheet()
        if "font-size" not in stylesheet:
            stylesheet += f" font-size: {self.zoom_factor * 10}%;"
        else:
            stylesheet = re.sub(r"font-size: \d+%;", f"font-size: {self.zoom_factor * 10}%;", stylesheet)
        self.setStyleSheet(stylesheet)
        self.viewport().update()

    def toHtmlPreservingOriginal(self):
        return self.document().toHtml()

    def insertFromMimeData(self, source):
        self.insertPlainText(source.text())


class FocusMode(QMainWindow):
    """A responsive, theme-aware space for uninterrupted writing."""

    def __init__(self, image_dir, scene_text="", theme_name="Juvion Claro", parent=None, scene_html=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.on_close = None
        self.image_dir = image_dir
        self.image_files = self._available_backgrounds()
        self.current_index = 0
        self.animation = None

        self.setWindowTitle("Modo foco")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._build_ui(scene_text)
        if scene_html is not None:
            self.editor.setHtml(scene_html)
        self.load_current_image()

    def _available_backgrounds(self):
        if not os.path.isdir(self.image_dir):
            return []
        return sorted(name for name in os.listdir(self.image_dir) if name.lower().endswith((".png", ".jpg", ".jpeg")))

    def _build_ui(self, scene_text):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QGridLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.bg_label = QLabel(central_widget)
        self.bg_label.setAlignment(Qt.AlignCenter)
        self.bg_label.setScaledContents(True)
        # Background art must never contribute its native image size to the
        # layout; otherwise changing it can force the writing page to resize.
        self.bg_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        layout.addWidget(self.bg_label, 0, 0)

        self.fg_widget = QWidget(central_widget)
        self.fg_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.fg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        fg_layout = QVBoxLayout(self.fg_widget)
        fg_layout.setContentsMargins(36, 22, 36, 28)
        fg_layout.setSpacing(12)

        controls = QHBoxLayout()
        controls.addStretch()
        controls.addWidget(QLabel("Fundo:"))
        self.background_combo = QComboBox()
        self.background_combo.addItem("Papel sem imagem", None)
        for filename in self.image_files:
            self.background_combo.addItem(os.path.splitext(filename)[0].replace("_", " ").title(), filename)
        self.background_combo.setToolTip("Escolha o fundo do Modo foco. Atalho: F12 troca para o próximo fundo.")
        self.background_combo.currentIndexChanged.connect(self.select_background)
        controls.addWidget(self.background_combo)
        exit_button = QPushButton("Sair do foco")
        exit_button.setToolTip("Volte ao estúdio de escrita. Atalho: Esc ou F11.")
        exit_button.clicked.connect(self.close)
        controls.addWidget(exit_button)
        fg_layout.addLayout(controls)

        self.page_widget = QWidget(self.fg_widget)
        self.page_widget.setObjectName("FocusPage")
        self.page_widget.setMaximumWidth(760)
        self.page_widget.setMinimumWidth(420)
        self.page_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        page_layout = QVBoxLayout(self.page_widget)
        page_layout.setContentsMargins(48, 38, 48, 38)

        self.editor = PlainTextEdit()
        self.editor.setPlainText(scene_text)
        self.editor.setAcceptRichText(False)
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page_layout.addWidget(self.editor)
        fg_layout.addWidget(self.page_widget, 1, Qt.AlignHCenter)

        layout.addWidget(self.fg_widget, 0, 0)
        self.fg_widget.raise_()
        self._apply_focus_palette()

    def _apply_focus_palette(self):
        dark = self.theme_name == "Juvion Escuro"
        page_color = "#1a1817" if dark else "#fffaf0"
        text_color = "#f2dda2" if dark else "#33291f"
        canvas_color = "#121212" if dark else "#f1e9dc"
        muted_color = "#d1bd89" if dark else "#645447"
        self.bg_label.setStyleSheet("background-color: {};".format(canvas_color))
        self.page_widget.setStyleSheet(
            "QWidget#FocusPage {{ background-color: {}; border: 1px solid {}; border-radius: 10px; }}".format(
                page_color, "#3d3530" if dark else "#e3d7c5"
            )
        )
        self.editor.setStyleSheet(
            "QTextEdit {{ background: transparent; color: {}; border: none; font-family: 'Palatino Linotype', 'Book Antiqua', Georgia, serif; font-size: 16pt; line-height: 1.7; }}"
            "QTextEdit::placeholder {{ color: {}; }}".format(text_color, muted_color)
        )

    def closeEvent(self, event):
        if callable(self.on_close):
            self.on_close(self.editor.toHtmlPreservingOriginal())
        event.accept()

    def select_background(self, index):
        selected = self.background_combo.itemData(index)
        if selected in self.image_files:
            self.current_index = self.image_files.index(selected)
        self.load_current_image()

    def load_current_image(self):
        selected = self.background_combo.currentData()
        if not selected:
            self.bg_label.clear()
            return
        pixmap = QPixmap(os.path.join(self.image_dir, selected))
        if pixmap.isNull():
            self.bg_label.clear()
            return
        opacity_effect = QGraphicsOpacityEffect()
        self.bg_label.setGraphicsEffect(opacity_effect)
        self.animation = QPropertyAnimation(opacity_effect, b"opacity")
        self.animation.setDuration(240)
        self.animation.setStartValue(0.15)
        self.animation.setEndValue(1.0)
        self.animation.start()
        self.bg_label.setPixmap(pixmap)

    def cycle_image(self):
        if not self.image_files:
            return
        self.current_index = (self.current_index + 1) % len(self.image_files)
        self.background_combo.setCurrentIndex(self.current_index + 1)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_F11, Qt.Key_Escape):
            self.close()
        elif event.key() == Qt.Key_F12:
            self.cycle_image()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    image_directory = os.path.join(os.getcwd(), "assets", "backgrounds")
    focus_mode = FocusMode(image_directory, scene_text="Seu texto aparece aqui.")
    focus_mode.show()
    sys.exit(app.exec_())
