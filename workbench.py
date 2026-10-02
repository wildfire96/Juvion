import json
import os
import random
import shutil
from gettext import gettext as _

from PyQt5.QtCore import QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from compendium.enhanced_compendium import EnhancedCompendiumWindow
from project_window import project_settings_manager
from settings.settings_manager import WWSettingsManager
from settings.theme_manager import ThemeManager

# Define the file used for storing project data.
PROJECTS_FILE = "projects.json"
# Define a key for the last displayed project
LAST_DISPLAYED_KEY = "last_displayed_project"
# Load version display
VERSION_FILE = "version.json"

def load_version():
    """Load version data from the version JSON file."""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.warning(None, _("Load Version Error"),
                                _("Error loading version: {}").format(str(e)))
    return {}

# Load settings at module level.
VERSION = load_version()

def load_projects():
    """Load project data from a JSON file. If the file does not exist, return default projects."""
    filepath = os.path.join(os.getcwd(), "Projects", PROJECTS_FILE)
    if not os.path.exists(filepath):
        oldpath = os.path.join(os.getcwd(), PROJECTS_FILE) # backward compatibility
        if os.path.exists(oldpath):
            os.rename(oldpath, filepath)
    default_data = {
        "projects": [
            {"name": "My First Project", "cover": None},
            {"name": "Sci-Fi Epic", "cover": None},
            {"name": "Mystery Novel", "cover": None},
        ],
        LAST_DISPLAYED_KEY: None
    }
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                # Ensure compatibility with older files
                if isinstance(data, list):
                    return {LAST_DISPLAYED_KEY: None, "projects": data}
                return data
        except Exception as e:
            QMessageBox.warning(None, _("Load Projects Error"),
                                _("Error loading projects: {}").format(str(e)))
    return default_data

def save_projects(projects):
    """Save the project data to a JSON file."""
    filepath = os.path.join(os.getcwd(), "Projects", PROJECTS_FILE)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=4)
    except Exception as e:
        QMessageBox.warning(None, _("Save Projects Error"),
                            _("Error saving projects: {}").format(str(e)))

# Load projects at module level with the new structure
PROJECTS_DATA = load_projects()
PROJECTS = PROJECTS_DATA["projects"]

class ProjectPostIt(QToolButton):
    """
    A custom QToolButton that displays the project cover.
    Left-click opens the project.
    Right-click shows a context menu with options.
    """

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setup_ui()
        self.setToolTip(
            "Clique para abrir a obra. Clique com o botão direito para ver ações da obra."
        )

    def setup_ui(self):
        default_size = QSize(300, 450)
        if self.project["cover"]:
            pixmap = QPixmap(self.project["cover"])
            pixmap = pixmap.scaled(
                default_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            pixmap = QPixmap(default_size)
            pixmap.fill(Qt.GlobalColor.lightGray)
        icon = QIcon(pixmap)
        self.setIcon(icon)
        self.setIconSize(default_size)
        self.setFixedSize(default_size)
        self.setText("")
        self.setStyleSheet("QToolButton { margin: 0px; padding: 0px; }")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        rename_action = menu.addAction("Renomear obra")
        export_action = menu.addAction("Exportar obra")
        stats_action = menu.addAction("Ver estatísticas")
        cover_action = menu.addAction("Definir capa")
        menu.addSeparator()
        delete_action = menu.addAction("Excluir obra")
        action = menu.exec_(event.globalPos())
        if action == delete_action:
            confirm = QMessageBox.question(
                self, _("Delete Project"),
                _("Are you sure you want to delete '{}'?").format(self.project['name']),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    PROJECTS.remove(self.project)
                    save_projects(PROJECTS_DATA)
                    QMessageBox.information(
                        self, _("Delete Project"), _("Project '{}' deleted.").format(self.project['name']))
                    workbench = self.window()
                    if hasattr(workbench, "load_covers"):
                        workbench.load_covers()
                except Exception as e:
                    QMessageBox.warning(
                        self, _("Delete Project Error"), _("Error deleting project: {}").format(str(e)))
        elif action == export_action:
            from exporter import show_export_dialog

            project_name = self.project['name']
            cover = self.project.get("cover")
            workbench = self.window()
            opened = getattr(workbench, "open_project_windows", {}).get(project_name)
            if opened and opened.isVisible():
                opened.open_export_dialog()
                return
            from project_window.project_model import ProjectModel
            model = ProjectModel(project_name)
            show_export_dialog(self, project_name, model, cover_path=cover)
        elif action == stats_action:
            try:
                from util.statistics import show_statistics
                project_name = self.project['name']
                project_path = WWSettingsManager.get_project_path(project_name)
                print(f"Looking for project: {project_name}")
                print(f"Current directory: {os.getcwd()}")
                if project_path and os.path.exists(project_path):
                    print(f"Found project at: {project_path}")
                else:
                    if os.path.exists(project_name) and os.path.isdir(project_name):
                        project_path = project_name
                        print(f"Found project at: {project_path}")
                    else:
                        sanitized_name = project_name.replace(" ", "")
                        if os.path.exists(sanitized_name) and os.path.isdir(sanitized_name):
                            project_path = sanitized_name
                            print(f"Found project at: {project_path}")
                if not project_path:
                    initial_dir = WWSettingsManager.get_project_path()
                    if not os.path.exists(initial_dir):
                        initial_dir = os.getcwd()
                    msg = _("Could not automatically find the directory for project '{}'. Please select the project directory manually.").format(project_name)
                    QMessageBox.information(self, _("Select Project Directory"), msg)
                    project_path = QFileDialog.getExistingDirectory(
                        self, _("Select Directory for Project '{}'").format(project_name),
                        initial_dir
                    )
                    if not project_path:
                        raise FileNotFoundError(_("User cancelled the project directory selection"))
                if not os.path.exists(project_path) or not os.path.isdir(project_path):
                    raise FileNotFoundError(_("Invalid project directory: {}").format(project_path))
                print(f"Opening statistics for project at: {project_path}")
                show_statistics(project_path)
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                QMessageBox.warning(
                    self, _("Statistics Error"),
                    _("Error loading project statistics: {}\n\nProject: '{}'\nCurrent directory: {}\n\nDetails (for debugging):\n{}").format(
                        str(e), self.project['name'], os.getcwd(), error_details)
                )
        elif action == cover_action:
            try:
                self.add_book_cover()
                save_projects(PROJECTS_DATA)
            except Exception as e:
                QMessageBox.warning(self, _("Error Adding Cover"),
                                    _("Error adding book cover: {}").format(str(e)))
        elif action == rename_action:
            try:
                self.rename_project()
                save_projects(PROJECTS_DATA)
            except Exception as e:
                QMessageBox.warning(self, _("Error Renaming Project"),
                                    _("Error renaming project: {}").format(str(e)))

    def add_book_cover(self):
        file_path, unused = QFileDialog.getOpenFileName(
            self, _("Select Book Cover"), "", _("Image Files (*.png *.jpg *.jpeg *.bmp)")
        )
        destination_path = WWSettingsManager.get_project_path(self.project["name"])
        os.makedirs(destination_path, exist_ok=True)
        if file_path and os.path.dirname(file_path) != destination_path[:-1]:
            file_path = os.path.relpath(shutil.copy2(file_path, destination_path))
        if file_path:
            self.project["cover"] = file_path
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, _("Invalid Image"),
                                    _("The selected file is not a valid image."))
                return
            default_size = QSize(300, 450)
            pixmap = pixmap.scaled(
                default_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(pixmap)
            self.setIcon(icon)
            self.setIconSize(default_size)

    def rename_project(self):
        newname, ok = QInputDialog.getText(
            self, _("Rename Project"), _("Enter the project's new name:"))
        if ok and newname.strip():
            oldname = self.project["name"]
            newname = newname.strip()
            if newname in [p["name"] for p in PROJECTS] or WWSettingsManager.sanitize(newname) in [WWSettingsManager.sanitize(p["name"]) for p in PROJECTS]:
                QMessageBox.warning(self, _("Rename Project"),
                                    _("Project '{}' already exists.").format(newname))
                return
            if newname == oldname:
                QMessageBox.warning(self, _("Rename Project"),
                                    _("Project name is unchanged."))
                return
            self.rename_project_dir(oldname, newname)
            self.project["name"] = newname
            self.rename_cover(newname)
            save_projects(PROJECTS_DATA)
            settings = project_settings_manager.load_project_settings(oldname)
            if settings:
                project_settings_manager.save_project_settings(newname, settings, PROJECTS)
            workbench = self.window()
            workbench.load_covers()
            QMessageBox.information(self,
                _("Rename Project"), _("Project {} renamed to '{}'").format(oldname, newname))

    def rename_project_dir(self, oldname, newname):
        old_name = WWSettingsManager.sanitize(oldname)
        new_name = WWSettingsManager.sanitize(newname)
        if old_name == new_name:
            return
        old_dirname = WWSettingsManager.get_project_path(old_name)
        new_dirname = WWSettingsManager.get_project_path(new_name)
        if os.path.exists(new_dirname):
            raise FileExistsError(_("Project '{}' directory already exists.").format(newname))
        if not os.path.exists(old_dirname):
            return
        self.rename_project_dir_contents(old_dirname, new_dirname, old_name, new_name)

    def rename_project_dir_contents(self, old_dirname, new_dirname, old_name, new_name):
        os.mkdir(new_dirname)
        for filename in os.listdir(old_dirname):
            old_path = os.path.join(old_dirname, filename)
            if filename.startswith(old_name):
                remainder = filename[len(old_name):]
                new_filename = new_name + remainder
                new_path = os.path.join(new_dirname, new_filename)
            else:
                new_path = os.path.join(new_dirname, filename)
            shutil.copy2(old_path, new_path)
        shutil.rmtree(old_dirname)

    def rename_cover(self, new_name):
        cover = self.project.get("cover")
        if cover:
            filename = os.path.basename(cover)
            new_filepath = WWSettingsManager.get_project_path(new_name, filename)
            self.project["cover"] = os.path.relpath(new_filepath)

class ProjectCoverWidget(QWidget):
    """
    A composite widget that displays the project title above the cover.
    """
    openProject = pyqtSignal(str)

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.titleLabel = QLabel(self.project["name"])
        self.titleLabel.setObjectName("projectTitleLabel")
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.titleLabel)
        self.coverButton = ProjectPostIt(self.project)
        self.coverButton.clicked.connect(
            lambda: self.openProject.emit(self.project["name"]))
        layout.addWidget(self.coverButton)
        self.setLayout(layout)
        self.setFixedSize(300, 480)

    def update_labels(self):
        """Update UI labels for language changes."""
        self.titleLabel.setText(self.project["name"])
        self.coverButton.setToolTip(
            "Clique para abrir a obra. Clique com o botão direito para ver ações da obra."
        )

class WorkbenchWindow(QMainWindow):
    def __init__(self, translation_manager):
        super().__init__()
        # Set up gettext based on the selected language
        self.translation_manager = translation_manager
        self.setWindowTitle("Juvion — Obras")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinimizeButtonHint | Qt.WindowType.WindowMaximizeButtonHint)
        self.resize(640, 720)
        self.init_ui()
        self.apply_fixed_stylesheet()
        self.enhanced_compendium = EnhancedCompendiumWindow(self)
        self.enhanced_compendium.hide()
        self.last_opened_project = None
        self.open_project_windows = {}
        self._pending_project_name = None
        self.translation_manager.language_changed.connect(self.on_language_changed)

        # Connect to theme change signal
        theme_manager = ThemeManager()
        theme_manager.themeChanged.connect(self.on_theme_changed)


    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(15)

        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_label = QLabel("Juvion")
        header_label.setObjectName("headerLabel")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        self.settings_button = QPushButton("")
        cog_icon_path = os.path.join("assets", "icons", "settings.svg")
        self.settings_button.setIcon(ThemeManager.get_tinted_icon(cog_icon_path))
        self.settings_button.setToolTip("Configurações do Juvion: aparência, fontes, caminhos e integrações.")
        self.settings_button.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_button)
        self.content_layout.addWidget(header_container)

        carousel_container = QWidget()
        carousel_layout = QHBoxLayout(carousel_container)
        carousel_layout.setContentsMargins(0, 0, 0, 0)
        carousel_layout.setSpacing(10)

        self.left_button = QPushButton("")
        left_arrow_icon = ThemeManager.get_tinted_icon(os.path.join("assets", "icons", "chevron-left.svg"))
        self.left_button.setIcon(left_arrow_icon)
        self.left_button.setIconSize(QSize(32, 32))
        self.left_button.setFixedSize(60, 60)
        self.left_button.setToolTip("Ver obra anterior")
        self.left_button.clicked.connect(self.show_previous)
        carousel_layout.addWidget(self.left_button)

        self.coverStack = QStackedWidget()
        self.coverStack.setFixedSize(300, 480)
        carousel_layout.addWidget(self.coverStack, stretch=1)

        self.right_button = QPushButton("")
        right_arrow_icon = ThemeManager.get_tinted_icon(os.path.join("assets", "icons", "chevron-right.svg"))
        self.right_button.setIcon(right_arrow_icon)
        self.right_button.setIconSize(QSize(32, 32))
        self.right_button.setFixedSize(60, 60)
        self.right_button.setToolTip("Ver próxima obra")
        self.right_button.clicked.connect(self.show_next)
        carousel_layout.addWidget(self.right_button)
        self.content_layout.addWidget(carousel_container)

        self.new_project_button = QPushButton("＋ Nova obra")
        self.new_project_button.setProperty("primary", True)
        self.new_project_button.setObjectName("newProjectButton")
        self.new_project_button.setFixedSize(200, 50)
        self.new_project_button.setToolTip("Crie uma obra com sua própria estrutura, manuscrito e Universo.")
        self.new_project_button.clicked.connect(self.new_project)
        self.content_layout.addWidget(self.new_project_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.opening_label = QLabel()
        self.opening_label.setObjectName("OpeningProjectLabel")
        self.opening_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.opening_label.setWordWrap(True)
        self.opening_label.hide()
        self.content_layout.addWidget(self.opening_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.quoteLabel = None
        if WWSettingsManager.get_general_settings().get("show_random_quote", False):
            self.create_quote_label()

        self.coverStack.currentChanged.connect(self.updateCoverStackSize)
        self.load_covers()

        self.main_layout.addStretch()

        version_layout = QHBoxLayout()
        version_layout.addStretch()
        self.version_label = QLabel(_("Version: {}").format(VERSION.get('version', 'No Version Set')))
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_layout.addWidget(self.version_label)
        self.main_layout.addLayout(version_layout)

        self.coverStack.currentChanged.connect(self.update_current_project)

    def create_quote_label(self):
        """Creates a quote label and adds it to the content layout."""
        if self.quoteLabel:
            self.update_quote_label()
            return
        self.quoteLabel = QLabel()
        self.quoteLabel.setObjectName("quoteLabel")
        self.quoteLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quoteLabel.setWordWrap(True)
        self.quoteLabel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.quoteLabel.setStyleSheet("font-style: italic; color: #666; margin: 10px;")
        self.update_quote_label()
        self.quoteLabel.setMinimumSize(650, 150)
        self.content_layout.addWidget(self.quoteLabel, 0, Qt.AlignmentFlag.AlignCenter)

    def update_quote_label(self):
        """Update the quote label with a new random quote."""
        random_quote = self.load_random_quote()
        quote_text = random_quote.get('text', _('No quote available'))
        author_text = random_quote.get('author', _('Unknown'))
        formatted_text = (
            f"<html><body>"
            f"<div style='text-align:center;'>"
            f"<span style='font-size:18px;'>{quote_text}</span><br/>"
            f"<span style='font-size:14px; color:#444;'> {author_text}</span>"
            f"</div>"
            f"</body></html>"
        )
        self.quoteLabel.setText(formatted_text)

    def load_random_quote(self):
        """Load a random quote based on selected language, falling back to English."""
        language = WWSettingsManager.get_general_settings().get("language", "en")
        file_name = "quotes_pl.json" if language == "pl" else "quotes.json"
        quotes_file = os.path.join(os.getcwd(), "assets", "quotes", file_name)
        try:
            with open(quotes_file, encoding="utf-8") as f:
                quotes = json.load(f)
            if not quotes:
                raise ValueError(_("Empty quotes list"))
            return random.choice(quotes)
        except Exception as e:
            if language != "en":
                print(f"Falling back to English quotes due to error: {e}")
                fallback_file = os.path.join(os.getcwd(), "assets", "quotes", "quotes.json")
                try:
                    with open(fallback_file, encoding="utf-8") as f:
                        quotes = json.load(f)
                    if not quotes:
                        raise ValueError(_("Empty quotes list"))
                    return random.choice(quotes)
                except Exception as ex:
                    print(f"Error loading English quotes: {ex}")
            print(f"Error loading quotes: {e}")
            return {"text": _("No quote available"), "author": _("Unknown")}

    def handle_quote_setting_change(self):
        """Responds to changing quote settings."""
        if WWSettingsManager.get_general_settings().get("show_random_quote", False):
            self.show_quote()
        else:
            self.hide_quote()

    def show_quote(self):
        """Shows a quote (creates if it doesn't exist)."""
        if not self.quoteLabel:
            self.create_quote_label()
        self.quoteLabel.show()

    def hide_quote(self):
        """Hides the quote (if there is one)."""
        if self.quoteLabel:
            self.quoteLabel.hide()

    def apply_fixed_stylesheet(self):
        fixed_styles = """
            QLabel#projectTitleLabel {
                font-weight: 500;
            }
            QPushButton#newProjectButton {
                font-size: 16px;
                font-weight: bold;
            }
        """
        self.setStyleSheet(fixed_styles)

    def open_settings(self):
        from settings.settings_dialog import SettingsDialog

        options = SettingsDialog(self.translation_manager, self)
        options.settings_saved.connect(self.handle_quote_setting_change)
        options.settings_saved.connect(self.handle_category_background_setting_change)
        options.exec_()

    def handle_category_background_setting_change(self):
        """Handle category background setting changes by refreshing open project windows."""
        # Refresh all open project windows to update category backgrounds
        for project_name, project_window in self.open_project_windows.items():
            if project_window and project_window.isVisible():
                project_window.refresh_category_backgrounds()

    def on_language_changed(self, language):
        """Handle language change by updating UI labels."""
        self.update_ui_labels()
        for i in range(self.coverStack.count()):
            widget = self.coverStack.widget(i)
            if isinstance(widget, ProjectCoverWidget):
                widget.update_labels()
        if self.quoteLabel:
            self.update_quote_label()

    def update_ui_labels(self):
        """Update all UI labels for the current language."""
        self.setWindowTitle("Juvion — Obras")
        self.left_button.setToolTip(_("Previous Project"))
        self.right_button.setToolTip(_("Next Project"))
        self.new_project_button.setText("＋ Nova obra")
        self.new_project_button.setToolTip(_("Create a brand-new project"))
        self.settings_button.setToolTip(_("Click here to configure global options (paths, fonts, themes, etc.)"))
        self.version_label.setText(_("Version: {}").format(VERSION.get('version', 'No Version Set')))

    def updateCoverStackSize(self, index):
        fixed_width = 300
        fixed_height = 480
        self.coverStack.setFixedSize(fixed_width, fixed_height)

    def load_covers(self):
        while self.coverStack.count():
            widget = self.coverStack.widget(0)
            self.coverStack.removeWidget(widget)
            widget.deleteLater()
        if PROJECTS:
            for project in PROJECTS:
                cover_widget = ProjectCoverWidget(project)
                cover_widget.openProject.connect(self.open_project)
                self.coverStack.addWidget(cover_widget)
            last_displayed = PROJECTS_DATA.get(LAST_DISPLAYED_KEY)
            if last_displayed:
                for i, project in enumerate(PROJECTS):
                    if project["name"] == last_displayed:
                        self.coverStack.setCurrentIndex(i)
                        break
        else:
            self.new_project_btn = QToolButton()
            self.new_project_btn.setText(_("＋ New Project"))
            self.new_project_btn.setFixedSize(300, 480)
            self.new_project_btn.clicked.connect(self.new_project)
            self.coverStack.addWidget(self.new_project_btn)
        self.updateCoverStackSize(self.coverStack.currentIndex())

    def show_previous(self):
        count = self.coverStack.count()
        if count == 0:
            return
        index = self.coverStack.currentIndex()
        new_index = (index - 1) % count
        self.coverStack.setCurrentIndex(new_index)

    def show_next(self):
        count = self.coverStack.count()
        if count == 0:
            return
        index = self.coverStack.currentIndex()
        new_index = (index + 1) % count
        self.coverStack.setCurrentIndex(new_index)

    def open_project(self, project_name):
        """Confirm a click, then open a project after a short visible preparation state."""
        from project_window.project_window import ProjectWindow

        # Check if the project window is already open
        if project_name in self.open_project_windows:
            project_window = self.open_project_windows[project_name]
            # Ensure the window is still valid (not deleted)
            if project_window and project_window.isVisible():
                project_window.raise_()  # Bring to front
                project_window.activateWindow()  # Focus the window
                return

        if self._pending_project_name:
            return

        self._pending_project_name = project_name
        self.opening_label.setText("Preparando “{}”…\nA obra abrirá em instantes.".format(project_name))
        self.opening_label.show()
        self.coverStack.setEnabled(False)
        self.left_button.setEnabled(False)
        self.right_button.setEnabled(False)
        self.new_project_button.setEnabled(False)
        self.opening_label.repaint()
        # Allow Qt to paint the feedback before constructing the project window.
        QTimer.singleShot(0, lambda: self._open_project_after_feedback(project_name, ProjectWindow))

    def _open_project_after_feedback(self, project_name, project_window_class):
        """Perform the existing project construction after the opening feedback is visible."""
        if self._pending_project_name != project_name:
            return

        try:
            self.last_opened_project = project_name
            PROJECTS_DATA[LAST_DISPLAYED_KEY] = project_name
            save_projects(PROJECTS_DATA)
            project = next(project for project in PROJECTS if project["name"] == project_name)
            self.project_window = project_window_class(
                project_name,
                self.enhanced_compendium,
                cover_path=project.get("cover"),
                project_updated=self.update_project_cover,
            )
            self.open_project_windows[project_name] = self.project_window
            # Connect the window's destroyed signal to clean up the dictionary
            self.project_window.destroyed.connect(
                lambda: self.on_project_window_closed(project_name)
            )
            self.project_window.show()
        except Exception as error:
            QMessageBox.warning(
                self,
                "Não foi possível abrir a obra",
                "O Juvion não conseguiu preparar “{}”.\n\n{}".format(project_name, error),
            )
        finally:
            self._reset_opening_feedback()

    def _reset_opening_feedback(self):
        """Restore the library controls after the opening attempt finishes."""
        self._pending_project_name = None
        self.opening_label.hide()
        self.coverStack.setEnabled(True)
        self.left_button.setEnabled(True)
        self.right_button.setEnabled(True)
        self.new_project_button.setEnabled(True)

    def on_project_window_closed(self, project_name):
        """Remove the project window from the tracking dictionary when closed."""
        self.open_project_windows.pop(project_name, None)

    def update_project_cover(self, project_name, cover_path):
        for project in PROJECTS:
            if project["name"] == project_name:
                project["cover"] = cover_path
                save_projects(PROJECTS_DATA)
                self.load_covers()
                return

    def new_project(self):
        from project_window.new_project_dialog import NewProjectDialog
        from project_window.templates_data import populate_template_structure, seed_template_universe
        from project_window.tree_manager import save_structure
        from project_window import project_settings_manager as psm
        from compendium.compendium_manager import CompendiumManager

        existing_names = [p["name"] for p in PROJECTS]
        dialog = NewProjectDialog(existing_names, self)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        name = dialog.project_name
        template = dialog.chosen_template

        # 1. Generate customized structure from template
        structure = populate_template_structure(template)
        save_structure(name, structure)

        # 2. Initialize project settings with template values
        project_settings = {
            "global_pov": "Terceira Pessoa Limitada",
            "global_pov_character": "Protagonista",
            "global_tense": "Presente",
            "progress": {"word_goal": template.get("word_goal", 80_000)},
            "work": {
                "cover": None,
                "synopsis": f"Uma obra do gênero {template.get('genre', 'Ficção')}.\n\n{template.get('description', '')}",
                "series": "",
                "volume": "1",
                "categories": template.get("categories", ""),
                "tags": template.get("tags", ""),
                "status": "Planejamento",
            },
        }
        psm.save_project_settings(name, project_settings)

        # 3. Seed initial compendium entries if defined in template
        try:
            compendium = CompendiumManager(name)
            seed_template_universe(compendium, template)
        except Exception as e:
            QMessageBox.warning(self, "Fichas do modelo", "A estrutura foi criada, mas algumas fichas não puderam ser adicionadas.\n\n{}".format(e))

        # 4. Save into library project list
        new_project = {"name": name, "cover": None}
        PROJECTS.append(new_project)
        PROJECTS_DATA[LAST_DISPLAYED_KEY] = name
        save_projects(PROJECTS_DATA)
        self.load_covers()
        self.coverStack.setCurrentIndex(len(PROJECTS) - 1)

        QMessageBox.information(
            self,
            "Nova Obra Criada",
            f"A obra “{name}” foi criada com sucesso usando o modelo “{template.get('name')}”.\n"
            f"Sua estrutura de atos, capítulos e fichas do Universo já foram inicializadas."
        )

    def closeEvent(self, event):
        """Save the last displayed project when closing."""
        current_index = self.coverStack.currentIndex()
        if current_index >= 0 and PROJECTS:
            PROJECTS_DATA[LAST_DISPLAYED_KEY] = PROJECTS[current_index]["name"]
        save_projects(PROJECTS_DATA)
        super().closeEvent(event)

    def update_current_project(self, index):
        """Update the last displayed project when switching."""
        if index >= 0 and index < len(PROJECTS):
            PROJECTS_DATA[LAST_DISPLAYED_KEY] = PROJECTS[index]["name"]
            save_projects(PROJECTS_DATA)

    def on_theme_changed(self, theme_name):
        """Handle theme changes by refreshing icons and UI elements."""
        # Refresh workbench icons
        cog_icon_path = os.path.join("assets", "icons", "settings.svg")
        self.settings_button.setIcon(ThemeManager.get_tinted_icon(cog_icon_path))
        self.left_button.setIcon(ThemeManager.get_tinted_icon(os.path.join("assets", "icons", "chevron-left.svg")))
        self.right_button.setIcon(ThemeManager.get_tinted_icon(os.path.join("assets", "icons", "chevron-right.svg")))

        # Refresh project cover widgets
        for i in range(self.coverStack.count()):
            widget = self.coverStack.widget(i)
            if isinstance(widget, ProjectCoverWidget):
                # Refresh the cover button icons
                cover_button = widget.coverButton
                if hasattr(cover_button, 'setup_ui'):
                    cover_button.setup_ui()

        # Refresh all open project windows
        for project_name, project_window in self.open_project_windows.items():
            if project_window and project_window.isVisible():
                project_window.change_theme(theme_name)

    def get_project_list(self) -> list[str]:
        """ Extract a list of "name" values from the PROJECTS list of dicts """
        project_list = [project.get("name", "Unnamed Project") for project in PROJECTS]
        return project_list

if __name__ == "__main__":
    import sys

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = WorkbenchWindow()
    window.show()
    sys.exit(app.exec_())
